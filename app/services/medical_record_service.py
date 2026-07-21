from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.schemas.medical_record import (
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
)


class MedicalRecordService:
    """진료기록 관련 업무 흐름을 담당하는 클래스."""

    @staticmethod
    async def get_records_by_patient(
        db: AsyncSession,
        patient_id: int,
    ) -> list[MedicalRecordListItem]:
        # 환자가 실제로 존재하는지 먼저 확인 (없으면 404)
        patient = await db.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )

        records = await MedicalRecordRepository.get_by_patient_id(db, patient_id)
        return [MedicalRecordListItem.model_validate(r) for r in records]

    @staticmethod
    async def get_record_detail(
        db: AsyncSession,
        record_id: int,
    ) -> MedicalRecordDetailResponse:
        record = await MedicalRecordRepository.get_by_id(db, record_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료기록을 찾을 수 없습니다.",
            )

        xray_image_url = await MedicalRecordRepository.get_latest_xray_image_url(
            db, record_id
        )

        return MedicalRecordDetailResponse(
            id=record.id,
            patient_id=record.patient_id,
            chart_number=record.chart_number,
            symptoms=record.symptoms,
            xray_image_url=xray_image_url,
            created_at=record.created_at,
        )