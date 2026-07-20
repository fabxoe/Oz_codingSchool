from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserSignupRequest,
    UserLoginRequest,
)


class UserService:

    @staticmethod
    async def signup(
        db: AsyncSession,
        payload: UserSignupRequest,
    ) -> User:

        # 이메일 중복 검사
        existing_user = await UserRepository.get_by_email(
            db,
            payload.email,
        )

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="이미 존재하는 이메일입니다.",
            )

        # 비밀번호 해시
        hashed_password = hash_password(payload.password)

        # User 객체 생성
        user = User(
            email=payload.email,
            hashed_password=hashed_password,
            name=payload.name,
            phone_number=payload.phone_number,
            gender=payload.gender,
            department=payload.department,
            role=Role.PENDING,
        )

        # DB 저장
        return await UserRepository.create(
            db,
            user,
        )

    @staticmethod
    async def login(
        db: AsyncSession,
        payload: UserLoginRequest,
    ) -> dict:

        user = await UserRepository.get_by_email(
            db,
            payload.email,
        )

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        if not verify_password(
            payload.password,
            user.hashed_password,
        ):
            raise HTTPException(
                status_code=401,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
        }