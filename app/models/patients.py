# app/models/patient.py
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db.databases import Base

class PatientGender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[PatientGender] = mapped_column(Enum(PatientGender), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    # 외래키 설정 
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # 관계 설정
    medical_records: Mapped[list["MedicalRecord"]] = relationship(back_populates="patient")