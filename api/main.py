"""
FastAPI application — modular, production-ready.

All endpoints live in api/routes/*.py
Business logic lives in api/services/*.py
Global state lives in api/state.py

This file handles: app creation, lifespan (data + model loading), CORS, and static files.
"""
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.state import app_state

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  LIFESPAN — runs once at startup, populates app_state
# ═════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data and train models on startup. Never retrain per-request."""
    logger.info("Starting data + model initialization...")
    data_dir = PROJECT_ROOT / "data" / "raw"

    # ── Step 1: Generate synthetic data if missing ───────────────────────────
    expected = ["billing.parquet", "weather.parquet", "pjm_market.parquet",
                "state_benchmark.parquet", "retail_plans.parquet"]
    missing = [f for f in expected if not (data_dir / f).exists()]
    if missing:
        logger.info(f"Missing files {missing} — generating synthetic data...")
        from data_pipeline.synthetic_data import generate_all
        generate_all(str(data_dir))

    # ── Step 2: Load Parquet datasets ────────────────────────────────────────
    try:
        app_state["billing_df"] = pd.read_parquet(data_dir / "billing.parquet")
        app_state["weather_df"] = pd.read_parquet(data_dir / "weather.parquet")
        app_state["market_df"] = pd.read_parquet(data_dir / "pjm_market.parquet")
        app_state["benchmark_df"] = pd.read_parquet(data_dir / "state_benchmark.parquet")
        app_state["plans_df"] = pd.read_parquet(data_dir / "retail_plans.parquet")
        logger.info(
            f"Loaded billing={len(app_state['billing_df'])}, "
            f"weather={len(app_state['weather_df'])}, "
            f"market={len(app_state['market_df'])}, "
            f"benchmark={len(app_state['benchmark_df'])}, "
            f"plans={len(app_state['plans_df'])} rows"
        )
    except Exception as e:
        logger.error(f"Data loading failed: {e}")

    # ── Step 3: Clean + feature-engineer ─────────────────────────────────────
    try:
        from data_pipeline.cleaners import run_cleaning_pipeline
        from data_pipeline.features import build_feature_matrix

        billing, weather, market = run_cleaning_pipeline(
            app_state["billing_df"], app_state["weather_df"], app_state["market_df"]
        )
        app_state["billing_df"] = billing  # use cleaned version
        df, feature_cols, _ = build_feature_matrix(billing, weather, market)
        app_state["feature_matrix"] = df
        app_state["feature_cols"] = feature_cols
        logger.info(f"Feature matrix: {df.shape[0]} rows x {len(feature_cols)} features")
    except Exception as e:
        logger.warning(f"Pipeline failed (non-fatal): {e}")

    # ── Step 4: Impact model (deterministic — no training needed) ────────────
    try:
        from models.impact_model import BillImpactModel
        app_state["impact_model"] = BillImpactModel()
        logger.info("BillImpactModel ready (deterministic)")
    except Exception as e:
        logger.warning(f"Impact model init failed: {e}")

    # ── Step 5: Forecast ensemble (trains SARIMA + Prophet) ──────────────────
    try:
        from models.forecast_model import ForecastEnsemble
        ensemble = ForecastEnsemble()
        ensemble.train_all(
            app_state["billing_df"]["total_bill"],
            app_state["billing_df"]["date"],
        )
        app_state["forecast_model"] = ensemble
        logger.info("Forecast ensemble trained and ready")
    except Exception as e:
        logger.warning(f"Forecast model training failed: {e}")

    logger.info("Initialization complete — all systems ready")
    yield
    logger.info("Shutting down...")


# ═════════════════════════════════════════════════════════════════════════════
#  APP CREATION
# ═════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Electricity Cost AI API",
    description="ML-powered electricity cost analysis, forecasting, and plan comparison for NJ",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register modular routers ────────────────────────────────────────────────
from api.routes.health import router as health_router
from api.routes.billing import router as billing_router
from api.routes.forecast import router as forecast_router
from api.routes.impact import router as impact_router
from api.routes.plans import router as plans_router
from api.routes.benchmark import router as benchmark_router
from api.routes.geo import router as geo_router

app.include_router(health_router)
app.include_router(billing_router)
app.include_router(forecast_router)
app.include_router(impact_router)
app.include_router(plans_router)
app.include_router(benchmark_router)
app.include_router(geo_router)


# ── Serve frontend static files ─────────────────────────────────────────────
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
