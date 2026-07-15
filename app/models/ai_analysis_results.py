# app/models/ai_analysis_result.py
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db.databases import Base

class Prediction(str, enum.Enum):
    NORMAL = "normal"
    PNEUMONIA = "pneumonia"

class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prediction: Mapped[Prediction] = mapped_column(Enum(Prediction), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # 외래키 설정 (xray_images 테이블의 id를 바라봄)
    xray_image_id: Mapped[int] = mapped_column(ForeignKey("xray_images.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # 관계 설정
    xray_image: Mapped["XrayImage"] = relationship(back_populates="ai_analysis_results")