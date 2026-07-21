# app/apis/medical_record.py
from fastapi import APIRouter, Depends, Form, File, UploadFile, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db.databases import async_get_db as get_db
from app.models.user import User, Role
from app.models.medical_record import MedicalRecord
from app.core.security import get_current_user
from app.schemas.medical_record import MedicalRecordResponse, MedicalRecordSummaryResponse
from app.services.medical_record import MedicalRecordService
from app.apis.patient import require_staff_or_admin

router = APIRouter(prefix="/api/v1", tags=["Medical Records"])

@router.post("/medical-records", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    patient_id: int = Form(..., description="환자 ID"),
    chart_number: str = Form(..., description="진료 차트 번호"),
    symptoms: str = Form(..., description="진료 증상"),
    xray_image: UploadFile = File(..., description="X-Ray 이미지 파일"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    return await MedicalRecordService.create_medical_record(
        db, patient_id, chart_number, symptoms, xray_image
    )

@router.get("/patients/{patient_id}/medical-records", response_model=list[MedicalRecordSummaryResponse])
async def list_patient_medical_records(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
    )
    return list(result.scalars().all())

@router.get("/medical-records/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record_detail(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="진료기록을 찾을 수 없습니다."
        )
    return record