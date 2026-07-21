"""환자·진료기록 데이터 접근 계층.

DB 쿼리만 담당한다. 업무 판단(404, 409 등)은 service가 한다.
"""

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import Gender
from app.models.xray_image import XrayImage


class PatientRepository:

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        patient_id: int,
    ) -> Patient | None:
        result = await db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[Patient]:
        """[REQ-PTNT-002] 이름 검색 + 성별·나이범위 필터."""
        statement = select(Patient)

        if name:
            statement = statement.where(Patient.name.like(f"%{name}%"))

        if gender is not None:
            statement = statement.where(Patient.gender == gender)

        if min_age is not None:
            statement = statement.where(Patient.age >= min_age)

        if max_age is not None:
            statement = statement.where(Patient.age <= max_age)

        result = await db.execute(statement.order_by(Patient.id))
        return list(result.scalars().all())

    @staticmethod
    async def create(
        db: AsyncSession,
        patient: Patient,
    ) -> Patient:
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return patient

    @staticmethod
    async def update(
        db: AsyncSession,
        patient: Patient,
    ) -> Patient:
        await db.commit()
        await db.refresh(patient)
        return patient

    @staticmethod
    async def delete(
        db: AsyncSession,
        patient: Patient,
    ) -> None:
        """[REQ-PTNT-005] 환자 삭제. 진료기록·X-ray도 함께 삭제된다.

        session.delete(patient) 를 쓰지 않는 이유:
        ORM이 patient.medical_records 관계를 먼저 로드하려 하는데,
        비동기 세션에서는 lazy loading 이 불가능해 MissingGreenlet 이 발생한다.
        또한 모델에 cascade 설정이 없어 ORM은 자식의 patient_id 를 NULL 로
        만들려 하지만 해당 컬럼은 nullable=False 다.

        DB 외래키에 ON DELETE CASCADE 가 걸려 있으므로,
        Core delete() 문으로 DB가 직접 연쇄 삭제하도록 맡긴다.
        """
        await db.execute(sa_delete(Patient).where(Patient.id == patient.id))
        await db.commit()


class MedicalRecordRepository:

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        record_id: int,
    ) -> MedicalRecord | None:
        """상세 조회 — X-ray 이미지를 함께 로드한다.

        selectinload 를 쓰지 않으면 비동기 세션에서 record.xray_images 접근 시
        MissingGreenlet 에러가 난다 (lazy loading 불가).
        """
        result = await db.execute(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_chart_number(
        db: AsyncSession,
        chart_number: str,
    ) -> MedicalRecord | None:
        """차트번호 중복 검사용."""
        result = await db.execute(
            select(MedicalRecord).where(
                MedicalRecord.chart_number == chart_number
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_by_patient(
        db: AsyncSession,
        patient_id: int,
    ) -> list[MedicalRecord]:
        """[REQ-MDR-002] 특정 환자의 진료기록 목록 (최신순)."""
        result = await db.execute(
            select(MedicalRecord)
            .where(MedicalRecord.patient_id == patient_id)
            .order_by(MedicalRecord.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_with_image(
        db: AsyncSession,
        record: MedicalRecord,
        image_url: str,
        uploader_id: int,
        shooting_datetime,
    ) -> MedicalRecord:
        """진료기록과 X-ray 이미지를 한 트랜잭션으로 저장한다.

        flush() 로 record.id 를 먼저 확보한 뒤 XrayImage 를 연결하고,
        마지막에 commit() 으로 한 번에 확정한다.
        """
        db.add(record)
        await db.flush()  # commit 없이 id 확보

        xray = XrayImage(
            record_id=record.id,
            uploader_id=uploader_id,
            image_url=image_url,
            shooting_datetime=shooting_datetime,
        )
        db.add(xray)

        await db.commit()
        await db.refresh(record)
        return record
