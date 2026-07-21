from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.user import Gender
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreateRequest


class PatientService:

    @staticmethod
    async def create(
        db: AsyncSession,
        payload: PatientCreateRequest,
    ) -> Patient:

        patient = Patient(
            name=payload.name,
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone_number,
        )

        return await PatientRepository.create(
            db,
            patient,
        )

    @staticmethod
    async def get_all(
        db: AsyncSession,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[Patient]:

        return await PatientRepository.get_all(
            db,
            name=name,
            gender=gender,
            min_age=min_age,
            max_age=max_age,
        )