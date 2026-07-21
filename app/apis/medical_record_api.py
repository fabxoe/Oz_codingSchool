from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.medical_record import (
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
)
from app.services.medical_record_service import MedicalRecordService

router = APIRouter(tags=["medical-records"])


# 환자별 진료기록 목록 조회
@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=list[MedicalRecordListItem],
)
async def get_medical_records_by_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.get_records_by_patient(db, patient_id)


# 진료기록 상세 조회
@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
)
async def get_medical_record_detail(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.get_record_detail(db, record_id)