from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserPasswordUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.auth import refresh_access_token
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


# [REQ-USER-002 연계] Access Token 갱신
@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh(
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(async_get_db),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없습니다.",
        )

    new_access_token = await refresh_access_token(db, refresh_token)
    return {"access_token": new_access_token, "token_type": "Bearer"}


# [REQ-USER-003] 로그아웃할 수 있다.
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,  # 운영 환경에서는 True
        samesite="lax",
        path="/",
    )


# [REQ-USER-006] 내 정보 조회
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# [REQ-USER-007] 내 정보 수정
@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await UserService.update_me(db, current_user, payload)


# [REQ-USER-008] 비밀번호 변경
@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    payload: UserPasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await UserService.update_password(db, current_user, payload)


# [REQ-USER-009] 회원 탈퇴
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await UserService.delete_me(db, current_user)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
