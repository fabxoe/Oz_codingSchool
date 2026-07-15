from app.core.db.databases import Base

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, String, Text, BigInteger, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    chart_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)