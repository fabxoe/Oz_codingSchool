import re

from fastapi import HTTPException, status
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
    UserLoginRequest,
    UserPasswordUpdateRequest,
    UserSignupRequest,
    UserUpdateRequest,
)


class UserService:

    @staticmethod
    def validate_password(password: str) -> None:
        is_valid = (
            8 <= len(password) <= 20
            and re.search(r"[A-Z]", password)
            and re.search(r"[a-z]", password)
            and re.search(r"\d", password)
            and re.search(r"[^A-Za-z0-9]", password)
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "비밀번호는 대소문자, 특수문자, 숫자를 각 1개씩 "
                    "포함한 8자 이상 20자 이하여야 합니다."
                ),
            )

    @staticmethod
    async def signup(
        db: AsyncSession,
        payload: UserSignupRequest,
    ) -> User:

        UserService.validate_password(payload.password)

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

        existing_phone = await UserRepository.get_by_phone_number(
            db,
            payload.phone_number,
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 휴대폰 번호입니다.",
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

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
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

    @staticmethod
    async def update_me(
        db: AsyncSession,
        user: User,
        payload: UserUpdateRequest,
    ) -> User:
        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 정보를 입력해야 합니다.",
            )

        phone_number = update_data.get("phone_number")
        if phone_number is not None:
            existing_user = await UserRepository.get_by_phone_number(
                db,
                phone_number,
            )
            if existing_user is not None and existing_user.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 존재하는 휴대폰 번호입니다.",
                )

        for field, value in update_data.items():
            setattr(user, field, value)

        return await UserRepository.update(db, user)

    @staticmethod
    async def update_password(
        db: AsyncSession,
        user: User,
        payload: UserPasswordUpdateRequest,
    ) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기존 비밀번호가 일치하지 않습니다.",
            )

        UserService.validate_password(payload.new_password)
        user.hashed_password = hash_password(payload.new_password)
        await UserRepository.update(db, user)

    @staticmethod
    async def delete_me(
        db: AsyncSession,
        user: User,
    ) -> None:
        await UserRepository.delete(db, user)
