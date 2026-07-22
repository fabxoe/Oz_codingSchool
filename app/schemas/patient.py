from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.models.user import Gender


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=30, description="환자 이름")
    age: int = Field(ge=0, description="환자 나이")
    gender: Gender = Field(description="환자 성별")
    phone_number: str = Field(
        min_length=10,
        max_length=11,
        pattern=r"^\d+$",
        description="숫자만 입력한 휴대폰 번호",
    )


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    phone_number: str | None = Field(
        default=None,
        min_length=10,
        max_length=11,
        pattern=r"^\d+$",
    )


class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: Gender
    phone_number: str = Field(
        validation_alias=AliasChoices("phone_number", "phone")
    )
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
