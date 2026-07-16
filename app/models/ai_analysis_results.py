# app/models/ai_analysis_result.py
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db.databases import Base

class Prediction(str, enum.Enum):
    NORMAL = "normal"
    PNEUMONIA = "pneumonia"

class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("medical_records.id"), nullable=False) 
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    heatmap_url: Mapped[str | None] = mapped_column(String(255), nullable=True) 
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False) 
    
    # 외래키 설정 (xray_images 테이블의 id를 바라봄)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow) 
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # 관계 설정
    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="ai_analysis_results")