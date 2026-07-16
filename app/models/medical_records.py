# app/models/medical_record.py
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db.databases import Base

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    chart_number: Mapped[str] = mapped_column(String(50), nullable=False)
    symptoms: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # 관계 설정
    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    xray_images: Mapped[list["XRayImage"]] = relationship(back_populates="medical_record")
    ai_analysis_results: Mapped[list["AIAnalysisResult"]] = relationship(back_populates="medical_record")