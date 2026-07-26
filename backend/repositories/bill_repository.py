"""
backend.repositories.bill_repository — Bill data access operations.
"""
from __future__ import annotations

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.database.models import BillRecord
from backend.repositories.base_repository import BaseRepository


class BillRepository(BaseRepository[BillRecord]):
    """Repository handling BillRecord persistence and status queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BillRecord, session)

    async def get_by_hash(self, bill_hash: str) -> Optional[BillRecord]:
        """Fetch bill record by SHA-256 binary hash."""
        result = await self.session.execute(
            select(BillRecord).where(BillRecord.bill_hash == bill_hash)
        )
        return result.scalars().first()

    async def update_status(
        self,
        bill_hash: str,
        status: str,
        progress_pct: int = 0,
        stage_message: str = "",
        error_message: Optional[str] = None,
    ) -> bool:
        """Update processing status and progress for a bill."""
        stmt = (
            update(BillRecord)
            .where(BillRecord.bill_hash == bill_hash)
            .values(
                status=status,
                progress_pct=progress_pct,
                stage_message=stage_message,
                error_message=error_message,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
