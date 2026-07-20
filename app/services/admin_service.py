from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Department, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRoleUpdateRequest


class AdminService:
    @staticmethod
    async def get_users(
        db: AsyncSession,
        query: str | None = None,
        department: Department | None = None,
    ) -> list[User]:
        return await UserRepository.get_all(
            db,
            query=query,
            department=department,
        )

    @staticmethod
    async def update_user_role(
        db: AsyncSession,
        payload: UserRoleUpdateRequest,
        current_user: User,
    ) -> User:
        if payload.user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자는 본인의 역할을 변경할 수 없습니다.",
            )

        target_user = await UserRepository.get_by_id(db, payload.user_id)

        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다.",
            )

        return await UserRepository.update_role(
            db,
            target_user,
            payload.new_role,
        )
