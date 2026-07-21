from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MedicalRecordListItem(BaseModel):
    """환자별 진료기록 목록 조회 응답 (요약)"""

    id: int
    chart_number: str
    symptoms: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicalRecordDetailResponse(BaseModel):
    """진료기록 상세 조회 응답"""

    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_image_url: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
