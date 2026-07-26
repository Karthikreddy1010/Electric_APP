"""
backend.repositories.analytics_repository — Analytics result persistence.
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database.models import AnalyticsRecord
from backend.repositories.base_repository import BaseRepository
from backend.schemas.analytics import AnalyticsResult


class AnalyticsRepository(BaseRepository[AnalyticsRecord]):
    """Repository handling AnalyticsRecord storage and retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AnalyticsRecord, session)

    async def get_latest_by_hash(self, bill_hash: str) -> Optional[AnalyticsRecord]:
        """Fetch latest calculated AnalyticsRecord by bill hash."""
        result = await self.session.execute(
            select(AnalyticsRecord)
            .where(AnalyticsRecord.bill_hash == bill_hash)
            .order_by(AnalyticsRecord.created_at.desc())
        )
        return result.scalars().first()

    async def save_analytics(self, bill_id: str, bill_hash: str, analytics: AnalyticsResult) -> AnalyticsRecord:
        """Persist a new AnalyticsResult object."""
        record = AnalyticsRecord(
            bill_id=bill_id,
            bill_hash=bill_hash,
            tenant_id=analytics.customer_id,
            analytics_version=analytics.analytics_version,
            ocr_version=analytics.ocr_version,
            parser_version=analytics.parser_version,
            tariff_version=analytics.tariff_version,
            weather_version=analytics.weather_version,
            usage_kwh=analytics.variable_charges.usage_kwh,
            total_bill=analytics.component_breakdown.total_bill,
            effective_rate=analytics.tariff_calculations.effective_volumetric_rate,
            confidence_score=analytics.confidence_score,
            analytics_result_json=analytics.model_dump(mode="json"),
        )
        return await self.add(record)
