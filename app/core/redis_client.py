"""Redis 연결 관리.

폐렴 예측 작업 큐(Queue)와 작업 상태 저장에 사용한다.
FastAPI는 비동기 서버이므로 redis.asyncio 클라이언트를 쓴다.
"""

import redis.asyncio as redis

from app.core.config import settings

# 큐/작업 상태 키 규칙 (worker/config.py 와 반드시 일치해야 한다)
QUEUE_KEY = "pneumonia:queue"
JOB_KEY_PREFIX = "pneumonia:job:"
LOCK_KEY_PREFIX = "pneumonia:lock:"

JOB_TTL_SECONDS = 60 * 60  # 1시간
LOCK_TTL_SECONDS = 60 * 10  # 10분


# 커넥션 풀은 클라이언트 내부에서 관리되므로 모듈 단위로 하나만 만든다.
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    """FastAPI 의존성으로 주입할 Redis 클라이언트."""
    return redis_client


def job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


def lock_key(record_id: int) -> str:
    return f"{LOCK_KEY_PREFIX}{record_id}"
