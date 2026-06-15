"""
SQLAlchemy ORM Models — Full schema for the Energy Cost Modeling Platform.

Tables follow the blueprint schema with normalized naming and proper indexes.
Supports both raw ingestion tables and processed analytical tables.

References:
    - Blueprint Database Schema (raw_energy_data, raw_weather, etc.)
    - PJM Manual 15/28 for market data fields
    - EIA-861 for utility/sales structure
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
#  RAW INGESTION TABLES
# ─────────────────────────────────────────────────────────────────────────────

class RawEnergyData(Base):
    """
    Hourly/sub-hourly generation and price data from EIA and ISOs.
    Primary source: EIA API bulk downloads, PJM Data Miner.
    """
    __tablename__ = "raw_energy_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    region_id = Column(String(20), nullable=False, index=True)  # ISO zone code (e.g. "PSEG")
    source = Column(String(20), nullable=False, default="eia")  # eia, pjm, caiso
    price_per_mwh = Column(Float)                               # LMP or avg price $/MWh
    generation_mw = Column(Float)                                # Generation output MW
    demand_mw = Column(Float)                                    # Load/demand MW
    congestion_per_mwh = Column(Float)                           # Congestion component $/MWh
    loss_per_mwh = Column(Float)                                 # Loss component $/MWh
    fuel_type = Column(String(30))                               # gas, coal, nuclear, wind, etc.
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("timestamp", "region_id", "source", name="uq_energy_ts_region_source"),
        Index("ix_energy_region_ts", "region_id", "timestamp"),
    )


class RawWeather(Base):
    """
    Daily weather observations from NOAA GHCND stations.
    Primary source: NOAA CDO API, NOAA FTP bulk downloads.
    """
    __tablename__ = "raw_weather"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    station_id = Column(String(20), nullable=False, index=True)  # GHCND station ID
    station_name = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    state = Column(String(2))
    tmax_f = Column(Float)                                       # Daily max temp °F
    tmin_f = Column(Float)                                       # Daily min temp °F
    tavg_f = Column(Float)                                       # Daily avg temp °F
    precip_in = Column(Float)                                    # Precipitation inches
    snow_in = Column(Float)                                      # Snowfall inches
    wind_speed_mph = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("date", "station_id", name="uq_weather_date_station"),
        Index("ix_weather_state_date", "state", "date"),
    )


class RawDemographics(Base):
    """
    US Census ACS demographic data by geography.
    Primary source: Census ACS API (1-year and 5-year estimates).
    """
    __tablename__ = "raw_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    geo_id = Column(String(15), nullable=False, index=True)      # FIPS code
    geo_name = Column(String(100))
    geo_level = Column(String(10), nullable=False, default="state")  # state, county, tract
    state_fips = Column(String(2))
    county_fips = Column(String(5))
    total_population = Column(Integer)
    median_household_income = Column(Numeric(12, 2))
    housing_units = Column(Integer)
    owner_occupied_pct = Column(Float)
    median_home_value = Column(Numeric(12, 2))
    poverty_rate = Column(Float)
    dataset = Column(String(10), default="acs5")                 # acs1, acs5
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "geo_id", "dataset", name="uq_demo_year_geo_dataset"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PROCESSED / ANALYTICAL TABLES
# ─────────────────────────────────────────────────────────────────────────────

class EnergyUsage(Base):
    """
    Aggregated monthly energy consumption and demand per account.
    Derived from billing data and meter readings.
    """
    __tablename__ = "energy_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(30), nullable=False, index=True)
    month = Column(Date, nullable=False, index=True)             # First day of month
    region_id = Column(String(20), nullable=False)
    usage_kwh = Column(Float, nullable=False)
    demand_kw = Column(Float)                                    # Peak demand kW
    effective_kwh = Column(Float)                                # Loss-adjusted kWh
    days_in_period = Column(Integer)
    avg_daily_kwh = Column(Float)

    __table_args__ = (
        UniqueConstraint("account_id", "month", name="uq_usage_account_month"),
        Index("ix_usage_region_month", "region_id", "month"),
    )


class Tariff(Base):
    """
    Rate plan definitions with component-level pricing.
    Each tariff has named rate components (fixed, energy, transmission, etc.).
    """
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tariff_id = Column(String(50), nullable=False, unique=True, index=True)
    provider = Column(String(50), nullable=False)                # PSE&G, JCP&L, etc.
    plan_name = Column(String(100))
    plan_type = Column(String(20), default="default")            # default, fixed, variable, green
    effective_date = Column(Date, nullable=False)
    end_date = Column(Date)
    customer_charge = Column(Numeric(8, 4), default=0)           # $/month fixed
    bgs_rate = Column(Numeric(8, 6), default=0)                  # $/kWh supply
    distribution_rate = Column(Numeric(8, 6), default=0)         # $/kWh distribution
    transmission_rate = Column(Numeric(8, 6), default=0)         # $/kWh transmission
    sbc_rate = Column(Numeric(8, 6), default=0)                  # $/kWh societal benefits
    nug_rate = Column(Numeric(8, 6), default=0)                  # $/kWh non-utility gen
    rider_rate = Column(Numeric(8, 6), default=0)                # $/kWh riders
    tax_rate = Column(Numeric(6, 5), default=0.06625)            # Sales tax rate
    is_active = Column(Boolean, default=True)

    billing_records = relationship("BillingData", back_populates="tariff")


class BillingData(Base):
    """
    Calculated bill breakdown per account per billing period.
    Links to tariff for rate lookup and energy_usage for consumption.
    """
    __tablename__ = "billing_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(30), nullable=False, index=True)
    bill_date = Column(Date, nullable=False, index=True)
    tariff_id = Column(String(50), ForeignKey("tariffs.tariff_id"), nullable=True)
    usage_kwh = Column(Float, nullable=False)
    effective_kwh = Column(Float)                                # Loss-adjusted

    # Bill components ($)
    customer_charge = Column(Numeric(10, 2), default=0)
    bgs_cost = Column(Numeric(10, 2), default=0)
    distribution_cost = Column(Numeric(10, 2), default=0)
    transmission_cost = Column(Numeric(10, 2), default=0)
    sbc_cost = Column(Numeric(10, 2), default=0)
    nug_cost = Column(Numeric(10, 2), default=0)
    rider_cost = Column(Numeric(10, 2), default=0)
    subtotal = Column(Numeric(10, 2))
    sales_tax = Column(Numeric(10, 2), default=0)
    total_bill = Column(Numeric(10, 2), nullable=False)

    # Rate snapshot ($/kWh at time of billing)
    bgs_rate = Column(Numeric(8, 6))
    distribution_rate = Column(Numeric(8, 6))
    transmission_rate = Column(Numeric(8, 6))
    sbc_rate = Column(Numeric(8, 6))

    # Market context
    avg_lmp = Column(Float)                                      # Avg LMP during period

    tariff = relationship("Tariff", back_populates="billing_records")

    __table_args__ = (
        UniqueConstraint("account_id", "bill_date", name="uq_billing_account_date"),
        Index("ix_billing_date", "bill_date"),
    )


class WeatherIndex(Base):
    """
    Pre-computed daily weather indices per region.
    HDD/CDD computed from raw_weather using base 65°F.
    """
    __tablename__ = "weather_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    region_id = Column(String(20), nullable=False, index=True)
    avg_temp_f = Column(Float)
    hdd = Column(Float, nullable=False)                          # max(65 - T_avg, 0)
    cdd = Column(Float, nullable=False)                          # max(T_avg - 65, 0)
    precip_in = Column(Float)

    __table_args__ = (
        UniqueConstraint("date", "region_id", name="uq_wx_date_region"),
    )


class FeatureStore(Base):
    """
    Engineered ML features per account per date.
    Pre-computed for fast model inference and Monte Carlo simulation.
    """
    __tablename__ = "feature_store"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(30), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Lagged and rolling features
    usage_kwh_lag_1 = Column(Float)
    usage_kwh_lag_12 = Column(Float)
    usage_ma_3 = Column(Float)                                   # 3-month moving average
    usage_ma_12 = Column(Float)                                  # 12-month moving average
    price_ma_3 = Column(Float)
    price_volatility = Column(Float)                             # Std dev of hourly prices

    # Weather features
    monthly_cdd = Column(Float)
    monthly_hdd = Column(Float)

    # Calendar features
    month_sin = Column(Float)
    month_cos = Column(Float)
    is_holiday_month = Column(Boolean, default=False)

    # Rate features
    effective_rate = Column(Float)
    avg_lmp = Column(Float)

    # Geo features (from Census join)
    population_density = Column(Float)
    median_income = Column(Float)

    computed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_feature_account_date"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  STATE BENCHMARK TABLE
# ─────────────────────────────────────────────────────────────────────────────

class StateBenchmark(Base):
    """
    State-level electricity price benchmarks from EIA.
    Used for geo-comparisons and national ranking.
    """
    __tablename__ = "state_benchmark"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer)                                      # 1-12 or NULL for annual
    state = Column(String(2), nullable=False, index=True)
    sector = Column(String(20), default="residential")           # residential, commercial, industrial
    avg_rate_cents_kwh = Column(Float)                           # Average rate ¢/kWh
    avg_bill_dollars = Column(Float)                             # Average monthly bill $
    total_sales_mwh = Column(Float)                              # Total sales MWh
    total_revenue_k = Column(Float)                              # Total revenue $1000s
    customer_count = Column(Integer)
    source = Column(String(20), default="eia")

    __table_args__ = (
        UniqueConstraint("year", "month", "state", "sector", name="uq_bench_yr_mo_st_sec"),
        Index("ix_bench_state_year", "state", "year"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ETL METADATA
# ─────────────────────────────────────────────────────────────────────────────

class ETLJobLog(Base):
    """
    Audit log for ETL pipeline runs.
    Tracks job status, row counts, and timing for observability.
    """
    __tablename__ = "etl_job_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False)
    source = Column(String(50))                                  # eia, noaa, census, pjm
    status = Column(String(20), nullable=False)                  # running, success, failed
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime)
    rows_ingested = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    error_message = Column(Text)
    metadata_json = Column(Text)                                 # JSON blob for extra info


# ─────────────────────────────────────────────────────────────────────────────
#  NEW DATASETS (REAL UPLOADED DATASETS)
# ─────────────────────────────────────────────────────────────────────────────

class BgsAuctionRate(Base):
    """
    New Jersey Basic Generation Service (BGS) historical auction rates.
    Sources: Table 1 (RSCP supply cents/kWh) & Table 2 (CIEP supply $/MW-day).
    """
    __tablename__ = "bgs_auction_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    edc = Column(String(20), nullable=False, index=True)        # PSE&G, JCP&L, ACE, RECO
    auction_product_type = Column(String(100))                 # RSCP, CIEP, default supply, etc.
    final_price_kwh = Column(Float)                            # rate in cents/kWh (RSCP)
    final_price_mw_day = Column(Float)                          # rate in $/MW-day (CIEP)
    sheet_source = Column(String(100))
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "edc", "auction_product_type", name="uq_bgs_yr_edc_type"),
    )


class CommunityEnergy(Base):
    """
    Aggregated Community-Scale Utility Energy Data for NJ.
    Tracks municipal electricity (kWh) and natural gas (therms) consumption.
    """
    __tablename__ = "community_energy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    municipality = Column(String(100), nullable=False, index=True)
    county = Column(String(50), nullable=False, index=True)
    muni_county = Column(String(150))
    year = Column(Integer, nullable=False, index=True)
    electric_utility = Column(String(50))
    residential_electricity = Column(Float)
    commercial_electricity = Column(Float)
    industrial_electricity = Column(Float)
    street_lighting_electricity = Column(Float)
    total_electricity_kwh = Column(Float)
    natural_gas_utility = Column(String(50))
    residential_natural_gas = Column(Float)
    commercial_natural_gas = Column(Float)
    industrial_natural_gas = Column(Float)
    street_lighting_natural_gas = Column(Float)
    total_natural_gas_therms = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("municipality", "county", "year", name="uq_comm_muni_co_yr"),
    )


class MunicipalEnergy(Base):
    """
    Historic Municipal Energy Use in New Jersey.
    Tracks sector-level municipal electricity (kWh) and natural gas (therms).
    """
    __tablename__ = "municipal_energy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    municipality = Column(String(100), nullable=False, index=True)
    county = Column(String(50), nullable=False, index=True)
    utility = Column(String(50))
    year = Column(Integer, nullable=False, index=True)
    sector = Column(String(50))                                  # Commercial, Residential, etc.
    electricity_kwh = Column(Float)
    natural_gas_therms = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())


class StateMonthlyPrice(Base):
    """
    EIA monthly average residential electricity prices per state since 2005.
    Source: eia_residential_Avg_electricity_prices.csv
    """
    __tablename__ = "state_monthly_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    state_name = Column(String(100))
    price_cents_kwh = Column(Float, nullable=False)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("date", "state", name="uq_state_mo_date_st"),
    )
