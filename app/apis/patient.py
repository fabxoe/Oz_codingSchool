from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.databases import async_get_db as get_db
from app.models.user import User, Role
from app.models.patient import Gender
from app.core.security import get_current_user
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse
from app.services.patient import PatientService

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])

# 권한 검사 디펜던시 (staff 또는 admin만 허용)
def require_staff_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {Role.STAFF, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )
    return current_user

@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin)
):
    service = PatientService(db)
    return await service.create_patient(payload)

@router.get("", response_model=list[PatientResponse])
async def list_patients(
    name: str | None = None,
    gender: Gender | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PatientService(db)
    return await service.get_patient_list(name=name, gender=gender, min_age=min_age, max_age=max_age)

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PatientService(db)
    return await service.get_patient_detail(patient_id)

@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PatientService(db)
    return await service.update_patient(patient_id, payload)

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = PatientService(db)
    await service.delete_patient(patient_id)