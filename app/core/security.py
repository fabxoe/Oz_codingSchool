"""인증·인가 공통 모듈.

담당 1: Argon2 해시, JWT 생성
담당 3: JWT 검증 dependency (get_current_user)   ★ 권일준 담당
담당 5: 역할 기반 인가 (require_roles)
"""


from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.models.enums import Role
from app.models.user import User


# ============================================================
# Argon2 비밀번호 해싱
# ============================================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """평문 비밀번호를 Argon2 해시로 변환한다."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 저장된 해시를 검증한다.

    Argon2는 salt가 해시 문자열에 포함되므로 같은 비밀번호도 매번 다른 해시가
    나온다. 따라서 해시끼리 직접 비교하지 않고 반드시 verify()를 사용한다.
    """
    return password_hash.verify(plain_password, hashed_password)


# ============================================================
# JWT 생성
# ============================================================

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """JWT를 생성한다.

    payload 구성은 팀 공통 기준으로 고정한다: sub, type, iat, exp
    민감 정보는 넣지 않는다 (payload는 누구나 디코딩 가능).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: int) -> str:
    """Access Token 발급 (만료 30분)."""
    return create_token(
        subject=str(user_id),
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """Refresh Token 발급 (만료 7일)."""
    return create_token(
        subject=str(user_id),
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


# ============================================================
# ★ 담당 3 (권일준) — JWT 검증 및 인증 dependency
# ============================================================

bearer_scheme = HTTPBearer()


def decode_token(token: str, expected_type: str) -> int:
    """JWT를 검증하고 user_id를 반환한다.

    검증 항목:
      1. 서명 (JWT_SECRET_KEY)
      2. 만료 시각 (exp) — jwt.decode가 자동 검사
      3. 토큰 종류 (type) — Refresh Token으로 일반 API 호출 차단

    Raises:
        HTTPException(401): 검증 실패
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        # type 검사가 없으면 Refresh Token으로도 일반 API를 호출할 수 있다.
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{expected_type} 토큰이 아닙니다.",
            )
        return int(payload["sub"])
    except HTTPException:
        raise
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(async_get_db),
) -> User:
    """[담당 3] Access Token을 검증하여 현재 로그인 사용자를 반환한다.

    흐름:
        Authorization 헤더 확인 → Bearer Token 추출
        → JWT 서명·만료·type 검증 → sub에서 user_id 추출
        → DB에서 사용자 조회 → 현재 사용자 반환

    이 dependency는 **인증만** 담당한다.
    역할(role) 검사는 require_roles가 담당한다.
    """
    # 순환 import 방지 (repositories → models → ... → security)
    from app.repositories.user import get_user_by_id

    user_id = decode_token(credentials.credentials, ACCESS_TOKEN_TYPE)

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증된 사용자를 찾을 수 없습니다.",
        )
    return user




# ============================================================
# 역할 기반 인가
# ============================================================


def require_roles(*allowed_roles: Role):
    """지정한 역할만 통과시키는 dependency를 생성한다.

    사용 예:
        current_user: User = Depends(require_roles(Role.ADMIN))

    401(인증 실패)과 403(권한 부족)을 구분한다.
    """

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="접근 권한이 없습니다.",
            )
        return current_user

    return checker


require_admin = require_roles(Role.ADMIN)
require_staff = require_roles(Role.STAFF, Role.ADMIN)