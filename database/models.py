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


class CensusDemographics(Base):
    """
    US Census ACS demographics table queried by CensusService by ZIP code.
    """
    __tablename__ = "census_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zip_code = Column(String(10), nullable=False, index=True, unique=True)
    state = Column(String(2), default="NJ")
    county = Column(String(50), default="Essex")
    total_population = Column(Integer, default=42500)
    median_household_income = Column(Float, default=78500.0)
    poverty_rate_pct = Column(Float, default=11.8)
    bachelor_degree_pct = Column(Float, default=36.5)
    housing_units = Column(Integer, default=17200)
    owner_occupied_pct = Column(Float, default=48.0)
    median_home_value = Column(Float, default=410000.0)
    median_age = Column(Float, default=37.2)


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


class TariffVersion(Base):
    """
    Metadata for a specific tariff version issued by a utility.
    """
    __tablename__ = "tariff_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    utility_name = Column(String(100), nullable=False)
    utility_code = Column(String(50), nullable=False, index=True)
    state = Column(String(2))
    service_territory = Column(String(100))
    regulator = Column(String(100))
    tariff_version = Column(String(50), nullable=False)
    description = Column(Text)
    regulator_order = Column(String(100))
    effective_start = Column(Date, index=True)
    effective_end = Column(Date, index=True)
    status = Column(String(20), default="active")
    ingested_at = Column(DateTime, server_default=func.now())

    rates = relationship("HistoricalUtilityTariff", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("utility_code", "tariff_version", name="uq_tariff_version_utility"),
    )


class HistoricalUtilityTariff(Base):
    """
    Normalized, historical component-level rates across utilities.
    """
    __tablename__ = "historical_utility_tariffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tariff_version_id = Column(Integer, ForeignKey("tariff_versions.id"), nullable=False, index=True)
    component = Column(String(100), nullable=False, index=True)
    component_category = Column(String(50))
    rate = Column(Float, nullable=False)
    unit = Column(String(20))
    schedule = Column(String(50), nullable=False, index=True)
    season = Column(String(20))
    ingested_at = Column(DateTime, server_default=func.now())

    version = relationship("TariffVersion", back_populates="rates")

    __table_args__ = (
        Index("ix_hist_tariff_fast_lookup", "tariff_version_id", "schedule", "component"),
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
        Index("ix_state_monthly_prices_lookup", "state", "year", "month"),
    )


class EIA861Master(Base):
    """
    Cleaned and merged EIA-861 utility/state-level dataset.
    Aggregates sales, net metering, demand response, dynamic pricing, and operational data.
    """
    __tablename__ = "eia861_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    utility_id = Column(Integer, nullable=False, index=True)
    utility_name = Column(String(200))
    state = Column(String(2), nullable=False, index=True)
    total_revenue = Column(Float)
    total_sales_mwh = Column(Float)
    total_customers = Column(Float)
    avg_price = Column(Float)
    nm_customers = Column(Float)
    nm_energy_mwh = Column(Float)
    peak_demand = Column(Float)
    total_load = Column(Float)
    demand_response_flag = Column(Integer, default=0)
    dynamic_pricing_flag = Column(Integer, default=0)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "utility_id", "state", name="uq_eia861_yr_util_st"),
        Index("ix_eia861_util_year", "utility_id", "year"),
    )


class WeatherOpenMeteo(Base):
    """Real daily weather data from Open-Meteo for New Jersey."""
    __tablename__ = "weather_openmeteo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    temp_max = Column(Float)
    temp_min = Column(Float)
    temp_avg = Column(Float)
    hdd = Column(Float)
    cdd = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())


class DailySubBaDemand(Base):
    """Daily demand data from EIA for PJM sub-BAs (AE, JC, PS, RECO)."""
    __tablename__ = "daily_subba_demand"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(Date, nullable=False, index=True)
    subba = Column(String(10), nullable=False, index=True)
    value = Column(Float)
    parent = Column(String(20), default="PJM")
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("period", "subba", name="uq_daily_subba_period_subba"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EIA-861M MONTHLY UTILITY DATA
# ─────────────────────────────────────────────────────────────────────────────

class EIA861MMonthly(Base):
    """
    EIA-861M monthly state-level electricity sales, revenue, customers, and prices.
    Source: EIA_861M_sales_revenue.xlsx (Monthly-States sheet) + EIA API incremental sync.
    One row per (year, month, state, sector).
    """
    __tablename__ = "eia861m_monthly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    sector = Column(String(20), nullable=False, default="total")  # residential, commercial, industrial, transportation, total
    period = Column(String(10), nullable=False, index=True)       # YYYY-MM format
    data_status = Column(String(20))                              # Preliminary, Final

    # Revenue (Thousand Dollars)
    revenue_k_dollars = Column(Float)
    # Sales (Megawatthours)
    sales_mwh = Column(Float)
    # Customers (Count)
    customers = Column(Integer)
    # Average Price (Cents/kWh)
    price_cents_kwh = Column(Float)

    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "month", "state", "sector", name="uq_eia861m_yr_mo_st_sec"),
        Index("ix_eia861m_state_year", "state", "year"),
        Index("ix_eia861m_period", "period"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  OPENEI UTILITY SERVICE TERRITORIES
# ─────────────────────────────────────────────────────────────────────────────

class UtilityMaster(Base):
    """
    Master list of US electric utilities from OpenEI IOU + NonIOU datasets.
    One row per (eia_utility_id, state).
    """
    __tablename__ = "utility_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eia_utility_id = Column(Integer, nullable=False, index=True)
    utility_name = Column(String(200), nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    ownership_type = Column(String(50))                            # Investor Owned, Municipal, Cooperative, etc.
    ingested_at = Column(DateTime, server_default=func.now())

    zip_lookups = relationship("UtilityZipLookup", back_populates="utility")
    rates = relationship("UtilityRate", back_populates="utility")

    __table_args__ = (
        UniqueConstraint("eia_utility_id", "state", name="uq_util_master_eiaid_st"),
    )


class UtilityZipLookup(Base):
    """
    ZIP code → utility mapping from OpenEI CSV datasets.
    Many ZIPs can map to one utility; one ZIP can have multiple utilities.
    """
    __tablename__ = "utility_zip_lookup"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zip_code = Column(String(10), nullable=False, index=True)
    eia_utility_id = Column(Integer, ForeignKey("utility_master.eia_utility_id"), nullable=False, index=True)
    utility_name = Column(String(200))
    state = Column(String(2), nullable=False, index=True)
    service_type = Column(String(20))                              # Bundled, Delivery
    ingested_at = Column(DateTime, server_default=func.now())

    utility = relationship("UtilityMaster", back_populates="zip_lookups",
                           primaryjoin="UtilityZipLookup.eia_utility_id == UtilityMaster.eia_utility_id",
                           foreign_keys="[UtilityZipLookup.eia_utility_id]")

    __table_args__ = (
        UniqueConstraint("zip_code", "eia_utility_id", name="uq_zip_lookup_zip_eiaid"),
        Index("ix_zip_lookup_state", "state"),
        Index("ix_zip_lookup_zip_state", "zip_code", "state"),
    )


class UtilityRate(Base):
    """
    Average electricity rates per utility from OpenEI CSV datasets.
    One row per (eia_utility_id, state).
    """
    __tablename__ = "utility_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eia_utility_id = Column(Integer, ForeignKey("utility_master.eia_utility_id"), nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    residential_rate = Column(Float)                               # $/kWh
    commercial_rate = Column(Float)                                # $/kWh
    industrial_rate = Column(Float)                                # $/kWh
    ingested_at = Column(DateTime, server_default=func.now())

    utility = relationship("UtilityMaster", back_populates="rates",
                           primaryjoin="UtilityRate.eia_utility_id == UtilityMaster.eia_utility_id",
                           foreign_keys="[UtilityRate.eia_utility_id]")

    __table_args__ = (
        UniqueConstraint("eia_utility_id", "state", name="uq_util_rate_eiaid_st"),
        Index("ix_utility_rates_lookup", "eia_utility_id", "state"),
    )


class UtilityTariff(Base):
    """
    Detailed tariff metadata from OpenEI API (optional monthly sync).
    Stores structured rate schedules, charges, and effective dates.
    """
    __tablename__ = "utility_tariffs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eia_utility_id = Column(Integer, nullable=False, index=True)
    label = Column(String(500))
    name = Column(String(200))
    uri = Column(String(500))
    sector = Column(String(50), index=True)                        # Residential, Commercial, Industrial
    service_type = Column(String(50))                              # Bundled, Delivery
    source = Column(String(200))
    source_parent = Column(String(200))

    # Charges
    fixed_charge = Column(Float)
    fixed_charge_units = Column(String(50))
    min_charge = Column(Float)
    min_charge_units = Column(String(50))

    # Rate structures (stored as JSON text)
    energy_rate_structure = Column(Text)
    energy_comments = Column(Text)
    demand_rate_structure = Column(Text)
    demand_comments = Column(Text)

    # Effective dates
    start_date = Column(Date)
    end_date = Column(Date)
    approved = Column(Boolean)
    is_default = Column(Boolean)

    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_tariff_eiaid", "eia_utility_id"),
        Index("ix_tariff_sector", "sector"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EIA-930 HOURLY GRID OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class EIA930Hourly(Base):
    """
    Hourly demand, demand forecast, net generation, and interchange by balancing authority.
    Source: EIA API v2 electricity/rto/region-data.
    type_code: D=Demand, DF=Day-ahead forecast, NG=Net generation, TI=Total interchange.
    """
    __tablename__ = "eia930_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(DateTime(timezone=True), nullable=False, index=True)
    ba_code = Column(String(20), nullable=False, index=True)       # PJM, CISO, etc.
    ba_name = Column(String(200))
    type_code = Column(String(5), nullable=False)                  # D, DF, NG, TI
    type_name = Column(String(50))
    value_mwh = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("period", "ba_code", "type_code", name="uq_eia930h_period_ba_type"),
        Index("ix_eia930h_ba_period", "ba_code", "period"),
    )


class EIA930Generation(Base):
    """
    Hourly generation by energy source per balancing authority.
    Source: EIA API v2 electricity/rto/fuel-type-data.
    """
    __tablename__ = "eia930_generation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(DateTime(timezone=True), nullable=False, index=True)
    ba_code = Column(String(20), nullable=False, index=True)
    ba_name = Column(String(200))
    fuel_type = Column(String(10), nullable=False)                 # COL, NG, NUC, WAT, SUN, WND, OIL, OTH
    fuel_type_name = Column(String(50))                            # Coal, Natural Gas, Nuclear, etc.
    value_mwh = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("period", "ba_code", "fuel_type", name="uq_eia930g_period_ba_fuel"),
        Index("ix_eia930g_ba_period", "ba_code", "period"),
    )


class EIA930Subregion(Base):
    """
    Hourly demand by sub-balancing authority (subregion).
    Source: EIA API v2 electricity/rto/region-sub-ba-data.
    """
    __tablename__ = "eia930_subregion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(DateTime(timezone=True), nullable=False, index=True)
    subba_code = Column(String(20), nullable=False, index=True)    # AE, JC, PS, RECO, etc.
    subba_name = Column(String(200))
    parent_ba = Column(String(20), nullable=False, index=True)     # PJM
    parent_ba_name = Column(String(200))
    value_mwh = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("period", "subba_code", name="uq_eia930s_period_subba"),
        Index("ix_eia930s_parent_period", "parent_ba", "period"),
    )


class EIA930Interchange(Base):
    """
    Hourly interchange between neighboring balancing authorities.
    Source: EIA API v2 electricity/rto/interchange-data.
    """
    __tablename__ = "eia930_interchange"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(DateTime(timezone=True), nullable=False, index=True)
    from_ba = Column(String(20), nullable=False, index=True)
    from_ba_name = Column(String(200))
    to_ba = Column(String(20), nullable=False, index=True)
    to_ba_name = Column(String(200))
    value_mwh = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("period", "from_ba", "to_ba", name="uq_eia930i_period_from_to"),
        Index("ix_eia930i_from_period", "from_ba", "period"),
    )


class UtilityServiceTerritory(Base):
    """
    EIA-861 Utility Service Territory mapping (county-level).
    Stores which utilities serve which counties.
    """
    __tablename__ = "utility_service_territories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    utility_id = Column(Integer, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    county = Column(String(100), nullable=False, index=True)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("utility_id", "state", "county", name="uq_ust_util_state_county"),
        Index("ix_ust_state_county", "state", "county"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOMER-LEVEL DATA TABLES (SYNTHETIC BILLS ARCHITECTURE)
# ─────────────────────────────────────────────────────────────────────────────

class CustomerProfile(Base):
    """
    Synthetic customer master profiles representing simulated customers.
    """
    __tablename__ = "customer_profiles"

    customer_id = Column(String(30), primary_key=True)
    utility = Column(String(50), nullable=False)
    zip_code = Column(String(10), nullable=False)
    rate_schedule = Column(String(50), nullable=False)
    meter_number = Column(String(30), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CustomerBill(Base):
    """
    Simulated customer utility bills (electric only).
    Contains structural metrics and raw texts for OCR training.
    """
    __tablename__ = "customer_bills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(30), ForeignKey("customer_profiles.customer_id"), nullable=False, index=True)
    bill_date = Column(Date, nullable=False, index=True)
    billing_period = Column(String(100))
    days = Column(Integer)
    previous_reading = Column(Integer)
    current_reading = Column(Integer)
    usage_kwh = Column(Float)
    monthly_service_charge = Column(Float)
    delivery_charge = Column(Float)
    supply_charge = Column(Float)
    tax = Column(Float)
    total_bill = Column(Float)
    
    # Bill Versioning Fields
    utility = Column(String(50))
    tariff_version_id = Column(Integer, ForeignKey("tariff_versions.id"), nullable=True)
    calculation_engine_version = Column(String(50))
    average_daily_usage = Column(Float)
    average_daily_cost = Column(Float)
    utility_message = Column(Text)
    weather_message = Column(Text)
    energy_assistance_message = Column(Text)
    net_metering_message = Column(Text)
    ocr_text = Column(Text)
    json_path = Column(String(255))

    # Async AI Status & Persistence Fields
    ai_status = Column(String(20), default="pending")  # pending, generating, completed, failed, offline
    ai_explanation = Column(Text, nullable=True)
    ai_recommendations = Column(Text, nullable=True)
    ai_model = Column(String(50), nullable=True)
    ai_prompt_version = Column(String(20), nullable=True)
    ai_latency_ms = Column(Float, nullable=True)
    ai_retry_count = Column(Integer, default=0)
    ai_error_reason = Column(Text, nullable=True)
    ai_generated_at = Column(DateTime, nullable=True)


class CustomerUsageHistory(Base):
    """
    Historical monthly electricity usage (12-month sequence) per synthetic customer.
    Used for forecasting and baseline comparisons.
    """
    __tablename__ = "customer_usage_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(30), ForeignKey("customer_profiles.customer_id"), nullable=False, index=True)
    month_label = Column(String(15), nullable=False)
    usage_kwh = Column(Float, nullable=False)
    avg_temp_f = Column(Float)


class CustomerForecast(Base):
    """
    Personalized forecast runs (30, 90, 365 days) for synthetic customer usage/costs.
    """
    __tablename__ = "customer_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(30), ForeignKey("customer_profiles.customer_id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False)
    days_ahead = Column(Integer, nullable=False)
    predicted_usage_kwh = Column(Float)
    predicted_cost = Column(Float)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    generated_at = Column(DateTime, server_default=func.now())


class CustomerSimulation(Base):
    """
    Personalized 'what-if' tariff rate and behavioral impact scenarios per customer.
    """
    __tablename__ = "customer_simulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(30), ForeignKey("customer_profiles.customer_id"), nullable=False, index=True)
    scenario_name = Column(String(100), nullable=False)
    simulated_annual_usage_kwh = Column(Float)
    simulated_annual_cost = Column(Float)
    difference_vs_actual = Column(Float)
    generated_at = Column(DateTime, server_default=func.now())


class CustomerBillOCR(Base):
    """
    Ground-truth and OCR-extracted field confidence evaluation runs.
    """
    __tablename__ = "customer_bill_ocr"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(30), ForeignKey("customer_profiles.customer_id"), nullable=False, index=True)
    bill_date = Column(Date, nullable=False)
    field_name = Column(String(50), nullable=False)
    ground_truth_value = Column(String(100))
    extracted_value = Column(String(100))
    confidence = Column(Float)
    ocr_error_flag = Column(Boolean, default=False)
    bbox = Column(String(100))


# ─────────────────────────────────────────────────────────────────────────────
#  ENTERPRISE GAP EXTENSION MODELS
# ─────────────────────────────────────────────────────────────────────────────

class SmartMeterInterval(Base):
    """
    Real-time Smart Meter analytics interval data.
    Stores hourly/sub-hourly usage, demand, voltage, and power factor.
    """
    __tablename__ = "smart_meter_intervals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(30), ForeignKey("customer_profiles.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    usage_kwh = Column(Float, nullable=False)
    demand_kw = Column(Float)
    voltage = Column(Float)
    power_factor = Column(Float)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("customer_id", "timestamp", name="uq_smart_meter_ts"),
        Index("ix_smart_meter_cust_ts", "customer_id", "timestamp"),
    )


class PjmLmpNode(Base):
    """
    PJM pricing nodes with geographical coordinate locations.
    """
    __tablename__ = "pjm_lmp_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    zone = Column(String(20), nullable=False, index=True)  # PSEG, JCPL, AECO, RECO
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


class PjmLmpHourly(Base):
    """
    Hourly Locational Marginal Pricing (LMP) components from PJM.
    """
    __tablename__ = "pjm_lmp_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String(50), ForeignKey("pjm_lmp_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    total_lmp = Column(Float, nullable=False)
    energy_comp = Column(Float, nullable=False)
    congestion_comp = Column(Float, nullable=False)
    loss_comp = Column(Float, nullable=False)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("node_id", "timestamp", name="uq_pjm_node_ts"),
    )


class UserBillCorrection(Base):
    """
    Persisted manual corrections of OCR-extracted fields by SaaS users.
    """
    __tablename__ = "user_bill_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(String(36), ForeignKey("user_bills.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(50), nullable=False)
    original_value = Column(Text)
    corrected_value = Column(Text)
    corrected_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("bill_id", "field_name", name="uq_bill_field_correction"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CPI INFLATION INDEX
# ─────────────────────────────────────────────────────────────────────────────

class CpiIndex(Base):
    """
    US Bureau of Labor Statistics Consumer Price Index (CPI-U) monthly data.
    Used for inflation-adjusting electricity bills and computing real cost trends.
    Source: cpi_monthly.csv and cpi_yearly.csv from BLS.
    """
    __tablename__ = "cpi_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    cpi = Column(Float, nullable=False)                          # CPI-U All Urban Consumers
    cpi_annual_avg = Column(Float)                               # Annual average CPI
    deflator = Column(Float)                                     # Deflator relative to base year
    inflation_pct = Column(Float)                                # YoY inflation %
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_cpi_year_month"),
        Index("ix_cpi_year_month", "year", "month"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITY RELIABILITY INDICES (SAIDI / SAIFI)
# ─────────────────────────────────────────────────────────────────────────────

class UtilityReliability(Base):
    """
    EIA-861 utility-level distribution reliability indices.
    SAIDI = System Average Interruption Duration Index (minutes/customer/year).
    SAIFI = System Average Interruption Frequency Index (interruptions/customer/year).
    CAIDI = Customer Average Interruption Duration Index (minutes/interruption).
    """
    __tablename__ = "utility_reliability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    utility_id = Column(Integer, nullable=False, index=True)
    utility_name = Column(String(200))
    state = Column(String(2), nullable=False, index=True)
    saidi = Column(Float)                                        # Minutes per customer per year
    saifi = Column(Float)                                        # Interruptions per customer per year
    caidi = Column(Float)                                        # Minutes per interruption
    customers_affected = Column(Integer)
    total_customers = Column(Integer)
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "utility_id", "state", name="uq_reliability_yr_util_st"),
        Index("ix_reliability_util_year", "utility_id", "year"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EIA-923 AGGREGATED ANALYTICAL TABLES (MANDATORY AGGREGATED SUMMARIES)
# ─────────────────────────────────────────────────────────────────────────────

class EIA923StateFuelMix(Base):
    """
    State and utility electricity generation and fuel mix aggregated from EIA-923 Schedule 1.
    No raw plant-level records stored; aggregated at (year, month, state, utility_id, fuel_code).
    """
    __tablename__ = "eia923_state_fuel_mix"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    utility_id = Column(Integer, index=True)
    nerc_region = Column(String(20))
    fuel_code = Column(String(20), nullable=False, index=True)   # NG, SUB, NUC, SUN, WND, DFO, etc.
    fuel_group = Column(String(50))                               # Gas, Coal, Nuclear, Solar, Wind, Hydro, Petroleum, Other
    net_generation_mwh = Column(Float, default=0.0)
    total_mmbtu = Column(Float, default=0.0)
    clean_share_pct = Column(Float)                              # % renewable / zero carbon
    fossil_share_pct = Column(Float)                             # % fossil generation
    carbon_intensity_g_kwh = Column(Float)                       # Calculated Scope 2 gCO2e/kWh
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "month", "state", "utility_id", "fuel_code", name="uq_eia923_state_yr_mo_util_fuel"),
        Index("ix_eia923_state_date", "state", "year", "month"),
        Index("ix_eia923_util_date", "utility_id", "year", "month"),
    )


class EIA923FuelCostTrend(Base):
    """
    State and utility monthly delivered fuel purchase costs ($/MMBtu and cents/MMBtu) from EIA-923 Schedule 5.
    No raw plant-level records stored; aggregated at (year, month, state, utility_id, fuel_group).
    """
    __tablename__ = "eia923_fuel_cost_trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    utility_id = Column(Integer, index=True)
    fuel_group = Column(String(30), nullable=False, index=True)   # Natural Gas, Coal, Petroleum
    avg_cost_cents_mmbtu = Column(Float)                          # Weighted average delivery cost (cents/MMBtu)
    avg_cost_dollars_mmbtu = Column(Float)                        # Weighted average delivery cost ($/MMBtu)
    total_quantity_delivered = Column(Float)                      # Total quantity purchased
    avg_heat_content = Column(Float)                              # MMBtu/unit
    mom_change_pct = Column(Float)                                # Month-over-Month price change %
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "month", "state", "utility_id", "fuel_group", name="uq_eia923_cost_yr_mo_util_fuel"),
        Index("ix_eia923_cost_state_date", "state", "year", "month"),
        Index("ix_eia923_cost_util_date", "utility_id", "year", "month"),
    )


class EIA923StorageSummary(Base):
    """
    State-level annual energy storage performance aggregated from EIA-923 Schedule 1 Energy Storage.
    No raw plant-level records stored; aggregated at (year, state, technology).
    """
    __tablename__ = "eia923_storage_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    technology = Column(String(50), nullable=False, default="Batteries")  # Batteries, Pumped Hydro, etc.
    total_discharge_mwh = Column(Float, default=0.0)
    total_charge_mwh = Column(Float, default=0.0)
    roundtrip_efficiency_pct = Column(Float)                      # Discharge MWh / Charge MWh * 100
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("year", "state", "technology", name="uq_eia923_storage_yr_st_tech"),
        Index("ix_eia923_storage_state_year", "state", "year"),
    )


class EIA923PlantFrame(Base):
    """
    Master plant metadata lookup table from EIA-923 Schedule 6.
    Links Plant IDs to operating utilities, states, NERC regions, and NAICS codes.
    """
    __tablename__ = "eia923_plant_frame"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, unique=True, index=True)
    plant_name = Column(String(200))
    operator_id = Column(Integer, index=True)
    operator_name = Column(String(200))
    state = Column(String(2), nullable=False, index=True)
    nerc_region = Column(String(20))
    census_region = Column(String(50))
    naics_code = Column(Integer)
    sector_number = Column(Integer)
    sector_name = Column(String(100))
    ingested_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_eia923_plant_operator", "operator_id", "state"),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  AUTH MODELS — imported here so Base.metadata.create_all includes them
# ─────────────────────────────────────────────────────────────────────────────
# This import must remain at the bottom to avoid a circular import
# (auth_models.py imports Base from this file).
import database.auth_models as _auth_models  # noqa: E402, F401

