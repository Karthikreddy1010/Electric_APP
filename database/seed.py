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
    BgsAuctionRate,
    CommunityEnergy,
    MunicipalEnergy,
    StateMonthlyPrice,
    EIA861Master,
    WeatherOpenMeteo,
    DailySubBaDemand,
    EIA861MMonthly,
    UtilityMaster,
    UtilityZipLookup,
    UtilityRate,
    UtilityTariff,
    EIA930Hourly,
    EIA930Generation,
    EIA930Subregion,
    EIA930Interchange,
    UtilityServiceTerritory,
    CustomerProfile,
    CustomerBill,
    CustomerUsageHistory,
    CustomerForecast,
    CustomerSimulation,
    CustomerBillOCR,
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

    if force:
        logger.info("force=True, clearing existing tables before seeding...")
        with get_sync_session() as session:
            try:
                session.query(BillingData).delete()
                session.query(RawWeather).delete()
                session.query(WeatherIndex).delete()
                session.query(StateBenchmark).delete()
                session.query(Tariff).delete()
                session.query(BgsAuctionRate).delete()
                session.query(CommunityEnergy).delete()
                session.query(MunicipalEnergy).delete()
                session.query(StateMonthlyPrice).delete()
                session.query(EIA861Master).delete()
                session.query(WeatherOpenMeteo).delete()
                session.query(DailySubBaDemand).delete()
                session.query(EIA861MMonthly).delete()
                session.query(UtilityZipLookup).delete()
                session.query(UtilityRate).delete()
                session.query(UtilityTariff).delete()
                session.query(UtilityMaster).delete()
                session.query(UtilityServiceTerritory).delete()
                session.query(EIA930Hourly).delete()
                session.query(EIA930Generation).delete()
                session.query(EIA930Subregion).delete()
                session.query(EIA930Interchange).delete()
                session.commit()
                logger.info("Cleared all existing tables successfully.")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to clear database tables: {e}")

    results = {}
    results["billing"] = seed_billing_data(force)
    results["weather"] = seed_weather_data(force)
    results["benchmarks"] = seed_benchmarks(force)
    results["plans"] = seed_retail_plans(force)
    results["bgs_auction"] = seed_bgs_auction_rates(force)
    results["community_energy"] = seed_community_energy(force)
    results["municipal_energy"] = seed_municipal_energy(force)
    results["state_monthly"] = seed_state_monthly_prices(force)
    results["eia861"] = seed_eia861_master(force)
    results["weather_openmeteo"] = seed_weather_openmeteo(force)
    results["daily_subba_demand"] = seed_daily_subba_demand(force)

    # New dataset seeds
    results["eia861m_monthly"] = seed_eia861m_monthly(force)
    results["openei_utilities"] = seed_openei_utilities(force)
    results["eia930_initial"] = seed_eia930_initial(force)
    results["utility_service_territories"] = seed_utility_service_territories(force)
    results["customer_data"] = seed_customer_data(force)

    logger.info(f"Seed complete: {results}")
    return results


def seed_weather_openmeteo(force: bool = False) -> int:
    """Load weather_openmeteo.csv into weather_openmeteo table."""
    csv_path = RAW_DIR / "weather_openmeteo.csv"
    if not csv_path.exists():
        logger.warning("No weather_openmeteo.csv found — skipping openmeteo seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(WeatherOpenMeteo.id)).scalar()
            if count > 0:
                logger.info(f"weather_openmeteo already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            record = WeatherOpenMeteo(
                date=pd.to_datetime(row["date"]).date(),
                temp_max=float(row["temp_max"]) if pd.notna(row.get("temp_max")) else None,
                temp_min=float(row["temp_min"]) if pd.notna(row.get("temp_min")) else None,
                temp_avg=float(row["temp_avg"]) if pd.notna(row.get("temp_avg")) else None,
                hdd=float(row["hdd"]) if pd.notna(row.get("hdd")) else None,
                cdd=float(row["cdd"]) if pd.notna(row.get("cdd")) else None,
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} weather_openmeteo records")
    return len(records)


def seed_daily_subba_demand(force: bool = False) -> int:
    """Load eia_pjm_daily_demand.csv into daily_subba_demand table."""
    csv_path = RAW_DIR / "eia_pjm_daily_demand.csv"
    if not csv_path.exists():
        logger.warning("No eia_pjm_daily_demand.csv found — skipping daily subba demand seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(DailySubBaDemand.id)).scalar()
            if count > 0:
                logger.info(f"daily_subba_demand already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            record = DailySubBaDemand(
                period=pd.to_datetime(row["period"]).date(),
                subba=str(row["subba"]),
                value=float(row["value"]) if pd.notna(row.get("value")) else None,
                parent=str(row.get("parent", "PJM")),
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} daily_subba_demand records")
    return len(records)


def seed_bgs_auction_rates(force: bool = False) -> int:
    """Load bgs_auction.csv into bgs_auction_rates table."""
    csv_path = PROCESSED_DIR / "bgs_auction.csv"
    if not csv_path.exists():
        logger.warning("No bgs_auction.csv found — skipping BGS seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(BgsAuctionRate.id)).scalar()
            if count > 0:
                logger.info(f"bgs_auction_rates already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            kwh = float(row["final_price_k_wh"]) if pd.notna(row.get("final_price_k_wh")) else None
            mwd = float(row["final_price_m_wday"]) if pd.notna(row.get("final_price_m_wday")) else None
            
            # Skip if both are None
            if kwh is None and mwd is None:
                continue

            record = BgsAuctionRate(
                year=int(row["year"]),
                edc=str(row["edc"]),
                auction_product_type=str(row["auction_product_type"]),
                final_price_kwh=kwh,
                final_price_mw_day=mwd,
                sheet_source=str(row.get("sheet")),
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} BGS Auction rates")
    return len(records)


def seed_community_energy(force: bool = False) -> int:
    """Load community_energy.csv into community_energy table."""
    csv_path = PROCESSED_DIR / "community_energy.csv"
    if not csv_path.exists():
        logger.warning("No community_energy.csv found — skipping Community Energy seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(CommunityEnergy.id)).scalar()
            if count > 0:
                logger.info(f"community_energy already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            # Convert values safely
            record = CommunityEnergy(
                municipality=str(row["municipality"]),
                county=str(row["county"]),
                muni_county=str(row.get("muni_county", "")),
                year=int(row["year"]),
                electric_utility=str(row.get("electric_utility", "")),
                residential_electricity=float(row.get("residential_electricity", 0)),
                commercial_electricity=float(row.get("commercial_electricity", 0)),
                industrial_electricity=float(row.get("industrial_electricity", 0)),
                street_lighting_electricity=float(row.get("street_lighting_electricity", 0)),
                total_electricity_kwh=float(row.get("total_electricity_kwh", 0)),
                natural_gas_utility=str(row.get("natural_gas_utility", "")),
                residential_natural_gas=float(row.get("residential_natural_gas", 0)),
                commercial_natural_gas=float(row.get("commercial_natural_gas", 0)),
                industrial_natural_gas=float(row.get("industrial_natural_gas", 0)),
                street_lighting_natural_gas=float(row.get("street_lighting_natural_gas", 0)),
                total_natural_gas_therms=float(row.get("total_natural_gas_therms", 0)),
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} Community Energy records")
    return len(records)


def seed_municipal_energy(force: bool = False) -> int:
    """Load municipal_energy.csv into municipal_energy table."""
    csv_path = PROCESSED_DIR / "municipal_energy.csv"
    if not csv_path.exists():
        logger.warning("No municipal_energy.csv found — skipping Municipal Energy seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(MunicipalEnergy.id)).scalar()
            if count > 0:
                logger.info(f"municipal_energy already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            record = MunicipalEnergy(
                municipality=str(row["municipality"]),
                county=str(row["county"]),
                utility=str(row.get("utility", "")),
                year=int(row["year"]),
                sector=str(row.get("sector", "")),
                electricity_kwh=float(row.get("electricity_kwh", 0)),
                natural_gas_therms=float(row.get("natural_gas_therms", 0)),
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} Municipal Energy records")
    return len(records)


def seed_state_monthly_prices(force: bool = False) -> int:
    """Load eia_residential_prices.csv into state_monthly_prices table."""
    csv_path = PROCESSED_DIR / "eia_residential_prices.csv"
    if not csv_path.exists():
        logger.warning("No eia_residential_prices.csv found — skipping State Monthly Prices seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(StateMonthlyPrice.id)).scalar()
            if count > 0:
                logger.info(f"state_monthly_prices already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            record = StateMonthlyPrice(
                date=pd.to_datetime(row["date"]).date(),
                state=str(row["state"]),
                state_name=str(row["state_name"]),
                price_cents_kwh=float(row["price_cents_kwh"]),
                year=int(row["year"]),
                month=int(row["month"]),
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} State Monthly Price records")
    return len(records)


def seed_eia861_master(force: bool = False) -> int:
    """Load eia861_master_clean.csv into eia861_master table."""
    csv_path = PROCESSED_DIR / "eia861" / "eia861_master_clean.csv"
    if not csv_path.exists():
        logger.warning("No eia861_master_clean.csv found — skipping EIA-861 seed")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(EIA861Master.id)).scalar()
            if count > 0:
                logger.info(f"eia861_master already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            record = EIA861Master(
                year=int(row["year"]),
                utility_id=int(row["utility_id"]),
                utility_name=str(row["utility_name"]) if pd.notna(row["utility_name"]) else None,
                state=str(row["state"]),
                total_revenue=float(row["total_revenue"]) if pd.notna(row["total_revenue"]) else None,
                total_sales_mwh=float(row["total_sales_mwh"]) if pd.notna(row["total_sales_mwh"]) else None,
                total_customers=float(row["total_customers"]) if pd.notna(row["total_customers"]) else None,
                avg_price=float(row["avg_price"]) if pd.notna(row["avg_price"]) else None,
                nm_customers=float(row["nm_customers"]) if pd.notna(row["nm_customers"]) else None,
                nm_energy_mwh=float(row["nm_energy_mwh"]) if pd.notna(row["nm_energy_mwh"]) else None,
                peak_demand=float(row["peak_demand"]) if pd.notna(row["peak_demand"]) else None,
                total_load=float(row["total_load"]) if pd.notna(row["total_load"]) else None,
                demand_response_flag=int(row["demand_response_flag"]) if pd.notna(row["demand_response_flag"]) else 0,
                dynamic_pricing_flag=int(row["dynamic_pricing_flag"]) if pd.notna(row["dynamic_pricing_flag"]) else 0,
            )
            records.append(record)

        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} EIA-861 master records")
    return len(records)


def seed_eia861m_monthly(force: bool = False) -> int:
    """Load EIA-861M monthly state-level data from Excel into eia861m_monthly table."""
    try:
        from data_pipeline.eia861m_loader import load_eia861m_from_csv
    except ImportError as e:
        logger.warning(f"Cannot import eia861m_loader: {e} — skipping EIA-861M seed")
        return 0

    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(EIA861MMonthly.id)).scalar()
            if count and count > 0:
                logger.info(f"eia861m_monthly already has {count} rows — skipping")
                return count

    df = load_eia861m_from_csv()
    if df.empty:
        logger.warning("No EIA-861M data to seed")
        return 0

    records = []
    for _, row in df.iterrows():
        record = EIA861MMonthly(
            year=int(row["year"]),
            month=int(row["month"]),
            state=str(row["state"]),
            sector=str(row["sector"]),
            period=str(row["period"]),
            data_status=str(row["data_status"]) if pd.notna(row.get("data_status")) else None,
            revenue_k_dollars=float(row["revenue_k_dollars"]) if pd.notna(row.get("revenue_k_dollars")) else None,
            sales_mwh=float(row["sales_mwh"]) if pd.notna(row.get("sales_mwh")) else None,
            customers=int(row["customers"]) if pd.notna(row.get("customers")) else None,
            price_cents_kwh=float(row["price_cents_kwh"]) if pd.notna(row.get("price_cents_kwh")) else None,
        )
        records.append(record)

    with get_sync_session() as session:
        session.add_all(records)
        session.commit()
    logger.info(f"Seeded {len(records)} EIA-861M monthly records")
    return len(records)


def seed_openei_utilities(force: bool = False) -> int:
    """Load OpenEI utility CSV data into utility_master, utility_zip_lookup, and utility_rates."""
    try:
        from data_pipeline.openei_loader import load_openei_from_csv
    except ImportError as e:
        logger.warning(f"Cannot import openei_loader: {e} — skipping OpenEI seed")
        return 0

    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(UtilityMaster.id)).scalar()
            if count and count > 0:
                logger.info(f"utility_master already has {count} rows — skipping OpenEI seed")
                return count

    masters_df, zip_df, rates_df = load_openei_from_csv()
    if masters_df.empty:
        logger.warning("No OpenEI data to seed")
        return 0

    total = 0

    # 1. Seed utility_master
    master_records = []
    for _, row in masters_df.iterrows():
        master_records.append(UtilityMaster(
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]),
            state=str(row["state"]),
            ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
        ))
    with get_sync_session() as session:
        session.add_all(master_records)
        session.commit()
    total += len(master_records)
    logger.info(f"Seeded {len(master_records)} utility_master records")

    # 2. Seed utility_zip_lookup
    zip_records = []
    for _, row in zip_df.iterrows():
        zip_records.append(UtilityZipLookup(
            zip_code=str(row["zip_code"]),
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]) if pd.notna(row.get("utility_name")) else None,
            state=str(row["state"]),
            service_type=str(row["service_type"]) if pd.notna(row.get("service_type")) else None,
        ))
    with get_sync_session() as session:
        session.add_all(zip_records)
        session.commit()
    total += len(zip_records)
    logger.info(f"Seeded {len(zip_records)} utility_zip_lookup records")

    # 3. Seed utility_rates
    rate_records = []
    for _, row in rates_df.iterrows():
        rate_records.append(UtilityRate(
            eia_utility_id=int(row["eia_utility_id"]),
            state=str(row["state"]),
            residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
            commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
            industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
        ))
    with get_sync_session() as session:
        session.add_all(rate_records)
        session.commit()
    total += len(rate_records)
    logger.info(f"Seeded {len(rate_records)} utility_rates records")

    return total


def seed_eia930_initial(force: bool = False) -> int:
    """Fetch initial EIA-930 data (last 48 hours) from API and seed into database."""
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(EIA930Hourly.id)).scalar()
            if count and count > 0:
                logger.info(f"eia930_hourly already has {count} rows — skipping initial EIA-930 seed")
                return count

    try:
        from data_pipeline.eia930_fetcher import fetch_all_eia930
    except ImportError as e:
        logger.warning(f"Cannot import eia930_fetcher: {e} — skipping EIA-930 seed")
        return 0

    try:
        data = fetch_all_eia930(hours_back=48)
    except Exception as e:
        logger.error(f"EIA-930 initial fetch failed: {e}")
        return 0

    total = 0

    # 1. Seed eia930_hourly
    hourly_df = data.get("hourly", pd.DataFrame())
    if not hourly_df.empty:
        records = []
        for _, row in hourly_df.iterrows():
            records.append(EIA930Hourly(
                period=row["period"],
                ba_code=str(row["ba_code"]),
                ba_name=str(row.get("ba_name", "")),
                type_code=str(row["type_code"]),
                type_name=str(row.get("type_name", "")),
                value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
            ))
        with get_sync_session() as session:
            session.add_all(records)
            session.commit()
        total += len(records)
        logger.info(f"Seeded {len(records)} eia930_hourly records")

    # 2. Seed eia930_generation
    gen_df = data.get("generation", pd.DataFrame())
    if not gen_df.empty:
        records = []
        for _, row in gen_df.iterrows():
            records.append(EIA930Generation(
                period=row["period"],
                ba_code=str(row["ba_code"]),
                ba_name=str(row.get("ba_name", "")),
                fuel_type=str(row["fuel_type"]),
                fuel_type_name=str(row.get("fuel_type_name", "")),
                value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
            ))
        with get_sync_session() as session:
            session.add_all(records)
            session.commit()
        total += len(records)
        logger.info(f"Seeded {len(records)} eia930_generation records")

    # 3. Seed eia930_subregion
    sub_df = data.get("subregion", pd.DataFrame())
    if not sub_df.empty:
        records = []
        for _, row in sub_df.iterrows():
            records.append(EIA930Subregion(
                period=row["period"],
                subba_code=str(row["subba_code"]),
                subba_name=str(row.get("subba_name", "")),
                parent_ba=str(row["parent_ba"]),
                parent_ba_name=str(row.get("parent_ba_name", "")),
                value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
            ))
        with get_sync_session() as session:
            session.add_all(records)
            session.commit()
        total += len(records)
        logger.info(f"Seeded {len(records)} eia930_subregion records")

    # 4. Seed eia930_interchange
    ix_df = data.get("interchange", pd.DataFrame())
    if not ix_df.empty:
        records = []
        for _, row in ix_df.iterrows():
            records.append(EIA930Interchange(
                period=row["period"],
                from_ba=str(row["from_ba"]),
                from_ba_name=str(row.get("from_ba_name", "")),
                to_ba=str(row["to_ba"]),
                to_ba_name=str(row.get("to_ba_name", "")),
                value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
            ))
        with get_sync_session() as session:
            session.add_all(records)
            session.commit()
        total += len(records)
        logger.info(f"Seeded {len(records)} eia930_interchange records")

    return total


def seed_utility_service_territories(force: bool = False) -> int:
    """Load service_territory_clean.csv into utility_service_territories table."""
    csv_path = PROCESSED_DIR / "eia861" / "service_territory_clean.csv"
    if not csv_path.exists():
        csv_path = PROJECT_ROOT / "data" / "processed" / "eia861" / "service_territory_clean.csv"
        
    if not csv_path.exists():
        logger.warning(f"No service territory CSV found at {csv_path} — skipping")
        return 0

    df = pd.read_csv(csv_path)
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(UtilityServiceTerritory.id)).scalar()
            if count > 0:
                logger.info(f"utility_service_territories already has {count} rows — skipping")
                return count

        records = []
        for _, row in df.iterrows():
            records.append(UtilityServiceTerritory(
                utility_id=int(row["utility_id"]),
                state=str(row["state"]).strip().upper(),
                county=str(row["county"]).strip(),
            ))
            if len(records) >= 5000:
                session.add_all(records)
                session.commit()
                records = []
        if records:
            session.add_all(records)
            session.commit()

    logger.info(f"Seeded {len(df)} utility service territory records")
    return len(df)


def seed_customer_data(force: bool = False) -> int:
    """Seeds synthetic customer profiles, bills, usage history, and simulated OCR data."""
    syn_dir = PROJECT_ROOT / "data" / "synthetic_bills"
    if not (syn_dir / "json").exists():
        syn_dir = PROJECT_ROOT / "data" / "test_synthetic_bills"
        
    if not (syn_dir / "json").exists():
        logger.warning(f"No synthetic customer bill JSON files found at {syn_dir} — skipping")
        return 0

    json_dir = syn_dir / "json"
    files = [f.name for f in json_dir.glob("*.json")]
    
    with get_sync_session() as session:
        if not force:
            count = session.query(func.count(CustomerProfile.customer_id)).scalar()
            if count > 0:
                logger.info(f"customer_profiles already has {count} rows — skipping")
                return count
        else:
            try:
                session.query(CustomerBillOCR).delete()
                session.query(CustomerForecast).delete()
                session.query(CustomerSimulation).delete()
                session.query(CustomerUsageHistory).delete()
                session.query(CustomerBill).delete()
                session.query(CustomerProfile).delete()
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to clear customer database tables: {e}")

        # Seed profiles, bills, history, and OCR
        import json
        import random
        
        profiles = {}
        bills = []
        histories = []
        ocr_runs = []
        
        for fname in files:
            path = json_dir / fname
            if not path.exists() or path.stat().st_size == 0:
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    bill_data = json.load(f)
            except Exception as e:
                logger.warning(f"Skipping corrupted JSON file {fname}: {e}")
                continue
                
            cust_id = bill_data["customer_id"]
            
            # Create unique customer profile
            if cust_id not in profiles:
                profiles[cust_id] = CustomerProfile(
                    customer_id=cust_id,
                    utility=bill_data["utility"],
                    zip_code=bill_data.get("zip_code", "07102"),
                    rate_schedule=bill_data["rate_schedule"],
                    meter_number=bill_data["meter_number"]
                )
            
            # Load ground truth OCR text
            base_name = fname.replace(".json", "")
            ocr_text_path = syn_dir / "ocr" / f"{base_name}.txt"
            ocr_txt = ""
            if ocr_text_path.exists():
                with open(ocr_text_path, "r", encoding="utf-8", errors="ignore") as ocr_f:
                    ocr_txt = ocr_f.read()
                    
            bill_date = pd.to_datetime(bill_data["bill_date"]).date()
            
            # Add bill
            bill_record = CustomerBill(
                customer_id=cust_id,
                bill_date=bill_date,
                billing_period=bill_data["billing_period"],
                days=bill_data["days"],
                previous_reading=bill_data["previous_reading"],
                current_reading=bill_data["current_reading"],
                usage_kwh=bill_data["usage_kwh"],
                monthly_service_charge=bill_data["monthly_service_charge"],
                delivery_charge=bill_data["delivery_charge"],
                supply_charge=bill_data["supply_charge"],
                tax=bill_data["tax"],
                total_bill=bill_data["total_bill"],
                average_daily_usage=bill_data["average_daily_usage"],
                average_daily_cost=bill_data["average_daily_cost"],
                utility_message=bill_data["utility_message"],
                weather_message=bill_data["weather_message"],
                energy_assistance_message=bill_data["energy_assistance_message"],
                net_metering_message=bill_data["net_metering_message"],
                ocr_text=ocr_txt,
                json_path=str(path)
            )
            bills.append(bill_record)
            
            # Add 12-month usage history
            for hist in bill_data.get("usage_history", []):
                histories.append(CustomerUsageHistory(
                    customer_id=cust_id,
                    month_label=hist["month_label"],
                    usage_kwh=float(hist["usage_kwh"]),
                    avg_temp_f=float(hist["avg_temp_f"])
                ))
                
            # Simulate OCR run evaluation
            bbox_path = syn_dir / "annotations" / "bboxes" / f"{base_name}_bboxes.json"
            bboxes = []
            if bbox_path.exists():
                with open(bbox_path, "r", encoding="utf-8", errors="ignore") as bbox_f:
                    bboxes = json.load(bbox_f)
            
            ocr_fields = [
                ("total_bill", str(bill_data["total_bill"])),
                ("usage_kwh", str(bill_data["usage_kwh"])),
                ("bill_date", str(bill_data["bill_date"])),
                ("due_date", str(bill_data["due_date"])),
                ("meter_number", str(bill_data["meter_number"])),
                ("monthly_service_charge", str(bill_data["monthly_service_charge"])),
                ("delivery_charge", str(bill_data["delivery_charge"])),
                ("supply_charge", str(bill_data["supply_charge"]))
            ]
            
            for field, gt_val in ocr_fields:
                box_str = ""
                for box in bboxes:
                    if box["field"] == field:
                        box_str = str(box["bbox"])
                        break
                        
                has_error = random.random() < 0.02
                ext_val = gt_val
                conf = round(random.uniform(0.92, 0.99), 2)
                
                if has_error:
                    conf = round(random.uniform(0.40, 0.75), 2)
                    if "." in gt_val:
                        parts = gt_val.split(".")
                        ext_val = parts[0] + "." + str(random.randint(0, 9))
                    else:
                        ext_val = gt_val[:-1] + random.choice(["B", "O", "1", "9"])
                
                ocr_runs.append(CustomerBillOCR(
                    customer_id=cust_id,
                    bill_date=bill_date,
                    field_name=field,
                    ground_truth_value=gt_val,
                    extracted_value=ext_val,
                    confidence=conf,
                    ocr_error_flag=has_error,
                    bbox=box_str
                ))
                
        # Save profiles
        session.add_all(profiles.values())
        session.commit()
        
        # Save bills in chunks
        for i in range(0, len(bills), 1000):
            session.add_all(bills[i:i+1000])
            session.commit()
            
        # Save history in chunks
        for i in range(0, len(histories), 5000):
            session.add_all(histories[i:i+5000])
            session.commit()
            
        # Save OCR runs in chunks
        for i in range(0, len(ocr_runs), 5000):
            session.add_all(ocr_runs[i:i+5000])
            session.commit()
            
    logger.info(f"Seeded customer data from {len(files)} synthetic bills")
    return len(files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database from CSV/Parquet files")
    parser.add_argument("--force", action="store_true", help="Re-seed even if tables have data")
    args = parser.parse_args()
    run_seed(force=args.force)

