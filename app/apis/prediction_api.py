"""AI 폐렴 예측 API.

[REQ-PRED-001] 진료기록의 X-ray 이미지로 폐렴 예측을 수행한다.
[REQ-PRED-002] 진료기록의 예측 결과를 목록으로 조회한다.

권한: 승인된 사용자(staff, admin). 승인 대기(pending)는 접근할 수 없다.

추론은 이 프로세스에서 하지 않는다. 모델이 thread-safe 하지 않고
CPU를 오래 점유하므로, 별도 Worker 프로세스가 Redis 큐를 통해 처리한다.
"""

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.redis_client import get_redis
from app.core.security import require_roles
from app.models.user import Role, User
from app.schemas.prediction import (
    PredictionJobResponse,
    PredictionListResponse,
    PredictionRequestResponse,
)
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1", tags=["Predictions"])

# 요구사항의 "사내 의료인, 개발팀, 연구자"는 승인이 끝난 사용자를 뜻한다.
# department 는 승인 시점에 부여되므로 여기서는 승인 여부(role)만 검사한다.
require_approved_user = require_roles(Role.STAFF, Role.ADMIN)


# [REQ-PRED-001] AI 모델을 활용한 폐렴 예측
@router.post(
    "/medical-records/{record_id}/predictions",
    response_model=PredictionRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="폐렴 예측 요청",
    responses={
        200: {"description": "이미 저장된 예측 결과가 있어 즉시 반환"},
        202: {"description": "추론 작업이 큐에 등록됨. job_id 로 상태를 조회"},
    },
)
async def request_prediction(
    response: Response,
    record_id: int = Path(..., ge=1),
    current_user: User = Depends(require_approved_user),
    db: AsyncSession = Depends(async_get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """예측을 요청한다.

    같은 진료기록에 같은 모델의 결과가 이미 있으면 추론하지 않고 200으로 바로 준다.
    새로 추론해야 하면 작업만 등록하고 202를 반환한다. (NFR-PRED-002: 3초 이내 응답)
    """
    body, status_code = await PredictionService.request_prediction(
        db, redis_client, record_id
    )
    # 캐시 히트면 200, 신규 작업이면 202로 응답 코드를 바꾼다.
    response.status_code = status_code
    return body


# [REQ-PRED-001 보조] 비동기 작업 상태 조회
@router.get(
    "/predictions/jobs/{job_id}",
    response_model=PredictionJobResponse,
    status_code=status.HTTP_200_OK,
    summary="예측 작업 상태 조회",
)
async def get_prediction_job(
    job_id: str = Path(..., min_length=8, max_length=64),
    current_user: User = Depends(require_approved_user),
    db: AsyncSession = Depends(async_get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """작업 상태를 조회한다.

    status: queued | processing | done | failed
    done 이면 result 에 예측 결과가 담긴다.
    클라이언트는 1초 간격으로 폴링하고 done/failed 를 받으면 중단한다.
    """
    return await PredictionService.get_job(db, redis_client, job_id)


# [REQ-PRED-002] 폐렴 예측 결과 목록 조회
@router.get(
    "/medical-records/{record_id}/predictions",
    response_model=PredictionListResponse,
    status_code=status.HTTP_200_OK,
    summary="폐렴 예측 결과 목록 조회",
)
async def list_predictions(
    record_id: int = Path(..., ge=1),
    current_user: User = Depends(require_approved_user),
    db: AsyncSession = Depends(async_get_db),
):
    """해당 진료기록의 X-ray 이미지와 예측 결과 목록을 최신순으로 반환한다.

    결과가 없으면 predictions 는 빈 배열이며 404가 아니다.
    """
    return await PredictionService.get_list(db, record_id)
