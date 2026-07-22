"""AI 폐렴 예측 API.

[REQ-PRED-001] 진료기록의 X-ray 이미지로 폐렴 예측을 수행한다.
[REQ-PRED-002] 진료기록의 예측 결과를 목록으로 조회한다.

권한: 승인된 사용자(staff, admin).
추론(3.6~5초)은 이 요청-응답 사이클 안에서 하지 않는다.
백그라운드 작업으로 등록만 하고 즉시 202로 응답한다. (NFR-PRED-002)
"""

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import require_roles
from app.models.user import Role, User
from app.schemas.prediction import (
    PredictionJobResponse,
    PredictionListResponse,
    PredictionRequestResponse,
)
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1", tags=["Predictions"])

require_approved_user = require_roles(Role.STAFF, Role.ADMIN)


# [REQ-PRED-001] AI 모델을 활용한 폐렴 예측
@router.post(
    "/medical-records/{record_id}/predictions",
    response_model=PredictionRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="폐렴 예측 요청",
    responses={
        200: {"description": "이미 저장된 예측 결과가 있어 즉시 반환"},
        202: {"description": "추론 작업이 백그라운드에 등록됨. job_id 로 상태를 조회"},
    },
)
async def request_prediction(
    response: Response,
    record_id: int = Path(..., ge=1),
    current_user: User = Depends(require_approved_user),
    db: AsyncSession = Depends(async_get_db),
):
    body, status_code = await PredictionService.request_prediction(db, record_id)
    response.status_code = status_code
    return body


# 비동기 작업 상태 조회 (폴링)
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
):
    return await PredictionService.get_job(db, job_id)


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
    return await PredictionService.get_list(db, record_id)
