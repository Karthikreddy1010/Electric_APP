"""
Database Repository — CRUD operations and query helpers.

Provides a clean data-access layer between the API/services and the ORM.
All methods accept a session (async or sync) for flexibility.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Base,
    BillingData,
    EnergyUsage,
    ETLJobLog,
    FeatureStore,
    RawDemographics,
    RawEnergyData,
    RawWeather,
    StateBenchmark,
    Tariff,
    WeatherIndex,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  GENERIC BULK UPSERT (PostgreSQL ON CONFLICT, SQLite INSERT OR REPLACE)
# ─────────────────────────────────────────────────────────────────────────────

async def bulk_upsert(
    session: AsyncSession,
    model: type[Base],
    records: list[dict],
    conflict_columns: list[str],
    update_columns: Optional[list[str]] = None,
) -> int:
    """
    Bulk insert records with upsert semantics (insert or update on conflict).

    For PostgreSQL uses ON CONFLICT DO UPDATE.
    For SQLite falls back to individual merge operations.

    Parameters
    ----------
    session : AsyncSession
    model : SQLAlchemy ORM model class
    records : list of dicts to insert/update
    conflict_columns : columns that form the unique constraint
    update_columns : columns to update on conflict (if None, updates all non-PK/non-conflict)

    Returns
    -------
    Number of records processed
    """
    if not records:
        return 0

    try:
        # Try PostgreSQL-native upsert
        stmt = pg_insert(model.__table__).values(records)
        if update_columns:
            update_dict = {col: stmt.excluded[col] for col in update_columns}
        else:
            # Update all columns except PK and conflict columns
            exclude = set(conflict_columns) | {"id"}
            update_dict = {
                col.name: stmt.excluded[col.name]
                for col in model.__table__.columns
                if col.name not in exclude
            }
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_dict,
        )
        await session.execute(stmt)
        return len(records)
    except Exception:
        # Fallback for SQLite: individual inserts with merge
        count = 0
        for record in records:
            try:
                obj = model(**record)
                await session.merge(obj)
                count += 1
            except Exception as e:
                logger.debug(f"Merge failed for record: {e}")
        return count


# ─────────────────────────────────────────────────────────────────────────────
#  ENERGY DATA QUERIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_energy_data(
    session: AsyncSession,
    region_id: str,
    start_date: datetime,
    end_date: datetime,
    source: Optional[str] = None,
) -> Sequence[RawEnergyData]:
    """Fetch energy price/generation data for a region and time range."""
    stmt = (
        select(RawEnergyData)
        .where(RawEnergyData.region_id == region_id)
        .where(RawEnergyData.timestamp >= start_date)
        .where(RawEnergyData.timestamp <= end_date)
        .order_by(RawEnergyData.timestamp)
    )
    if source:
        stmt = stmt.where(RawEnergyData.source == source)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_latest_lmp(
    session: AsyncSession,
    region_id: str = "PSEG",
) -> Optional[float]:
    """Get the most recent LMP for a region."""
    stmt = (
        select(RawEnergyData.price_per_mwh)
        .where(RawEnergyData.region_id == region_id)
        .where(RawEnergyData.price_per_mwh.isnot(None))
        .order_by(RawEnergyData.timestamp.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return float(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
#  WEATHER QUERIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_weather_index(
    session: AsyncSession,
    region_id: str,
    start_date: date,
    end_date: date,
) -> Sequence[WeatherIndex]:
    """Fetch pre-computed HDD/CDD for a region and date range."""
    stmt = (
        select(WeatherIndex)
        .where(WeatherIndex.region_id == region_id)
        .where(WeatherIndex.date >= start_date)
        .where(WeatherIndex.date <= end_date)
        .order_by(WeatherIndex.date)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_monthly_hdd_cdd(
    session: AsyncSession,
    region_id: str,
    year: int,
    month: int,
) -> Dict[str, float]:
    """Get total HDD and CDD for a specific month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    stmt = (
        select(
            func.sum(WeatherIndex.hdd).label("total_hdd"),
            func.sum(WeatherIndex.cdd).label("total_cdd"),
            func.avg(WeatherIndex.avg_temp_f).label("avg_temp"),
        )
        .where(WeatherIndex.region_id == region_id)
        .where(WeatherIndex.date >= start)
        .where(WeatherIndex.date < end)
    )
    result = await session.execute(stmt)
    row = result.one()
    return {
        "hdd": float(row.total_hdd or 0),
        "cdd": float(row.total_cdd or 0),
        "avg_temp": float(row.avg_temp or 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  BILLING QUERIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_billing_history(
    session: AsyncSession,
    account_id: str,
    months: int = 24,
) -> Sequence[BillingData]:
    """Get recent billing records for an account."""
    stmt = (
        select(BillingData)
        .where(BillingData.account_id == account_id)
        .order_by(BillingData.bill_date.desc())
        .limit(months)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_billing_as_dataframe(
    session: AsyncSession,
    account_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Load billing data as a pandas DataFrame for ML models."""
    stmt = select(BillingData)
    if account_id:
        stmt = stmt.where(BillingData.account_id == account_id)
    if start_date:
        stmt = stmt.where(BillingData.bill_date >= start_date)
    if end_date:
        stmt = stmt.where(BillingData.bill_date <= end_date)
    stmt = stmt.order_by(BillingData.bill_date)

    result = await session.execute(stmt)
    rows = result.scalars().all()
    if not rows:
        return pd.DataFrame()

    records = [{c.name: getattr(r, c.name) for c in BillingData.__table__.columns} for r in rows]
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
#  BENCHMARK QUERIES
# ─────────────────────────────────────────────────────────────────────────────

async def get_state_benchmarks(
    session: AsyncSession,
    year: int,
    sector: str = "residential",
) -> Sequence[StateBenchmark]:
    """Get all state benchmarks for a given year and sector."""
    stmt = (
        select(StateBenchmark)
        .where(StateBenchmark.year == year)
        .where(StateBenchmark.sector == sector)
        .order_by(StateBenchmark.avg_rate_cents_kwh.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_state_benchmark_history(
    session: AsyncSession,
    state: str,
    sector: str = "residential",
) -> Sequence[StateBenchmark]:
    """Get historical benchmarks for a specific state."""
    stmt = (
        select(StateBenchmark)
        .where(StateBenchmark.state == state)
        .where(StateBenchmark.sector == sector)
        .order_by(StateBenchmark.year, StateBenchmark.month)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
#  ETL JOB LOGGING
# ─────────────────────────────────────────────────────────────────────────────

async def log_etl_job(
    session: AsyncSession,
    job_name: str,
    source: str,
    status: str = "running",
    rows_ingested: int = 0,
    error_message: Optional[str] = None,
) -> ETLJobLog:
    """Create or update an ETL job log entry."""
    job = ETLJobLog(
        job_name=job_name,
        source=source,
        status=status,
        rows_ingested=rows_ingested,
        error_message=error_message,
    )
    session.add(job)
    await session.flush()
    return job


async def complete_etl_job(
    session: AsyncSession,
    job_id: int,
    status: str = "success",
    rows_ingested: int = 0,
    rows_updated: int = 0,
    error_message: Optional[str] = None,
) -> None:
    """Mark an ETL job as completed."""
    stmt = (
        update(ETLJobLog)
        .where(ETLJobLog.id == job_id)
        .values(
            status=status,
            completed_at=func.now(),
            rows_ingested=rows_ingested,
            rows_updated=rows_updated,
            error_message=error_message,
        )
    )
    await session.execute(stmt)


# ─────────────────────────────────────────────────────────────────────────────
#  FEATURE STORE
# ─────────────────────────────────────────────────────────────────────────────

async def get_feature_matrix(
    session: AsyncSession,
    account_id: Optional[str] = None,
) -> pd.DataFrame:
    """Load the feature store as a DataFrame for ML training."""
    stmt = select(FeatureStore).order_by(FeatureStore.date)
    if account_id:
        stmt = stmt.where(FeatureStore.account_id == account_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    if not rows:
        return pd.DataFrame()
    records = [{c.name: getattr(r, c.name) for c in FeatureStore.__table__.columns} for r in rows]
    return pd.DataFrame(records)
