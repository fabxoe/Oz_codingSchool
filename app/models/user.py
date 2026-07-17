from app.core.db.databases import Base
import enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, String, BigInteger,text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"

class Role(str, enum.Enum):
    PENDING = "pending"
    STAFF = "staff"
    ADMIN = "admin"


class Department(str, enum.Enum):
    MEDICAL = "medical"
    DEV = "dev"
    RESEARCH = "research"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    department: Mapped[Department] = mapped_column(Enum(Department), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=func.now())
    
    uploaded_xrays: Mapped[list["XrayImage"]] = relationship(back_populates="uploader")