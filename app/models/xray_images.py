# app/models/xray_image.py
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db.databases import Base

class XrayImage(Base):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    
    # 외래키 설정 (medical_records 테이블의 id를 바라봄)
    medical_record_id: Mapped[int] = mapped_column(ForeignKey("medical_records.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # 관계 설정
    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="xray_images")
    ai_analysis_results: Mapped[list["AIAnalysisResult"]] = relationship(back_populates="xray_image")