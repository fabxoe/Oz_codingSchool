# app/repositories/patient.py
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.patient import Patient, Gender

class PatientRepository:
    # 1. ID 조회
    @staticmethod
    async def get_by_id(db: AsyncSession, patient_id: int) -> Patient | None:
        result = await db.execute(select(Patient).where(Patient.id == patient_id))
        return result.scalar_one_or_none()

    # 2. 전체 조회 및 조건 조회 (이름, 성별, 나이 범위 필터링)
    @staticmethod
    async def get_list(
        db: AsyncSession,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[Patient]:
        stmt = select(Patient)
        conditions = []

        if name:
            conditions.append(Patient.name.like(f"%{name}%"))
        if gender:
            conditions.append(Patient.gender == gender)
        if min_age is not None:
            conditions.append(Patient.age >= min_age)
        if max_age is not None:
            conditions.append(Patient.age <= max_age)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 3. 생성
    @staticmethod
    async def create(db: AsyncSession, patient: Patient) -> Patient:
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return patient

    # 4. 수정
    @staticmethod
    async def update(db: AsyncSession, patient: Patient) -> Patient:
        await db.commit()
        await db.refresh(patient)
        return patient

    # 5. 삭제
    @staticmethod
    async def delete(db: AsyncSession, patient: Patient) -> None:
        await db.delete(patient)
        await db.commit()