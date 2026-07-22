"""AI 예측 결과 데이터 접근 계층.

DB 쿼리만 담당한다. 업무 판단(404, 422 등)은 service가 한다.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis_result import AIAnalysisResult
from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage


class PredictionRepository:

    @staticmethod
    async def get_medical_record(
        db: AsyncSession,
        record_id: int,
    ) -> MedicalRecord | None:
        result = await db.execute(
            select(MedicalRecord).where(MedicalRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_latest_xray_url(
        db: AsyncSession,
        record_id: int,
    ) -> str | None:
        """진료기록에 연결된 X-ray 이미지 URL (가장 최근 것)."""
        result = await db.execute(
            select(XrayImage.image_url)
            .where(XrayImage.record_id == record_id)
            .order_by(XrayImage.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_cached_result(
        db: AsyncSession,
        record_id: int,
        ai_model: str,
    ) -> AIAnalysisResult | None:
        """[REQ-PRED-001] 같은 진료기록 + 같은 모델의 예측 결과가 이미 있는지 확인.

        있으면 추론을 다시 하지 않고 저장된 값을 반환한다.
        """
        result = await db.execute(
            select(AIAnalysisResult)
            .where(
                AIAnalysisResult.record_id == record_id,
                AIAnalysisResult.ai_model == ai_model,
            )
            .order_by(AIAnalysisResult.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        result_id: int,
    ) -> AIAnalysisResult | None:
        result = await db.execute(
            select(AIAnalysisResult).where(AIAnalysisResult.id == result_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_by_record(
        db: AsyncSession,
        record_id: int,
    ) -> list[AIAnalysisResult]:
        """[REQ-PRED-002] 진료기록의 예측 결과 목록 (최신순)."""
        result = await db.execute(
            select(AIAnalysisResult)
            .where(AIAnalysisResult.record_id == record_id)
            .order_by(AIAnalysisResult.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(
        db: AsyncSession,
        record_id: int,
        is_pneumonia: bool,
        confidence: float,
        ai_model: str,
        heatmap_url: str | None = None,
    ) -> AIAnalysisResult:
        result = AIAnalysisResult(
            record_id=record_id,
            is_pneumonia=is_pneumonia,
            confidence=Decimal(str(round(confidence, 4))),
            heatmap_url=heatmap_url,
            ai_model=ai_model,
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)
        return result
