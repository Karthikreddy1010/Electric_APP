"""
Database Seeder — migrate existing CSV/Parquet data into PostgreSQL.

Reads from data/raw/ and data/processed/ files and loads them into
the appropriate database tables. Idempotent — can be run multiple times.

Usage:
    python -m database.seed
    python -m database.seed --force  # Re-seed even if tables have data
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import func, select

from database.connection import get_sync_engine, get_sync_session
from database.models import (
    Base,
    BillingData,
    RawWeather,
    StateBenchmark,
    Tariff,
    WeatherIndex,
)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def seed_billing_data(force: bool = False) -> int:
    """Load billing.csv or billing.parquet into the billing_data table."""
    csv_path = RAW_DIR / "billing.csv"
    parquet_path = RAW_DIR / "billing.parquet"

    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        logger.warning("No billing data file found — skipping")
        return 0

    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(BillingData.id)).scalar()
            if count > 0:
                logger.info(f"billing_data already has {count} rows — skipping (use --force to override)")
                return count

        records = []
        for _, row in df.iterrows():
            record = BillingData(
                account_id=str(row.get("account_id", "default")),
                bill_date=pd.to_datetime(row.get("date", row.get("bill_date"))).date(),
                usage_kwh=float(row.get("usage_kwh", 0)),
                effective_kwh=float(row.get("effective_kwh", row.get("usage_kwh", 0) * 1.043)),
                customer_charge=float(row.get("customer_charge", 0)),
                bgs_cost=float(row.get("bgs_cost", 0)),
                distribution_cost=float(row.get("distribution_cost", 0)),
                transmission_cost=float(row.get("transmission_cost", 0)),
                sbc_cost=float(row.get("sbc_cost", 0)),
                rider_cost=float(row.get("rider_cost", 0)),
                sales_tax=float(row.get("sales_tax", 0)),
                total_bill=float(row.get("total_bill", 0)),
                bgs_rate=float(row.get("bgs_rate", 0)) if pd.notna(row.get("bgs_rate")) else None,
                distribution_rate=float(row.get("distribution_rate", 0)) if pd.notna(row.get("distribution_rate")) else None,
                transmission_rate=float(row.get("transmission_rate", 0)) if pd.notna(row.get("transmission_rate")) else None,
                sbc_rate=float(row.get("sbc_rate", 0)) if pd.notna(row.get("sbc_rate")) else None,
                avg_lmp=float(row.get("avg_lmp", 0)) if pd.notna(row.get("avg_lmp")) else None,
            )
            records.append(record)

        session.add_all(records)
        session.commit()

    logger.info(f"Seeded {len(records)} billing records")
    return len(records)


def seed_weather_data(force: bool = False) -> int:
    """Load air_temp.csv into raw_weather and compute weather_index."""
    air_temp_path = RAW_DIR / "air_temp.csv"
    if not air_temp_path.exists():
        logger.warning("No air_temp.csv found — skipping weather seed")
        return 0

    df = pd.read_csv(air_temp_path)
    df["DATE"] = pd.to_datetime(df["DATE"])

    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(RawWeather.id)).scalar()
            if count > 0:
                logger.info(f"raw_weather already has {count} rows — skipping")
                return count

        # Parse raw weather records
        records = []
        for _, row in df.iterrows():
            tmax = float(row.get("TMAX", 0)) if pd.notna(row.get("TMAX")) else None
            tmin = float(row.get("TMIN", 0)) if pd.notna(row.get("TMIN")) else None
            tavg = float(row.get("TAVG", 0)) if pd.notna(row.get("TAVG")) else None
            if tavg is None and tmax is not None and tmin is not None:
                tavg = (tmax + tmin) / 2.0

            record = RawWeather(
                date=row["DATE"].date(),
                station_id=str(row.get("STATION", "UNKNOWN")),
                station_name=str(row.get("NAME", "")),
                state="NJ",
                tmax_f=tmax,
                tmin_f=tmin,
                tavg_f=tavg,
            )
            records.append(record)

        session.add_all(records)
        session.commit()

    # Compute and seed weather_index (HDD/CDD)
    with get_sync_session() as session:
        wx_records = []
        for _, row in df.iterrows():
            tmax = float(row.get("TMAX", 0)) if pd.notna(row.get("TMAX")) else None
            tmin = float(row.get("TMIN", 0)) if pd.notna(row.get("TMIN")) else None
            tavg = float(row.get("TAVG", 0)) if pd.notna(row.get("TAVG")) else None
            if tavg is None and tmax is not None and tmin is not None:
                tavg = (tmax + tmin) / 2.0
            if tavg is None:
                continue

            hdd = max(65.0 - tavg, 0.0)
            cdd = max(tavg - 65.0, 0.0)

            wx = WeatherIndex(
                date=row["DATE"].date(),
                region_id="NJ",
                avg_temp_f=tavg,
                hdd=hdd,
                cdd=cdd,
            )
            wx_records.append(wx)

        session.add_all(wx_records)
        session.commit()

    logger.info(f"Seeded {len(records)} raw_weather + {len(wx_records)} weather_index records")
    return len(records)


def seed_benchmarks(force: bool = False) -> int:
    """Load state benchmark data into state_benchmark table."""
    csv_path = PROCESSED_DIR / "state_benchmark.csv"
    parquet_path = PROCESSED_DIR / "state_benchmark.parquet"

    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        # Try raw directory
        raw_parquet = RAW_DIR / "state_benchmark.parquet"
        raw_csv = RAW_DIR / "state_benchmark.csv"
        if raw_parquet.exists():
            df = pd.read_parquet(raw_parquet)
        elif raw_csv.exists():
            df = pd.read_csv(raw_csv)
        else:
            logger.warning("No benchmark data found — skipping")
            return 0

    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(StateBenchmark.id)).scalar()
            if count > 0:
                logger.info(f"state_benchmark already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            record = StateBenchmark(
                year=int(row.get("year", 2024)),
                month=int(row["month"]) if pd.notna(row.get("month")) else None,
                state=str(row.get("state", "")),
                sector="residential",
                avg_rate_cents_kwh=float(row.get("avg_rate", row.get("avg_rate_cents_kwh", 0))),
                avg_bill_dollars=float(row.get("avg_bill", row.get("avg_bill_dollars", 0))),
                total_sales_mwh=float(row.get("total_sales_mwh", 0)) if pd.notna(row.get("total_sales_mwh")) else None,
            )
            records.append(record)

        session.add_all(records)
        session.commit()

    logger.info(f"Seeded {len(records)} state benchmark records")
    return len(records)


def seed_retail_plans(force: bool = False) -> int:
    """Load retail plans into tariffs table."""
    csv_path = RAW_DIR / "retail_plans.csv"
    parquet_path = RAW_DIR / "retail_plans.parquet"

    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        logger.warning("No retail plans data found — skipping")
        return 0

    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(Tariff.id)).scalar()
            if count > 0:
                logger.info(f"tariffs already has {count} rows — skipping")
                return count

        records = []
        for idx, row in df.iterrows():
            record = Tariff(
                tariff_id=f"plan_{idx}_{row.get('provider', 'unknown')}",
                provider=str(row.get("provider", "Unknown")),
                plan_name=str(row.get("plan_name", row.get("plan_type", "Standard"))),
                plan_type=str(row.get("type", row.get("plan_type", "default"))),
                effective_date=pd.Timestamp.now().date(),
                bgs_rate=float(row.get("rate", row.get("bgs_rate", 0))),
            )
            records.append(record)

        session.add_all(records)
        session.commit()

    logger.info(f"Seeded {len(records)} tariff/plan records")
    return len(records)


def run_seed(force: bool = False) -> dict:
    """Run all seed operations and return summary."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logger.info("=" * 70)
    logger.info("DATABASE SEED — Loading existing data into PostgreSQL")
    logger.info("=" * 70)

    # Ensure tables exist
    engine = get_sync_engine()
    Base.metadata.create_all(engine)

    results = {}
    results["billing"] = seed_billing_data(force)
    results["weather"] = seed_weather_data(force)
    results["benchmarks"] = seed_benchmarks(force)
    results["plans"] = seed_retail_plans(force)

    logger.info(f"Seed complete: {results}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database from CSV/Parquet files")
    parser.add_argument("--force", action="store_true", help="Re-seed even if tables have data")
    args = parser.parse_args()
    run_seed(force=args.force)
