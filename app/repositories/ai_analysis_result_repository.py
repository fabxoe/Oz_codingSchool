from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis_result import AIAnalysisResult


class AIAnalysisResultRepository:

    @staticmethod
    async def get_by_record_id(
        db: AsyncSession,
        record_id: int,
    ) -> AIAnalysisResult | None:
        result = await db.execute(
            select(AIAnalysisResult)
            .where(AIAnalysisResult.record_id == record_id)
            .order_by(desc(AIAnalysisResult.created_at))
        )
        return result.scalars().first()

    @staticmethod
    async def create(
        db: AsyncSession,
        analysis: AIAnalysisResult,
    ) -> AIAnalysisResult:
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return analysis