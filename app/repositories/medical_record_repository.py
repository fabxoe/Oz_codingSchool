from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage


class MedicalRecordRepository:

    @staticmethod
    async def get_by_patient_id(
        db: AsyncSession,
        patient_id: int,
    ) -> list[MedicalRecord]:
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
        result = await db.execute(
            select(MedicalRecord).where(MedicalRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_chart_number(
        db: AsyncSession,
        chart_number: str,
    ) -> MedicalRecord | None:
        result = await db.execute(
            select(MedicalRecord).where(
                MedicalRecord.chart_number == chart_number
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_latest_xray_image_url(
        db: AsyncSession,
        record_id: int,
    ) -> str | None:
        statement = (
            select(XrayImage.image_url)
            .where(XrayImage.record_id == record_id)
            .order_by(XrayImage.created_at.desc())
        )
        result = await db.execute(statement)
        return result.scalars().first()

    @staticmethod
    async def get_image_urls_by_patient(
        db: AsyncSession,
        patient_id: int,
    ) -> list[str]:
        statement = (
            select(XrayImage.image_url)
            .join(MedicalRecord, XrayImage.record_id == MedicalRecord.id)
            .where(MedicalRecord.patient_id == patient_id)
        )
        result = await db.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def create_with_image(
        db: AsyncSession,
        record: MedicalRecord,
        image_url: str,
        uploader_id: int,
        shooting_datetime: datetime,
    ) -> MedicalRecord:
        db.add(record)
        await db.flush()

        db.add(
            XrayImage(
                record_id=record.id,
                uploader_id=uploader_id,
                image_url=image_url,
                shooting_datetime=shooting_datetime,
            )
        )

        await db.commit()
        await db.refresh(record)
        return record
