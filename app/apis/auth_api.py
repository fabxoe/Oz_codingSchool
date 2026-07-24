from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.schemas.user import (
    LoginResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)
from app.services.user_service import UserService

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Auth"],
)


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    payload: UserSignupRequest,
    db: AsyncSession = Depends(async_get_db),
):
    return await UserService.signup(
        db,
        payload,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(async_get_db),
):
    payload = UserLoginRequest(
        email=form_data.username,
        password=form_data.password,
    )
    result = await UserService.login(
        db,
        payload,
    )

    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )

    return LoginResponse(
        access_token=result["access_token"],
        token_type="Bearer",
    )
