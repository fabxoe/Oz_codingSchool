from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import (
    PatientCreateRequest,
    PatientUpdateRequest,
)
from app.models.user import Gender


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
