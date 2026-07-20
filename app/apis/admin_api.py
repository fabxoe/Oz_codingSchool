from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import require_roles
from app.models.user import Department, Role, User
from app.schemas.user import UserResponse, UserRoleUpdateRequest
from app.services.admin_service import AdminService


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
)


@router.get(
    "/users",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
)
async def get_users(
    query: str | None = Query(default=None, max_length=255),
    department: Department | None = Query(default=None),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    return await AdminService.get_users(
        db,
        query=query,
        department=department,
    )


@router.patch(
    "/users/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user_role(
    payload: UserRoleUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    return await AdminService.update_user_role(
        db,
        payload,
        current_user,
    )
