from app.core.db.databases import Base
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, Boolean, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from decimal import Decimal

class AIAnalysisResult(Base):
    __tablename__= "ai_analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    heatmap_url: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)