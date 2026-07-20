"""환자·진료기록 요청/응답 스키마.

주의: ORM 속성은 Patient.phone 이고, 프론트엔드 API 필드는 phone_number 다.
     service 계층에서 변환한다.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import Gender


# ------------------------------------------------------------
# 환자
# ------------------------------------------------------------


class PatientCreate(BaseModel):
    """[REQ-PTNT-001] 환자 정보 등록 요청."""

    name: str = Field(..., min_length=2, max_length=30)
    age: int = Field(..., ge=0, le=150)
    gender: Gender
    phone_number: str = Field(..., min_length=10, max_length=11)


class PatientUpdate(BaseModel):
    """[REQ-PTNT-004] 환자 정보 수정 요청 (이름, 연락처만)."""

    name: str | None = Field(None, min_length=2, max_length=30)
    phone_number: str | None = Field(None, min_length=10, max_length=11)


class PatientResponse(BaseModel):
    """[REQ-PTNT-002/003] 환자 응답."""

    id: int
    name: str
    age: int
    gender: Gender
    phone_number: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------
# 진료기록
# ------------------------------------------------------------


class MedicalRecordListResponse(BaseModel):
    """[REQ-MDR-002] 환자별 진료기록 목록 (요약)."""

    id: int
    chart_number: str
    symptoms: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicalRecordDetailResponse(BaseModel):
    """[REQ-MDR-003] 진료기록 상세 (X-ray 이미지 URL 포함)."""

    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
