from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user, require_roles
from app.models.user import Gender, Role, User
from app.schemas.patient import (
    PatientCreateRequest,
    PatientResponse,
    PatientUpdateRequest,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="환자 등록",
)
async def create_patient(
    payload: PatientCreateRequest,
    current_user: User = Depends(require_roles(Role.STAFF, Role.ADMIN)),
    db: AsyncSession = Depends(async_get_db),
):
    return await PatientService.create(db, payload)


@router.get(
    "",
    response_model=list[PatientResponse],
    status_code=status.HTTP_200_OK,
    summary="환자 목록 조회",
)
async def get_patients(
    name: str | None = Query(default=None),
    gender: Gender | None = Query(default=None),
    min_age: int | None = Query(default=None, ge=0),
    max_age: int | None = Query(default=None, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await PatientService.get_all(
        db,
        name=name,
        gender=gender,
        min_age=min_age,
        max_age=max_age,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="환자 상세 조회",
)
async def get_patient(
    patient_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await PatientService.get_by_id(db, patient_id)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="환자 정보 수정",
)
async def update_patient(
    payload: PatientUpdateRequest,
    patient_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await PatientService.update(db, patient_id, payload)


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="환자 삭제",
)
async def delete_patient(
    patient_id: int = Path(ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await PatientService.delete(db, patient_id)
