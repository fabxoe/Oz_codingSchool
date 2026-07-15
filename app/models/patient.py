from datetime import datetime

from sqlalchemy import DateTime, Enum, SmallInteger, String
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.databases import Base
from app.models.user import Gender


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    age: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False
    )

    gender: Mapped[Gender] = mapped_column(
        Enum(Gender),
        nullable=True
    )

    phone: Mapped[str] = mapped_column(
        String(11),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime
    )