"""
backend.database.session — Database session provider.

Exports helper functions for acquiring async and sync SQLAlchemy database sessions,
integrating directly with database/connection.py.
"""
from __future__ import annotations

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db, get_sync_session, check_db_health


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper yielding an AsyncSession."""
    async for session in get_db():
        yield session


__all__ = ["get_async_db", "get_sync_session", "check_db_health"]
