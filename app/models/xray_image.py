from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.databases import Base


class XrayImage(Base):
    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False
    )
    uploader_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    shooting_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    ) 