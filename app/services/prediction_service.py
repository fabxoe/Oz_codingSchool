"""AI 폐렴 예측 업무 로직 계층.

[REQ-PRED-001] 예측 실행 (캐싱 포함)
[REQ-PRED-002] 예측 결과 목록 조회

Redis 없이, FastAPI 프로세스 안의 asyncio 백그라운드 태스크 +
인메모리 딕셔너리로 작업 큐를 흉내낸다.
추론(3.6~5초)은 asyncio.to_thread로 별도 스레드에서 돌려서
이벤트 루프를 막지 않고, API는 즉시 202로 응답한다. (NFR-PRED-002)

주의: 인메모리 상태이므로 서버 재시작 시 진행 중이던 job은 사라진다.
이 구현은 단일 프로세스 운영을 전제로 한다.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import AsyncSessionLocal
from app.models.ai_analysis_result import AIAnalysisResult
from app.repositories.prediction_repository import PredictionRepository

AI_MODEL_NAME = "pneumonia_ensemble_v1"

# job_id -> {"status", "record_id", "result_id", "error"}
_JOBS: dict[str, dict] = {}
# record_id -> job_id (동시에 같은 진료기록에 중복 추론 방지)
_RECORD_LOCKS: dict[int, str] = {}

_predictor = None
_predictor_lock = asyncio.Lock()


async def _get_predictor():
    """모델을 최초 1회만 로드하고 재사용한다."""
    global _predictor
    if _predictor is None:
        async with _predictor_lock:
            if _predictor is None:
                from worker.model import PneumoniaEnsemble

                _predictor = await asyncio.to_thread(PneumoniaEnsemble)
    return _predictor


class PredictionService:

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

    @staticmethod
    async def request_prediction(
        db: AsyncSession,
        record_id: int,
    ) -> tuple[dict, int]:
        await PredictionService._ensure_record_exists(db, record_id)

        image_url = await PredictionRepository.get_latest_xray_url(db, record_id)
        if image_url is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="해당 진료기록에 X-ray 이미지가 없어 예측할 수 없습니다.",
            )

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

        existing_job_id = _RECORD_LOCKS.get(record_id)
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

        job_id = uuid.uuid4().hex
        _JOBS[job_id] = {
            "status": "queued",
            "record_id": record_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result_id": None,
            "error": None,
        }
        _RECORD_LOCKS[record_id] = job_id

        asyncio.create_task(
            PredictionService._run_prediction(job_id, record_id, image_url)
        )

        return (
            {
                "status": "queued",
                "cached": False,
                "job_id": job_id,
                "poll_url": f"/api/v1/predictions/jobs/{job_id}",
            },
            status.HTTP_202_ACCEPTED,
        )

    @staticmethod
    async def _run_prediction(job_id: str, record_id: int, image_url: str) -> None:
        _JOBS[job_id]["status"] = "processing"
        try:
            predictor = await _get_predictor()

            from pathlib import Path

            relative = image_url.removeprefix("/media/").lstrip("/")
            image_path = Path("media") / relative
            if not image_path.exists():
                raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

            result = await asyncio.to_thread(predictor.predict, image_path)

            async with AsyncSessionLocal() as db:
                saved = await PredictionRepository.create(
                    db,
                    record_id=record_id,
                    is_pneumonia=result["is_pneumonia"],
                    confidence=result["confidence"],
                    ai_model=AI_MODEL_NAME,
                    heatmap_url=None,
                )
                _JOBS[job_id]["status"] = "done"
                _JOBS[job_id]["result_id"] = saved.id

        except Exception as error:  # noqa: BLE001
            _JOBS[job_id]["status"] = "failed"
            _JOBS[job_id]["error"] = str(error)
        finally:
            _RECORD_LOCKS.pop(record_id, None)

    @staticmethod
    async def get_job(db: AsyncSession, job_id: str) -> dict:
        job = _JOBS.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="존재하지 않거나 만료된 작업입니다.",
            )

        response = {
            "job_id": job_id,
            "record_id": job["record_id"],
            "status": job["status"],
            "result": None,
            "error": job.get("error"),
        }

        if job["status"] == "done" and job.get("result_id"):
            saved = await PredictionRepository.get_by_id(db, job["result_id"])
            if saved is not None:
                response["result"] = PredictionService._to_result_dict(saved)

        return response

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
