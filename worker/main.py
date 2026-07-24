"""폐렴 예측 Worker.

Redis 큐에서 작업을 하나씩 꺼내 모델 추론을 수행하고,
결과를 ai_analysis_results 테이블에 저장한 뒤 작업 상태를 갱신한다.

이 프로세스가 모델을 독점하므로 동시 요청으로 인한 내부 상태 꼬임이 없다.
처리량을 늘리려면 프로세스를 늘린다: docker compose up --scale worker=2
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import redis
from sqlalchemy import create_engine, text

from worker import config
from worker.model import PneumoniaEnsemble


def log(message: str) -> None:
    """컨테이너 로그에 바로 보이도록 시각을 붙여 출력한다."""
    print(f"[worker {datetime.now():%H:%M:%S}] {message}", flush=True)


def resolve_image_path(image_url: str) -> Path:
    """DB에 저장된 URL을 실제 파일 경로로 바꾼다.

    "/media/xray/abc.png"  ->  MEDIA_ROOT/xray/abc.png
    """
    relative = image_url.removeprefix("/media/").lstrip("/")
    return Path(config.MEDIA_ROOT) / relative


class PredictionWorker:

    def __init__(self) -> None:
        log("Redis 연결 중...")
        self.redis = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            decode_responses=True,
            # 유휴 상태에서 연결이 끊기지 않도록 keepalive 와 주기적 health check 를 켠다.
            socket_keepalive=True,
            health_check_interval=30,
        )

        log("DB 연결 중...")
        # pool_pre_ping: 오래 대기하다 끊긴 커넥션을 자동으로 되살린다.
        self.engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)

        log("모델 로딩 중... (약 609MB, 시간이 걸립니다)")
        started = time.time()
        self.predictor = PneumoniaEnsemble()
        log(f"모델 로딩 완료 ({time.time() - started:.1f}초)")

    # ------------------------------------------------------------
    # 작업 상태 관리
    # ------------------------------------------------------------

    def _job_key(self, job_id: str) -> str:
        return f"{config.JOB_KEY_PREFIX}{job_id}"

    def _update_job(self, job_id: str, **fields) -> None:
        key = self._job_key(job_id)
        self.redis.hset(key, mapping={k: str(v) for k, v in fields.items()})
        self.redis.expire(key, config.JOB_TTL_SECONDS)

    def _release_lock(self, record_id: int) -> None:
        self.redis.delete(f"{config.LOCK_KEY_PREFIX}{record_id}")

    # ------------------------------------------------------------
    # DB
    # ------------------------------------------------------------

    def _fetch_image_url(self, record_id: int) -> str | None:
        """진료기록에 연결된 X-ray 이미지 URL을 가져온다."""
        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT image_url FROM xray_images "
                    "WHERE record_id = :record_id "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"record_id": record_id},
            ).first()
        return row[0] if row else None

    def _save_result(self, record_id: int, result: dict) -> int:
        """예측 결과를 저장하고 생성된 행의 id를 반환한다."""
        with self.engine.begin() as connection:
            inserted = connection.execute(
                text(
                    "INSERT INTO ai_analysis_results "
                    "(record_id, is_pneumonia, confidence, heatmap_url, ai_model, created_at) "
                    "VALUES (:record_id, :is_pneumonia, :confidence, NULL, :ai_model, NOW())"
                ),
                {
                    "record_id": record_id,
                    "is_pneumonia": bool(result["is_pneumonia"]),
                    # Numeric(5,4) 컬럼에 맞춰 소수점 4자리로 저장한다.
                    "confidence": Decimal(str(round(float(result["confidence"]), 4))),
                    "ai_model": config.AI_MODEL_NAME,
                },
            )
            return int(inserted.lastrowid)

    # ------------------------------------------------------------
    # 작업 처리
    # ------------------------------------------------------------

    def handle(self, task: dict) -> None:
        job_id = task["job_id"]
        record_id = int(task["record_id"])

        log(f"작업 시작 job={job_id} record={record_id}")
        self._update_job(job_id, status="processing")

        # 1. 이미지 경로 확인
        image_url = self._fetch_image_url(record_id)
        if image_url is None:
            raise FileNotFoundError("진료기록에 연결된 X-ray 이미지가 없습니다.")

        image_path = resolve_image_path(image_url)
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        # 2. 추론
        started = time.time()
        result = self.predictor.predict(image_path)
        elapsed = time.time() - started
        log(
            f"추론 완료 ({elapsed:.2f}초) "
            f"폐렴={result['is_pneumonia']} confidence={result['confidence']:.4f}"
        )

        # 3. 저장
        result_id = self._save_result(record_id, result)

        # 4. 상태 갱신
        self._update_job(job_id, status="done", result_id=result_id)
        self._release_lock(record_id)
        log(f"작업 완료 job={job_id} result_id={result_id}")

    def run(self) -> None:
        log(f"큐 대기 시작: {config.QUEUE_KEY}")
        while True:
            # BLPOP: 큐가 빌 때까지 블로킹. timeout=5 로 주기적으로 깨어난다.
            # 대기 중 소켓 타임아웃 등 Redis 예외가 나도 worker 가 죽지 않고
            # 잠시 쉬었다가 다시 대기한다.
            try:
                popped = self.redis.blpop(config.QUEUE_KEY, timeout=5)
            except redis.exceptions.RedisError as error:
                log(f"큐 대기 재시도: {error}")
                time.sleep(1)
                continue
            if popped is None:
                continue

            _, raw = popped
            try:
                task = json.loads(raw)
            except json.JSONDecodeError:
                log(f"잘못된 작업 형식 무시: {raw!r}")
                continue

            try:
                self.handle(task)
            except Exception as error:  # noqa: BLE001 - Worker는 죽으면 안 된다
                log(f"작업 실패: {error}")
                traceback.print_exc()
                self._update_job(
                    task["job_id"], status="failed", error=str(error)
                )
                self._release_lock(int(task["record_id"]))


def main() -> None:
    worker = PredictionWorker()
    worker.run()


if __name__ == "__main__":
    main()
