from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.user import Gender


class PatientRepository:

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

        statement = select(Patient)

        if name:
            statement = statement.where(
                Patient.name.like(f"%{name}%")
            )

        if gender:
            statement = statement.where(
                Patient.gender == gender
            )

        if min_age is not None:
            statement = statement.where(
                Patient.age >= min_age
            )

        if max_age is not None:
            statement = statement.where(
                Patient.age <= max_age
            )

        result = await db.execute(
            statement.order_by(Patient.id)
        )

        return list(result.scalars().all())

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
    ):
        await db.delete(patient)
        await db.commit()