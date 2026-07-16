"""인증·사용자 비즈니스 로직 계층.

HTTP를 모르는 계층이지만, 이번 과제 규모에서는 HTTPException을 직접 사용한다.
(실무에서는 도메인 예외를 정의하고 API 계층에서 HTTP로 변환하는 편이 낫다.)
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.enums import Department, Role
from app.models.user import User
from app.repositories import user as user_repo
from app.schemas.auth import (
    PasswordChangeRequest,
    RoleUpdateRequest,
    UserSignUpRequest,
    UserUpdateRequest,
)


# ------------------------------------------------------------
# 담당 2 — 회원가입 / 로그인
# ------------------------------------------------------------


async def sign_up(db: AsyncSession, payload: UserSignUpRequest) -> User:
    """[REQ-USER-001] 회원가입.

    흐름: 이메일/휴대폰 중복 확인 → Argon2 해시 생성 → User 저장
    """
    if await user_repo.get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )
    if await user_repo.get_user_by_phone(db, payload.phone_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 휴대폰 번호입니다.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),  # 평문 저장 금지
        name=payload.name,
        department=payload.department,
        gender=payload.gender,
        role=Role.PENDING,  # 가입 시 기본 권한
        is_active=True,
    )
    user.phone_number = payload.phone_number
    return await user_repo.save(db, user)


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    """[REQ-USER-002] 이메일/비밀번호 검증.

    보안: "이메일 없음"과 "비밀번호 틀림"을 구분하지 않는다.
    구분하면 공격자가 가입된 이메일 목록을 알아낼 수 있다 (계정 열거 공격).
    """
    user = await user_repo.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비활성화된 계정입니다.",
        )
    return user


def issue_tokens(user_id: int) -> tuple[str, str]:
    """Access Token과 Refresh Token을 발급한다."""
    return create_access_token(user_id), create_refresh_token(user_id)


# ------------------------------------------------------------
# 담당 3 — 마이페이지 (★ 권일준)
# ------------------------------------------------------------


async def update_me(
    db: AsyncSession, user: User, payload: UserUpdateRequest
) -> User:
    """[REQ-USER-007] 회원 정보 수정 (부서, 휴대폰 번호).

    exclude_unset=True 가 핵심이다. 이걸 빼면 전달하지 않은 필드까지
    None으로 덮어써서 데이터가 소실된다.
    """
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 항목이 없습니다.",
        )

    new_phone = data.get("phone_number")
    if new_phone and new_phone != user.phone_number:
        if await user_repo.get_user_by_phone(db, new_phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 휴대폰 번호입니다.",
            )

    for key, value in data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


async def change_password(
    db: AsyncSession, user: User, payload: PasswordChangeRequest
) -> None:
    """[REQ-USER-008] 비밀번호 변경.

    기존 비밀번호는 평문 비교가 아니라 해시 검증으로 확인한다.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="기존 비밀번호가 일치하지 않습니다.",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호가 기존 비밀번호와 동일합니다.",
        )

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()


async def withdraw(db: AsyncSession, user: User) -> None:
    """[REQ-USER-009] 회원 탈퇴 (Hard Delete).

    xray_images.uploader_id 는 ON DELETE SET NULL 이므로
    업로드한 X-ray 이미지 자체는 남고 업로더 정보만 NULL이 된다.
    """
    await user_repo.delete(db, user)


# ------------------------------------------------------------
# 담당 5 — 관리자
# ------------------------------------------------------------


async def list_all_users(
    db: AsyncSession,
    search: str | None = None,
    department: Department | None = None,
) -> list[User]:
    """[REQ-USER-004] 전체 회원 목록 조회 (관리자 전용)."""
    return await user_repo.list_users(db, search=search, department=department)


async def update_role(db: AsyncSession, payload: RoleUpdateRequest) -> User:
    """[REQ-USER-005] 회원 권한 변경 (관리자 전용)."""
    target = await user_repo.get_user_by_id(db, payload.user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 사용자입니다.",
        )

    target.role = payload.role
    await db.commit()
    await db.refresh(target)
    return target
