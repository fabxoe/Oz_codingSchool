from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.dependencies import get_current_user  # 3번 담당자가 만드는 인증 dependency
from app.models.user import User
from app.services.auth import refresh_access_token

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
    return {"access_token": new_access_token, "token_type": "bearer"}


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