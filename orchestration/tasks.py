"""
ETL Orchestration Tasks — definitions of scheduled background jobs.
"""
from __future__ import annotations

import logging
import time
import pandas as pd
from api.state import app_state
from api.cache import invalidate_all_caches

logger = logging.getLogger(__name__)


def run_etl_pipeline_task():
    """Runs the full ingestion, transformation, merging, and DB-seeding pipeline."""
    logger.info("Executing scheduled job: run_etl_pipeline_task")
    t0 = time.time()
    try:
        from data_pipeline.pipeline_runner import run_pipeline
        # Run with force=True to ensure new/incremental data gets processed
        output_paths = run_pipeline(force=True)
        duration = time.time() - t0
        logger.info(f"Scheduled ETL pipeline completed in {duration:.1f}s. Outputs: {output_paths}")
        invalidate_all_caches()
    except Exception as e:
        logger.error(f"Scheduled ETL pipeline failed: {e}", exc_info=True)


def retrain_forecast_models_task():
    """Retrains the Prophet and SARIMA forecast models with the latest data."""
    logger.info("Executing scheduled job: retrain_forecast_models_task")
    t0 = time.time()
    try:
        from models.forecast_model import ElectricityDemandForecaster
        ensemble = ElectricityDemandForecaster()
        ensemble.train_and_evaluate()
        app_state["forecast_model"] = ensemble
        duration = time.time() - t0
        logger.info(f"Retraining of forecasting models completed in {duration:.1f}s")
        invalidate_all_caches()
    except Exception as e:
        logger.error(f"Retraining of forecasting models failed: {e}", exc_info=True)


def update_elasticity_model_task():
    """Updates the demand response elasticity model coefficients."""
    logger.info("Executing scheduled job: update_elasticity_model_task")
    t0 = time.time()
    try:
        from models.demand_model import DemandResponseModel
        from data_pipeline.features import build_feature_matrix
        from data_pipeline.cleaners import run_cleaning_pipeline
        import pandas as pd
        
        # Pull latest data from app_state
        billing = app_state.get("billing_df")
        weather = app_state.get("weather_df")
        market = app_state.get("market_df")
        
        if billing is not None and weather is not None and market is not None:
            billing_clean, weather_clean, market_clean = run_cleaning_pipeline(billing, weather, market)
            df, feature_cols, _ = build_feature_matrix(billing_clean, weather_clean, market_clean)
            
            demand_model = DemandResponseModel()
            demand_model.train(df, feature_cols)
            app_state["demand_model"] = demand_model
            duration = time.time() - t0
            logger.info(f"Demand response elasticity model updated in {duration:.1f}s")
            invalidate_all_caches()
        else:
            logger.warning("Missing datasets in app_state; skipping elasticity model update")
    except Exception as e:
        logger.error(f"Failed to update elasticity model: {e}", exc_info=True)


def fetch_eia_demand_task():
    """Fetches latest PJM demand + NJ weather data, then retrains forecast models."""
    logger.info("Executing scheduled job: fetch_eia_demand_task")
    t0 = time.time()
    try:
        from data_pipeline.eia_demand_fetcher import fetch_and_update_daily_demand
        from data_pipeline.weather_service import update_daily_weather

        # Step 1: Fetch new demand data from EIA
        output_path = fetch_and_update_daily_demand()
        logger.info(f"EIA demand data updated in {time.time() - t0:.1f}s")

        # Step 2: Fetch new weather data from Open-Meteo
        t1 = time.time()
        update_daily_weather()
        logger.info(f"Open-Meteo weather updated in {time.time() - t1:.1f}s")

        # Step 3: Retrain forecast models with fresh demand + weather
        retrain_forecast_models_task()

        total_duration = time.time() - t0
        logger.info(f"Full pipeline (demand + weather + retrain) completed in {total_duration:.1f}s")
    except Exception as e:
        logger.error(f"EIA demand fetch+retrain failed: {e}", exc_info=True)


def sync_eia861m_task():
    """Scheduled task to incrementally sync EIA-861M monthly utility data from the EIA API."""
    logger.info("Executing scheduled job: sync_eia861m_task")
    t0 = time.time()
    try:
        from database.connection import get_sync_engine, get_sync_session
        from database.models import EIA861MMonthly
        from data_pipeline.eia861m_loader import sync_eia861m_from_api
        import pandas as pd
        
        # 1. Determine latest period in DB
        engine = get_sync_engine()
        latest_period = None
        try:
            latest_period = pd.read_sql("SELECT MAX(period) as max_period FROM eia861m_monthly", con=engine).iloc[0]["max_period"]
        except Exception:
            pass

        # 2. Fetch incremental records
        df = sync_eia861m_from_api(latest_period=latest_period)
        if df.empty:
            logger.info("EIA-861M API sync: No new records to insert.")
            return

        # 3. Upsert records
        inserted_count = 0
        updated_count = 0
        with get_sync_session() as session:
            for _, row in df.iterrows():
                exists = session.query(EIA861MMonthly).filter_by(
                    year=int(row["year"]),
                    month=int(row["month"]),
                    state=str(row["state"]),
                    sector=str(row["sector"]),
                ).first()
                if exists:
                    # Update fields
                    exists.period = str(row["period"])
                    exists.data_status = str(row.get("data_status", "API"))
                    exists.revenue_k_dollars = float(row["revenue_k_dollars"]) if pd.notna(row.get("revenue_k_dollars")) else None
                    exists.sales_mwh = float(row["sales_mwh"]) if pd.notna(row.get("sales_mwh")) else None
                    exists.customers = int(row["customers"]) if pd.notna(row.get("customers")) else None
                    exists.price_cents_kwh = float(row["price_cents_kwh"]) if pd.notna(row.get("price_cents_kwh")) else None
                    updated_count += 1
                else:
                    # Insert new record
                    session.add(EIA861MMonthly(
                        year=int(row["year"]),
                        month=int(row["month"]),
                        state=str(row["state"]),
                        sector=str(row["sector"]),
                        period=str(row["period"]),
                        data_status=str(row.get("data_status", "API")),
                        revenue_k_dollars=float(row["revenue_k_dollars"]) if pd.notna(row.get("revenue_k_dollars")) else None,
                        sales_mwh=float(row["sales_mwh"]) if pd.notna(row.get("sales_mwh")) else None,
                        customers=int(row["customers"]) if pd.notna(row.get("customers")) else None,
                        price_cents_kwh=float(row["price_cents_kwh"]) if pd.notna(row.get("price_cents_kwh")) else None,
                    ))
                    inserted_count += 1
            session.commit()

        # 4. Refresh app_state DataFrame
        app_state["eia861m_df"] = pd.read_sql("SELECT * FROM eia861m_monthly", con=engine)
        duration = time.time() - t0
        logger.info(f"EIA-861M sync completed: inserted {inserted_count}, updated {updated_count} records in {duration:.1f}s")
        invalidate_all_caches()
    except Exception as e:
        logger.error(f"EIA-861M API sync task failed: {e}", exc_info=True)


def sync_openei_tariffs_task():
    """Scheduled task to sync OpenEI utility tariff metadata for top NJ utilities."""
    logger.info("Executing scheduled job: sync_openei_tariffs_task")
    t0 = time.time()
    try:
        from database.connection import get_sync_session
        from database.models import UtilityTariff
        from data_pipeline.openei_loader import sync_openei_tariffs
        
        # Sync top NJ utilities (PSE&G, JCP&L, ACE, RECO)
        df = sync_openei_tariffs(eia_utility_ids=[15477, 8901, 347, 12390], api_key="DEMO_KEY")
        if df.empty:
            logger.info("OpenEI tariff sync: No records fetched.")
            return

        # Simple bulk insert
        records = []
        for _, row in df.iterrows():
            records.append(UtilityTariff(
                eia_utility_id=int(row["eia_utility_id"]),
                label=str(row.get("label")) if pd.notna(row.get("label")) else None,
                name=str(row.get("name")) if pd.notna(row.get("name")) else None,
                uri=str(row.get("uri")) if pd.notna(row.get("uri")) else None,
                sector=str(row.get("sector")) if pd.notna(row.get("sector")) else None,
                service_type=str(row.get("service_type")) if pd.notna(row.get("service_type")) else None,
                source=str(row.get("source")) if pd.notna(row.get("source")) else None,
                source_parent=str(row.get("source_parent")) if pd.notna(row.get("source_parent")) else None,
                fixed_charge=float(row["fixed_charge"]) if pd.notna(row.get("fixed_charge")) else None,
                fixed_charge_units=str(row.get("fixed_charge_units")) if pd.notna(row.get("fixed_charge_units")) else None,
                min_charge=float(row["min_charge"]) if pd.notna(row.get("min_charge")) else None,
                min_charge_units=str(row.get("min_charge_units")) if pd.notna(row.get("min_charge_units")) else None,
                energy_rate_structure=str(row.get("energy_rate_structure")) if pd.notna(row.get("energy_rate_structure")) else None,
                energy_comments=str(row.get("energy_comments")) if pd.notna(row.get("energy_comments")) else None,
                demand_rate_structure=str(row.get("demand_rate_structure")) if pd.notna(row.get("demand_rate_structure")) else None,
                demand_comments=str(row.get("demand_comments")) if pd.notna(row.get("demand_comments")) else None,
                start_date=row.get("start_date"),
                end_date=row.get("end_date"),
                approved=bool(row.get("approved")) if pd.notna(row.get("approved")) else None,
                is_default=bool(row.get("is_default")) if pd.notna(row.get("is_default")) else None,
            ))

        with get_sync_session() as session:
            # Clean old tariffs before sync to prevent duplicate bloat
            session.query(UtilityTariff).delete()
            session.add_all(records)
            session.commit()

        duration = time.time() - t0
        logger.info(f"OpenEI tariff sync completed: inserted {len(records)} records in {duration:.1f}s")
        invalidate_all_caches()
    except Exception as e:
        logger.error(f"OpenEI tariff sync task failed: {e}", exc_info=True)


def sync_eia930_task():
    """Scheduled task to fetch latest hourly EIA-930 grid operations data."""
    logger.info("Executing scheduled job: sync_eia930_task")
    t0 = time.time()
    try:
        from database.connection import get_sync_session
        from database.models import EIA930Hourly, EIA930Generation, EIA930Subregion, EIA930Interchange
        from data_pipeline.eia930_fetcher import fetch_all_eia930
        
        # Fetch last 24 hours to accommodate API reporting lags
        data = fetch_all_eia930(hours_back=24)
        
        inserted_count = 0
        with get_sync_session() as session:
            # 1. EIA-930 hourly totals
            hourly_df = data.get("hourly", pd.DataFrame())
            for _, row in hourly_df.iterrows():
                # Check for duplicates manually to prevent UniqueConstraintViolation errors
                exists = session.query(EIA930Hourly).filter_by(
                    period=row["period"], ba_code=row["ba_code"], type_code=row["type_code"]
                ).first()
                if not exists:
                    session.add(EIA930Hourly(
                        period=row["period"],
                        ba_code=str(row["ba_code"]),
                        ba_name=str(row.get("ba_name", "")),
                        type_code=str(row["type_code"]),
                        type_name=str(row.get("type_name", "")),
                        value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
                    ))
                    inserted_count += 1

            # 2. EIA-930 generation mix
            gen_df = data.get("generation", pd.DataFrame())
            for _, row in gen_df.iterrows():
                exists = session.query(EIA930Generation).filter_by(
                    period=row["period"], ba_code=row["ba_code"], fuel_type=row["fuel_type"]
                ).first()
                if not exists:
                    session.add(EIA930Generation(
                        period=row["period"],
                        ba_code=str(row["ba_code"]),
                        ba_name=str(row.get("ba_name", "")),
                        fuel_type=str(row["fuel_type"]),
                        fuel_type_name=str(row.get("fuel_type_name", "")),
                        value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
                    ))
                    inserted_count += 1

            # 3. EIA-930 subregion demand
            sub_df = data.get("subregion", pd.DataFrame())
            for _, row in sub_df.iterrows():
                exists = session.query(EIA930Subregion).filter_by(
                    period=row["period"], subba_code=row["subba_code"]
                ).first()
                if not exists:
                    session.add(EIA930Subregion(
                        period=row["period"],
                        subba_code=str(row["subba_code"]),
                        subba_name=str(row.get("subba_name", "")),
                        parent_ba=str(row["parent_ba"]),
                        parent_ba_name=str(row.get("parent_ba_name", "")),
                        value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
                    ))
                    inserted_count += 1

            # 4. EIA-930 interchanges
            ix_df = data.get("interchange", pd.DataFrame())
            for _, row in ix_df.iterrows():
                exists = session.query(EIA930Interchange).filter_by(
                    period=row["period"], from_ba=row["from_ba"], to_ba=row["to_ba"]
                ).first()
                if not exists:
                    session.add(EIA930Interchange(
                        period=row["period"],
                        from_ba=str(row["from_ba"]),
                        from_ba_name=str(row.get("from_ba_name", "")),
                        to_ba=str(row["to_ba"]),
                        to_ba_name=str(row.get("to_ba_name", "")),
                        value_mwh=float(row["value_mwh"]) if pd.notna(row.get("value_mwh")) else None,
                    ))
                    inserted_count += 1

            session.commit()

        duration = time.time() - t0
        logger.info(f"EIA-930 grid sync completed: upserted {inserted_count} records in {duration:.1f}s")
        invalidate_all_caches()
    except Exception as e:
        logger.error(f"EIA-930 hourly sync task failed: {e}", exc_info=True)


