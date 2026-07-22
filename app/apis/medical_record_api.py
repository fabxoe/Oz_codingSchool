from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user, require_roles
from app.models.user import Role, User
from app.schemas.medical_record import (
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
    AIAnalysisResultResponse,
)
from app.services.medical_record_service import MedicalRecordService

router = APIRouter(prefix="/api/v1", tags=["Medical Records"])


@router.post(
    "/medical-records",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="진료기록 등록",
)
async def create_medical_record(
    patient_id: int = Form(ge=1),
    chart_number: str = Form(min_length=1, max_length=50),
    symptoms: str = Form(min_length=1),
    xray_image: UploadFile = File(),
    current_user: User = Depends(require_roles(Role.STAFF, Role.ADMIN)),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.create(
        db,
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        xray_image=xray_image,
        uploader_id=current_user.id,
    )


@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=list[MedicalRecordListItem],
    status_code=status.HTTP_200_OK,
    summary="환자별 진료기록 목록 조회",
)
async def get_medical_records_by_patient(
    patient_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.get_records_by_patient(db, patient_id)


@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="진료기록 상세 조회",
)
async def get_medical_record_detail(
    record_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.get_record_detail(db, record_id)

@router.post(
    "/medical-records/{record_id}/predict",
    response_model=AIAnalysisResultResponse,
    status_code=status.HTTP_200_OK,
    summary="AI 폐렴 예측",
)
async def predict_ai(
    record_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await MedicalRecordService.predict_ai(db, record_id)
