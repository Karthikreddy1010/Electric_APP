"""
ETL Orchestration Tasks — definitions of scheduled background jobs.
"""
from __future__ import annotations

import logging
import time
from api.state import app_state

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
        else:
            logger.warning("Missing datasets in app_state; skipping elasticity model update")
    except Exception as e:
        logger.error(f"Failed to update elasticity model: {e}", exc_info=True)
