from datetime import datetime
from app.core.db.databases import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, text

class XrayImage(Base):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    uploader_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False) 
    shooting_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="xray_images")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_xrays")