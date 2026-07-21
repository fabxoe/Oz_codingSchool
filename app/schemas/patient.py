from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Gender


class PatientCreateRequest(BaseModel):
    name: str
    age: int
    gender: Gender
    phone_number: str


class PatientUpdateRequest(BaseModel):
    name: str | None = None
    phone_number: str | None = None


class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: Gender

    phone_number: str = Field(validation_alias="phone")

    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)