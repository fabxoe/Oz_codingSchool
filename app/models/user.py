import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.databases import Base

class Gender(str, enum.Enum):
    M = "male"
    F = "female"


class Role(str, enum.Enum):
    PENDING = "pending"
    STAFF = "staff"
    ADMIN = "admin"


class Department(str, enum.Enum):
    MEDICAL = "medical"
    DEV = "dev"
    RESEARCH = "research"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(20)
    )

    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True
    )

    gender: Mapped[Gender] = mapped_column(
        Enum(Gender),
        nullable=False
    )

    department: Mapped[Department] = mapped_column(
        Enum(Department),
        nullable=False
    )

    role: Mapped[Role] = mapped_column(
        Enum(Role),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime
    )