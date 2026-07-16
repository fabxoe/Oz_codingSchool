"""사용자 데이터 접근 계층.

DB 쿼리만 담당한다. 비즈니스 판단(중복이면 409 등)은 service가 한다.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Department
from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """id로 사용자를 조회한다. (담당 3 — get_current_user에서 사용)"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """이메일로 사용자를 조회한다. (로그인, 중복 검사용)"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> User | None:
    """휴대폰 번호로 사용자를 조회한다. (중복 검사용)"""
    result = await db.execute(
        select(User).where(User.phone_number == phone_number)
    )
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    search: str | None = None,
    department: Department | None = None,
) -> list[User]:
    """[REQ-USER-004] 전체 사용자 목록을 검색/필터하여 조회한다.

    search: 이메일 또는 이름 부분 검색 (OR)
    department: 부서 필터 (AND)
    """
    stmt = select(User)

    if search:
        stmt = stmt.where(
            or_(
                User.email.contains(search),
                User.name.contains(search),
            )
        )
    if department:
        stmt = stmt.where(User.department == department)

    result = await db.execute(stmt.order_by(User.id))
    return list(result.scalars().all())


async def save(db: AsyncSession, user: User) -> User:
    """사용자를 저장하고 DB가 채운 값(id, created_at)을 반영한다."""
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete(db: AsyncSession, user: User) -> None:
    """사용자를 삭제한다. (Hard Delete)"""
    await db.delete(user)
    await db.commit()
