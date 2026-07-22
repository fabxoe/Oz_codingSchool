from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.user import Gender
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreateRequest, PatientUpdateRequest

BASE_DIR = Path(__file__).resolve().parent.parent.parent


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
        return await PatientRepository.create(db, patient)

    @staticmethod
    async def get_all(
        db: AsyncSession,
        name: str | None = None,
        gender: Gender | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
    ) -> list[Patient]:
        if min_age is not None and max_age is not None and min_age > max_age:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최소 나이는 최대 나이보다 클 수 없습니다.",
            )

        return await PatientRepository.get_all(
            db,
            name=name,
            gender=gender,
            min_age=min_age,
            max_age=max_age,
        )

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        patient_id: int,
    ) -> Patient:
        patient = await PatientRepository.get_by_id(db, patient_id)
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="환자를 찾을 수 없습니다.",
            )
        return patient

    @staticmethod
    async def update(
        db: AsyncSession,
        patient_id: int,
        payload: PatientUpdateRequest,
    ) -> Patient:
        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목이 없습니다.",
            )

        patient = await PatientService.get_by_id(db, patient_id)
        if "name" in update_data:
            patient.name = update_data["name"]
        if "phone_number" in update_data:
            patient.phone = update_data["phone_number"]

        return await PatientRepository.update(db, patient)

    @staticmethod
    async def delete(
        db: AsyncSession,
        patient_id: int,
    ) -> None:
        patient = await PatientService.get_by_id(db, patient_id)
        image_urls = await MedicalRecordRepository.get_image_urls_by_patient(
            db,
            patient_id,
        )

        await PatientRepository.delete(db, patient)

        for image_url in image_urls:
            image_path = BASE_DIR / image_url.lstrip("/")
            image_path.unlink(missing_ok=True)
