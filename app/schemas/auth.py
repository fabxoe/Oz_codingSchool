"""인증·사용자 관련 요청/응답 스키마.

담당 1: 인증 스키마 정의
"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Department, Gender, Role

# 프론트엔드(static/apis.js)의 에러 메시지와 동일한 규칙:
# "비밀번호는 대소문자, 특수문자, 숫자를 각 1개씩 포함한 8자리 이상이어야 합니다."
PASSWORD_MESSAGE = "비밀번호는 대소문자, 특수문자, 숫자를 각 1개씩 포함한 8자리 이상이어야 합니다."
SPECIAL_PATTERN = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]/\\~`';]")


def validate_password_rule(value: str) -> str:
    """비밀번호 정책 검증 (대문자·소문자·숫자·특수문자 각 1개 이상, 8자 이상)."""
    if len(value) < 8:
        raise ValueError(PASSWORD_MESSAGE)
    if not re.search(r"[A-Z]", value):
        raise ValueError(PASSWORD_MESSAGE)
    if not re.search(r"[a-z]", value):
        raise ValueError(PASSWORD_MESSAGE)
    if not re.search(r"[0-9]", value):
        raise ValueError(PASSWORD_MESSAGE)
    if not SPECIAL_PATTERN.search(value):
        raise ValueError(PASSWORD_MESSAGE)
    return value


# ------------------------------------------------------------
# 요청 스키마
# ------------------------------------------------------------


class UserSignUpRequest(BaseModel):
    """[REQ-USER-001] 회원가입 요청."""

    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., max_length=128)
    name: str = Field(..., min_length=2, max_length=20)
    department: Department
    gender: Gender
    phone_number: str = Field(..., min_length=9, max_length=20)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_rule(v)


class UserUpdateRequest(BaseModel):
    """[REQ-USER-007] 회원 정보 수정 요청 (Partial Update)."""

    department: Department | None = None
    phone_number: str | None = Field(None, min_length=9, max_length=20)


class PasswordChangeRequest(BaseModel):
    """[REQ-USER-008] 비밀번호 변경 요청."""

    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_rule(v)


class RoleUpdateRequest(BaseModel):
    """[REQ-USER-005] 회원 권한 변경 요청 (관리자 전용)."""

    user_id: int = Field(..., ge=1)
    role: Role


# ------------------------------------------------------------
# 응답 스키마
# ------------------------------------------------------------


class UserResponse(BaseModel):
    """사용자 응답. hashed_password는 절대 포함하지 않는다."""

    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """로그인·토큰 재발급 응답. Refresh Token은 쿠키로 전달하므로 여기 없다."""

    access_token: str
    token_type: str = "bearer"
