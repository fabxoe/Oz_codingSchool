"""AI 폐렴 예측 요청/응답 스키마.

[REQ-PRED-001] 예측 실행
[REQ-PRED-002] 예측 결과 목록 조회
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PredictionResult(BaseModel):
    """단건 예측 결과."""

    id: int
    record_id: int
    is_pneumonia: bool
    confidence: Decimal
    heatmap_url: str | None
    ai_model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PredictionListItem(BaseModel):
    """[REQ-PRED-002] 목록의 한 항목."""

    id: int
    is_pneumonia: bool
    confidence: Decimal
    heatmap_url: str | None
    ai_model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PredictionListResponse(BaseModel):
    """[REQ-PRED-002] 진료기록의 X-ray 이미지와 예측 결과 목록."""

    record_id: int
    xray_image_url: str | None
    predictions: list[PredictionListItem]


class PredictionRequestResponse(BaseModel):
    """[REQ-PRED-001] 예측 요청 응답.

    캐시된 결과가 있으면 200 + result,
    새로 추론해야 하면 202 + job_id 가 채워진다.
    """

    status: str = Field(description="done | queued")
    cached: bool
    result: PredictionResult | None = None
    job_id: str | None = None
    poll_url: str | None = None


class PredictionJobResponse(BaseModel):
    """작업 상태 폴링 응답."""

    job_id: str
    record_id: int
    status: str = Field(description="queued | processing | done | failed")
    result: PredictionResult | None = None
    error: str | None = None
