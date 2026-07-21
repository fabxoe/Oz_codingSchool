"""AI 폐렴 예측 업무 로직 계층.

[REQ-PRED-001] 예측 실행 (캐싱 포함)
[REQ-PRED-002] 예측 결과 목록 조회

추론은 이 프로세스에서 하지 않는다. Redis 큐에 작업을 넣으면
별도의 Worker 프로세스가 꺼내서 처리하고 DB에 결과를 저장한다.
"""

import json
import uuid
from datetime import datetime

import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import (
    JOB_TTL_SECONDS,
    LOCK_TTL_SECONDS,
    QUEUE_KEY,
    job_key,
    lock_key,
)
from app.models.ai_analysis_result import AIAnalysisResult
from app.repositories.prediction_repository import PredictionRepository

# 현재 서비스에서 사용하는 모델 식별자.
# 캐싱 판단(record_id + ai_model)의 기준이 되므로 모델 교체 시 이 값을 바꾼다.
AI_MODEL_NAME = "pneumonia_ensemble_v1"


class PredictionService:

    # ------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------

    @staticmethod
    async def _ensure_record_exists(db: AsyncSession, record_id: int) -> None:
        record = await PredictionRepository.get_medical_record(db, record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않는 진료기록입니다.",
            )

    @staticmethod
    def _to_result_dict(result: AIAnalysisResult) -> dict:
        return {
            "id": result.id,
            "record_id": result.record_id,
            "is_pneumonia": result.is_pneumonia,
            "confidence": result.confidence,
            "heatmap_url": result.heatmap_url,
            "ai_model": result.ai_model,
            "created_at": result.created_at,
        }

    # ------------------------------------------------------------
    # [REQ-PRED-001] 예측 요청
    # ------------------------------------------------------------

    @staticmethod
    async def request_prediction(
        db: AsyncSession,
        redis_client: redis.Redis,
        record_id: int,
    ) -> tuple[dict, int]:
        """예측을 요청한다. (응답 본문, HTTP 상태코드) 를 반환한다.

        흐름:
        1. 진료기록 존재 확인          → 없으면 404
        2. X-ray 이미지 존재 확인      → 없으면 422
        3. 기존 결과 조회              → 있으면 200 + 결과 (추론 안 함)
        4. 진행 중 작업 확인           → 있으면 202 + 기존 job_id
        5. 작업 등록                   → 202 + 새 job_id
        """
        # 1
        await PredictionService._ensure_record_exists(db, record_id)

        # 2
        image_url = await PredictionRepository.get_latest_xray_url(db, record_id)
        if image_url is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="해당 진료기록에 X-ray 이미지가 없어 예측할 수 없습니다.",
            )

        # 3 — 캐시 히트. 추론 과정을 거치지 않고 저장된 데이터를 응답한다.
        cached = await PredictionRepository.get_cached_result(
            db, record_id, AI_MODEL_NAME
        )
        if cached is not None:
            return (
                {
                    "status": "done",
                    "cached": True,
                    "result": PredictionService._to_result_dict(cached),
                },
                status.HTTP_200_OK,
            )

        try:
            # 4 — 같은 진료기록이 이미 처리 중이면 그 작업을 그대로 알려준다.
            #     사용자가 버튼을 연타해도 중복 추론이 일어나지 않는다.
            existing_job_id = await redis_client.get(lock_key(record_id))
            if existing_job_id:
                return (
                    {
                        "status": "queued",
                        "cached": False,
                        "job_id": existing_job_id,
                        "poll_url": f"/api/v1/predictions/jobs/{existing_job_id}",
                    },
                    status.HTTP_202_ACCEPTED,
                )

            # 5 — 새 작업 등록
            job_id = uuid.uuid4().hex

            await redis_client.hset(
                job_key(job_id),
                mapping={
                    "status": "queued",
                    "record_id": str(record_id),
                    "created_at": datetime.now().isoformat(),
                },
            )
            await redis_client.expire(job_key(job_id), JOB_TTL_SECONDS)

            await redis_client.set(
                lock_key(record_id), job_id, ex=LOCK_TTL_SECONDS
            )

            # 큐에 넣는 것이 마지막이다. 상태를 먼저 기록해야
            # Worker가 즉시 꺼내갔을 때 상태가 없어서 생기는 문제를 막는다.
            await redis_client.rpush(
                QUEUE_KEY,
                json.dumps({"job_id": job_id, "record_id": record_id}),
            )

        except redis.RedisError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="예측 작업 큐에 연결할 수 없습니다.",
            ) from error

        return (
            {
                "status": "queued",
                "cached": False,
                "job_id": job_id,
                "poll_url": f"/api/v1/predictions/jobs/{job_id}",
            },
            status.HTTP_202_ACCEPTED,
        )

    # ------------------------------------------------------------
    # 작업 상태 조회 (폴링)
    # ------------------------------------------------------------

    @staticmethod
    async def get_job(
        db: AsyncSession,
        redis_client: redis.Redis,
        job_id: str,
    ) -> dict:
        try:
            job = await redis_client.hgetall(job_key(job_id))
        except redis.RedisError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="예측 작업 큐에 연결할 수 없습니다.",
            ) from error

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않거나 만료된 작업입니다.",
            )

        response = {
            "job_id": job_id,
            "record_id": int(job["record_id"]),
            "status": job["status"],
            "result": None,
            "error": job.get("error"),
        }

        # 완료된 작업이면 Worker가 저장한 결과를 DB에서 읽어 함께 반환한다.
        if job["status"] == "done" and job.get("result_id"):
            saved = await PredictionRepository.get_by_id(
                db, int(job["result_id"])
            )
            if saved is not None:
                response["result"] = PredictionService._to_result_dict(saved)

        return response

    # ------------------------------------------------------------
    # [REQ-PRED-002] 예측 결과 목록
    # ------------------------------------------------------------

    @staticmethod
    async def get_list(db: AsyncSession, record_id: int) -> dict:
        await PredictionService._ensure_record_exists(db, record_id)

        image_url = await PredictionRepository.get_latest_xray_url(db, record_id)
        results = await PredictionRepository.get_all_by_record(db, record_id)

        return {
            "record_id": record_id,
            "xray_image_url": image_url,
            "predictions": results,
        }
