from fastapi import APIRouter, Depends, Query, Response, status
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

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["Patients"],
)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_patient(
    payload: PatientCreateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(require_roles(Role.STAFF, Role.ADMIN)),
):
    return await PatientService.create(
        db,
        payload,
    )
