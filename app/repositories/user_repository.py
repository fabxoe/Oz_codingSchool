from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Department, Role, User


class UserRepository:

    @staticmethod
    async def get_by_email(
        db: AsyncSession,
        email: str,
    ) -> User | None:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        user_id: int,
    ) -> User | None:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        user: User,
    ) -> User:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_all(
        db: AsyncSession,
        query: str | None = None,
        department: Department | None = None,
    ) -> list[User]:
        statement = select(User)

        if query:
            search_pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    User.name.like(search_pattern),
                    User.email.like(search_pattern),
                )
            )

        if department is not None:
            statement = statement.where(User.department == department)

        result = await db.execute(statement.order_by(User.id))
        return list(result.scalars().all())

    @staticmethod
    async def update_role(
        db: AsyncSession,
        user: User,
        new_role: Role,
    ) -> User:
        user.role = new_role
        await db.commit()
        await db.refresh(user)
        return user
