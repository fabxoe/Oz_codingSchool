# app/schemas/patient.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.patient import Gender

class PatientCreate(BaseModel):
    name: str = Field(..., description="환자 이름")
    age: int = Field(..., ge=0, description="환자 나이")
    gender: Gender = Field(..., description="male 또는 female")
    phone_number: str = Field(..., description="휴대폰 번호")

class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, description="수정할 이름")
    phone_number: str | None = Field(default=None, description="수정할 휴대폰 번호")

class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: Gender
    phone_number: str = Field(validation_alias="phone")
    created_at: datetime
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)