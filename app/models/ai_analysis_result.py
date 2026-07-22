from app.core.db.databases import Base
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, Boolean, Numeric, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal

class AIAnalysisResult(Base):
    __tablename__= "ai_analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # 모델이 반환하는 0.9821 이 Numeric(5,2) 에서는 0.98 로 잘리므로 소수점 4자리로 저장한다.
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    # 현재 모델(pneumonia_ensemble_v1)은 히트맵을 생성하지 않으므로 선택사항으로 둔다.
    heatmap_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=func.now())

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="ai_analysis_results")
