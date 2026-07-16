"""User API 엔드포인트.

경로·상태코드는 팀 공통 기준 문서를 따른다. 임의 변경 금지.

담당 2: 회원가입, 로그인
담당 3: get_current_user 적용, /users/me 전반   ★ 권일준
담당 4: 토큰 재발급, 로그아웃
담당 5: 관리자 API
"""

from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    decode_token,
    get_current_user,
    require_admin,
)
from app.models.enums import Department
from app.models.user import User
from app.schemas.auth import (
    PasswordChangeRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserResponse,
    UserSignUpRequest,
    UserUpdateRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/api/v1", tags=["users"])

REFRESH_COOKIE_KEY = "refresh_token"
# 팀 공통 기준: HttpOnly=True, Secure=False(local), SameSite=lax, Path=/
REFRESH_COOKIE_OPTIONS = {
    "httponly": True,
    "secure": False,  # 운영 환경에서는 True (HTTPS)
    "samesite": "lax",
    "path": "/",
}


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **REFRESH_COOKIE_OPTIONS,
    )


# ============================================================
# 담당 2 — 회원가입 / 로그인
# ============================================================


# [REQ-USER-001] 사내 의료인, 개발 실무진은 회원가입을 통해 서비스를 이용할 수 있다.
@router.post(
    "/users/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def signup(
    payload: UserSignUpRequest,
    db: AsyncSession = Depends(async_get_db),
):
    return await auth_service.sign_up(db, payload)


# [REQ-USER-002] 가입된 이메일과 비밀번호로 로그인을 할 수 있다.
# [NFR-USER-001] Access Token은 JSON body, Refresh Token은 HTTP-only Cookie
@router.post(
    "/users/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="로그인",
)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(async_get_db),
):
    # OAuth2 규격상 필드명이 username 이며, 여기에 이메일을 넣는다.
    user = await auth_service.authenticate(
        db, form_data.username, form_data.password
    )
    access_token, refresh_token = auth_service.issue_tokens(user.id)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


# ============================================================
# 담당 4 — 토큰 재발급 / 로그아웃
# ============================================================


# [NFR-USER-001] 엑세스 토큰 만료 시 리프레시 토큰을 통해 재발급할 수 있다.
@router.post(
    "/users/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Access Token 재발급",
)
async def refresh(refresh_token: str | None = Cookie(default=None)):
    if refresh_token is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 없습니다.",
        )
    # type="refresh" 검사 — Access Token 제출을 허용하지 않는다.
    user_id = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
    return TokenResponse(access_token=create_access_token(user_id))


# [REQ-USER-003] 로그인 유저는 로그아웃을 진행할 수 있다.
@router.post(
    "/users/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    # 발급할 때와 동일한 조건이어야 브라우저가 쿠키를 삭제한다.
    response.delete_cookie(key=REFRESH_COOKIE_KEY, **REFRESH_COOKIE_OPTIONS)
    return None


# ============================================================
# ★ 담당 3 (권일준) — 마이페이지
# ============================================================


# [REQ-USER-006] 모든 로그인 유저는 마이페이지에서 본인의 정보를 확인할 수 있다.
@router.get(
    "/users/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="내 정보 조회",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """get_current_user 가 JWT 검증과 사용자 조회를 모두 처리하므로
    이 함수는 반환만 한다."""
    return current_user


# [REQ-USER-007] 모든 로그인 유저는 마이페이지에서 본인의 정보를 수정할 수 있다.
@router.patch(
    "/users/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="내 정보 수정",
)
async def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    return await auth_service.update_me(db, current_user, payload)


# [REQ-USER-008] 모든 로그인 유저는 계정의 비밀번호를 변경할 수 있다.
@router.patch(
    "/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="비밀번호 변경",
)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await auth_service.change_password(db, current_user, payload)
    return None


# [REQ-USER-009] 모든 로그인 유저는 회원탈퇴를 진행할 수 있다.
@router.delete(
    "/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
)
async def withdraw(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    await auth_service.withdraw(db, current_user)
    response.delete_cookie(key=REFRESH_COOKIE_KEY, **REFRESH_COOKIE_OPTIONS)
    return None


# ============================================================
# 담당 5 — 관리자
# ============================================================


# [REQ-USER-004] 관리자 권한 유저는 모든 회원을 목록으로 조회할 수 있다.
@router.get(
    "/admin/users",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="회원 목록 조회 (관리자)",
)
async def admin_list_users(
    search: str | None = None,
    department: Department | None = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(async_get_db),
):
    return await auth_service.list_all_users(
        db, search=search, department=department
    )


# [REQ-USER-005] 관리자 권한 유저는 다른 유저의 권한을 변경할 수 있다.
@router.patch(
    "/admin/users/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="회원 권한 변경 (관리자)",
)
async def admin_update_role(
    payload: RoleUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(async_get_db),
):
    return await auth_service.update_role(db, payload)
