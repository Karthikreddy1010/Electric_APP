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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.middleware.rate_limiter import RateLimiterMiddleware

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.state import app_state
from database.connection import init_db, close_db
from api.cache import init_cache, close_cache

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  LIFESPAN — runs once at startup, populates app_state
# ═════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data and train models on startup. Never retrain per-request."""
    logger.info("Starting data + model initialization...")

    # Initialize DB connection pool
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Initialize cache backend
    try:
        await init_cache()
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")

    # Start background scheduler
    try:
        from orchestration.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

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
        app_state["plans_df"] = pd.read_parquet(data_dir / "retail_plans.parquet")
        
        if (data_dir / "pseg_rate_history.csv").exists():
            app_state["pseg_history_df"] = pd.read_csv(data_dir / "pseg_rate_history.csv")
            logger.info(f"Loaded pseg_history={len(app_state['pseg_history_df'])} rows")
            
        logger.info(
            f"Loaded billing={len(app_state['billing_df'])}, "
            f"weather={len(app_state['weather_df'])}, "
            f"market={len(app_state['market_df'])}, "
            f"plans={len(app_state['plans_df'])} rows"
        )
        from models.pjm_market_physics import DEFAULT_PJM
        app_state["pjm_defaults"] = DEFAULT_PJM
    except Exception as e:
        logger.error(f"Data loading failed: {e}")

    # ── Step 2b: Build real benchmark from EIA data ──────────────────────────
    try:
        processed_path = PROJECT_ROOT / "data" / "processed" / "state_benchmark.parquet"
        price_path = data_dir / "Avg_price_Electricity.xlsx"
        sales_path = data_dir / "salesofelectricity.xlsx"

        if price_path.exists() and sales_path.exists():
            from data_pipeline.benchmark_builder import build_state_benchmark
            app_state["benchmark_df"] = build_state_benchmark(price_path, sales_path)
            logger.info(f"EIA benchmark built: {len(app_state['benchmark_df'])} rows, "
                        f"{app_state['benchmark_df']['state'].nunique()} states")
        elif processed_path.exists():
            app_state["benchmark_df"] = pd.read_parquet(processed_path)
            logger.info(f"Loaded cached benchmark: {len(app_state['benchmark_df'])} rows")
        else:
            app_state["benchmark_df"] = pd.read_parquet(data_dir / "state_benchmark.parquet")
            logger.info(f"Loaded legacy benchmark: {len(app_state['benchmark_df'])} rows")
    except Exception as e:
        logger.warning(f"Benchmark build failed, falling back: {e}")
        try:
            app_state["benchmark_df"] = pd.read_parquet(data_dir / "state_benchmark.parquet")
        except Exception:
            logger.error("No benchmark data available")

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

    # ── Step 4b: Demand model (learned elasticity) ───────────────────────────
    try:
        from models.demand_model import DemandResponseModel
        demand_model = DemandResponseModel()
        demand_model.train(app_state["feature_matrix"], app_state["feature_cols"])
        app_state["demand_model"] = demand_model
        logger.info(f"DemandResponseModel trained (elasticity={demand_model.get_learned_elasticity():.4f})")
    except Exception as e:
        logger.warning(f"Demand model training failed (non-fatal): {e}")

    # ── Step 4c: Causal model ────────────────────────────────────────────────
    try:
        from api.services.causal_model_service import CausalModelService
        causal_svc = CausalModelService()
        causal_svc.fit(app_state["feature_matrix"])
        app_state["causal_service"] = causal_svc
        logger.info("CausalModelService (DML) fitted")
    except Exception as e:
        logger.warning(f"Causal model fit failed (non-fatal): {e}")

    # ── Step 4d: Rate Covariance Matrix for Simulation ───────────────────────
    try:
        from api.services.simulation_service_v2 import build_rate_covariance
        if app_state.get("billing_df") is not None:
            app_state["rate_cov_matrix"] = build_rate_covariance(app_state["billing_df"])
            logger.info("Rate covariance matrix built")
    except Exception as e:
        logger.warning(f"Rate covariance matrix build failed (non-fatal): {e}")

    # ── Step 5: Forecast ensemble (trains SARIMA + Prophet) ──────────────────
    try:
        from models.forecast_model import ElectricityDemandForecaster
        ensemble = ElectricityDemandForecaster()
        ensemble.train_and_evaluate()
        app_state["forecast_model"] = ensemble
        logger.info("Demand Forecast ensemble trained and ready")
    except Exception as e:
        logger.warning(f"Forecast model training failed: {e}")

    # ── Step 6: Build monthly geo data from benchmarks or StateMonthlyPrice ────────
    try:
        from database.connection import get_sync_engine
        engine = get_sync_engine()

        # Load the new real datasets into app_state
        app_state["bgs_auction_df"] = pd.read_sql("SELECT * FROM bgs_auction_rates", con=engine)
        app_state["community_energy_df"] = pd.read_sql("SELECT * FROM community_energy", con=engine)
        app_state["municipal_energy_df"] = pd.read_sql("SELECT * FROM municipal_energy", con=engine)
        app_state["state_monthly_prices_df"] = pd.read_sql("SELECT * FROM state_monthly_prices", con=engine)

        logger.info(
            f"Loaded database tables: "
            f"bgs_auction={len(app_state['bgs_auction_df'])}, "
            f"community_energy={len(app_state['community_energy_df'])}, "
            f"municipal_energy={len(app_state['municipal_energy_df'])}, "
            f"state_monthly_prices={len(app_state['state_monthly_prices_df'])}"
        )

        # Build geo_monthly_df from state_monthly_prices directly
        mo_df = app_state["state_monthly_prices_df"].copy()
        
        # Mapping of average monthly usage by state for bill estimates
        STATE_AVG_MONTHLY_USAGE = {
            "AL": 1200, "AK": 570, "AZ": 1060, "AR": 1120, "CA": 530,
            "CO": 690, "CT": 730, "DE": 930, "DC": 710, "FL": 1100,
            "GA": 1120, "HI": 510, "ID": 960, "IL": 720, "IN": 940,
            "IA": 870, "KS": 930, "KY": 1130, "LA": 1220, "ME": 530,
            "MD": 1000, "MA": 600, "MI": 630, "MN": 780, "MS": 1200,
            "MO": 1060, "MT": 810, "NE": 960, "NV": 910, "NH": 590,
            "NJ": 680, "NM": 640, "NY": 570, "NC": 1060, "ND": 1110,
            "OH": 870, "OK": 1100, "OR": 910, "PA": 830, "RI": 570,
            "SC": 1130, "SD": 1020, "TN": 1210, "TX": 1140, "UT": 790,
            "VT": 540, "VA": 1120, "WA": 950, "WV": 1090, "WI": 680,
            "WY": 860,
        }

        records = []
        for _, row in mo_df.iterrows():
            st = row["state"]
            yr = int(row["year"])
            mo = int(row["month"])
            rate_cents = float(row["price_cents_kwh"])
            rate_dollars = rate_cents / 100.0
            usage = float(STATE_AVG_MONTHLY_USAGE.get(st, 750.0))
            bill = usage * rate_dollars
            
            records.append({
                "state": st,
                "year": yr,
                "month": mo,
                "month_str": f"{yr}-{mo:02d}",
                "avg_rate": rate_dollars,
                "avg_bill": bill,
                "usage_kwh": usage,
            })
            
        geo_df = pd.DataFrame(records)
        geo_df = geo_df.sort_values(["state", "year", "month"]).reset_index(drop=True)
        geo_df["yoy_change"] = geo_df.groupby("state")["avg_bill"].pct_change(12) * 100
        geo_df["yoy_change"] = geo_df["yoy_change"].round(1)
        
        app_state["geo_monthly_df"] = geo_df
        logger.info(f"Geo monthly data built from real EIA monthly prices: {len(app_state['geo_monthly_df'])} records")

    except Exception as e:
        logger.warning(f"Failed to load database tables: {e}. Falling back to benchmark build.")
        try:
            from api.services.geo_insights_service import build_monthly_state_data
            app_state["geo_monthly_df"] = build_monthly_state_data(app_state["benchmark_df"])
            logger.info(f"Geo monthly data built (fallback): {len(app_state['geo_monthly_df'])} records")
        except Exception as ex:
            logger.error(f"Geo data build fallback failed: {ex}")

    logger.info("Initialization complete -- all systems ready")
    yield
    logger.info("Shutting down...")
    try:
        await close_cache()
    except Exception as e:
        logger.error(f"Failed to close cache: {e}")
    try:
        await close_db()
    except Exception as e:
        logger.error(f"Failed to close database: {e}")


# ═════════════════════════════════════════════════════════════════════════════
#  APP CREATION
# ═════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Electricity Cost AI API",
    description="ML-powered electricity cost analysis, forecasting, and plan comparison for NJ",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RateLimiterMiddleware, requests_limit=100, window_seconds=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Register modular routers ────────────────────────────────────────────────
from api.routes.health import router as health_router
from api.routes.dashboard import router as dashboard_router
from api.routes.billing import router as billing_router
from api.routes.geo_insights import router as geo_insights_router
from api.routes.impact import router as impact_router
from api.routes.bill_impact import router as bill_impact_router
from api.routes.benchmark import router as benchmark_router
from api.routes.forecast import router as forecast_router
from api.routes.plans import router as plans_router
from api.routes.bgs import router as bgs_router
from api.routes.municipal import router as municipal_router

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(billing_router)
app.include_router(geo_insights_router)
app.include_router(impact_router)
app.include_router(bill_impact_router)
app.include_router(benchmark_router)
app.include_router(forecast_router)
app.include_router(plans_router)
app.include_router(bgs_router)
app.include_router(municipal_router)


# ── Serve frontend static files ─────────────────────────────────────────────
frontend_dir = PROJECT_ROOT / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
