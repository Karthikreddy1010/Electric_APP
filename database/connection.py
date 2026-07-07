"""
Database Connection — async connection pool for PostgreSQL.

Provides both async (for FastAPI) and sync (for ETL/scripts) access patterns.
Falls back to SQLite for local development if PostgreSQL is unavailable.

Usage in FastAPI endpoints:
    async def my_endpoint(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Model))

Usage in ETL scripts:
    with get_sync_session() as session:
        session.add(record)
        session.commit()
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  CONNECTION URL RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE = f"sqlite:///{PROJECT_ROOT / 'data' / 'electricity.db'}"
DEFAULT_ASYNC_SQLITE = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'electricity.db'}"


def _get_database_url(async_mode: bool = False) -> str:
    """
    Resolve database URL from environment or config.

    Priority:
        1. DATABASE_URL environment variable
        2. DB_POSTGRES_* environment variables (assembled)
        3. SQLite fallback for local development
    """
    # Direct URL override
    url = os.environ.get("DATABASE_URL")
    if url:
        if async_mode and url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif async_mode and url.startswith("sqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    # Assemble from parts
    host = os.environ.get("DB_POSTGRES_HOST")
    if host:
        port = os.environ.get("DB_POSTGRES_PORT", "5432")
        user = os.environ.get("DB_POSTGRES_USER", "electric")
        password = os.environ.get("DB_POSTGRES_PASSWORD", "electric")
        dbname = os.environ.get("DB_POSTGRES_DB", "electricity_dw")

        if async_mode:
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
        else:
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"

    # Fallback to SQLite
    logger.info("No PostgreSQL config found — using SQLite fallback")
    return DEFAULT_ASYNC_SQLITE if async_mode else DEFAULT_SQLITE


# ─────────────────────────────────────────────────────────────────────────────
#  ASYNC ENGINE + SESSION (for FastAPI)
# ─────────────────────────────────────────────────────────────────────────────

_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db() -> None:
    """
    Initialize the async database engine and create all tables.
    Called during FastAPI lifespan startup.
    """
    global _async_engine, _async_session_factory

    url = _get_database_url(async_mode=True)
    logger.info(f"Initializing database: {url.split('@')[-1] if '@' in url else url}")

    engine_kwargs = {
        "echo": os.environ.get("DB_ECHO", "false").lower() == "true",
    }

    if "postgresql" in url:
        engine_kwargs.update({
            "pool_size": int(os.environ.get("DB_POOL_SIZE", "20")),
            "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
            "pool_pre_ping": True,
            "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "1800")),
        })

    _async_engine = create_async_engine(url, **engine_kwargs)
    _async_session_factory = async_sessionmaker(
        _async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables (in production, use Alembic migrations instead)
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized — all tables created/verified")


async def close_db() -> None:
    """Dispose of the async engine connection pool."""
    global _async_engine
    if _async_engine:
        await _async_engine.dispose()
        logger.info("Database connection pool closed")
        _async_engine = None


def get_engine() -> Optional[AsyncEngine]:
    """Return the current async engine (for health checks, etc.)."""
    return _async_engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an async database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────────────────────────────────────────────────────
#  SYNC ENGINE + SESSION (for ETL pipelines and scripts)
# ─────────────────────────────────────────────────────────────────────────────

_sync_engine = None
_sync_session_factory = None


def _get_sync_engine():
    """Lazy-initialize the sync engine."""
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        url = _get_database_url(async_mode=False)
        engine_kwargs = {
            "echo": os.environ.get("DB_ECHO", "false").lower() == "true",
        }
        if "postgresql" in url:
            engine_kwargs.update({
                "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "10")),
                "pool_pre_ping": True,
                "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "1800")),
            })
        _sync_engine = create_engine(url, **engine_kwargs)
        _sync_session_factory = sessionmaker(bind=_sync_engine)

        # Create tables
        Base.metadata.create_all(_sync_engine)
    return _sync_engine


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    Context manager for sync database sessions (ETL, scripts).

    Usage:
        with get_sync_session() as session:
            session.add(record)
            session.commit()
    """
    _get_sync_engine()
    session = _sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_sync_engine():
    """Return the sync engine (for bulk operations with pandas)."""
    return _get_sync_engine()


# ─────────────────────────────────────────────────────────────────────────────
#  HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

async def check_db_health() -> dict:
    """
    Check database connectivity and return status.
    Used by the /health endpoint.
    """
    if _async_engine is None:
        return {"status": "not_initialized", "backend": "none"}

    try:
        async with _async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        backend = "postgresql" if "postgresql" in str(_async_engine.url) else "sqlite"
        return {"status": "healthy", "backend": backend}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
