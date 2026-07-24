from app.core.db.databases import Base

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, String, Text, BigInteger, ForeignKey, SmallInteger, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.user import Gender

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=func.now())

    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        back_populates="patient",
        passive_deletes=True,
    )
