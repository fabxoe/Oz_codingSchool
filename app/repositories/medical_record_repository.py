from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage


class MedicalRecordRepository:
    """진료기록 테이블에 대한 DB 조회를 모아둔 클래스."""

    @staticmethod
    async def get_by_patient_id(
        db: AsyncSession,
        patient_id: int,
    ) -> list[MedicalRecord]:
        # 특정 환자의 진료기록 목록을 최신순으로 조회
        statement = (
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.created_at.desc())
        )
        result = await db.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        record_id: int,
    ) -> MedicalRecord | None:
        statement = select(MedicalRecord).where(MedicalRecord.id == record_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_latest_xray_image_url(
        db: AsyncSession,
        record_id: int,
    ) -> str | None:
        # 진료기록에 연결된 X-Ray 이미지 중 가장 최근 것의 URL을 반환
        statement = (
            select(XrayImage.image_url)
            .where(XrayImage.record_id == record_id)
            .order_by(XrayImage.created_at.desc())
        )
        result = await db.execute(statement)
        return result.scalars().first()