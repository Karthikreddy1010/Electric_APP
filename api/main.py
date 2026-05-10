"""
FastAPI main application with all REST endpoints.
Serves: /forecast, /impact, /benchmark, /plan-simulation, /bill-breakdown, /trends
"""
import sys
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.schemas import (
    ForecastRequest, ForecastResponse, ForecastPoint,
    ImpactRequest, ImpactResponse, ComponentImpact,
    BenchmarkRequest, BenchmarkResponse, StateData,
    PlanSimRequest, PlanSimResponse, PlanResult,
    BillBreakdownResponse, TrendResponse, HealthResponse,
)

logger = logging.getLogger(__name__)

# ===== Global state for loaded models/data =====
app_state = {
    "billing_df": None,
    "weather_df": None,
    "market_df": None,
    "benchmark_df": None,
    "plans_df": None,
    "impact_model": None,
    "forecast_model": None,
    "feature_matrix": None,
    "feature_cols": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data and models on startup."""
    logger.info("Loading data and models...")
    data_dir = PROJECT_ROOT / "data" / "raw"
    
    if not data_dir.exists():
        logger.info("No data found - generating synthetic data...")
        from data_pipeline.synthetic_data import generate_all
        generate_all(str(data_dir))
    
    # Load datasets
    try:
        app_state["billing_df"] = pd.read_parquet(data_dir / "billing.parquet")
        app_state["weather_df"] = pd.read_parquet(data_dir / "weather.parquet")
        app_state["market_df"] = pd.read_parquet(data_dir / "pjm_market.parquet")
        app_state["benchmark_df"] = pd.read_parquet(data_dir / "state_benchmark.parquet")
        app_state["plans_df"] = pd.read_parquet(data_dir / "retail_plans.parquet")
        logger.info("All datasets loaded successfully")
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
    
    # Build feature matrix and train impact model
    try:
        from data_pipeline.cleaners import run_cleaning_pipeline
        from data_pipeline.features import build_feature_matrix
        from models.impact_model import BillImpactModel
        
        billing, weather, market = run_cleaning_pipeline(
            app_state["billing_df"], app_state["weather_df"], app_state["market_df"]
        )
        df, feature_cols, target = build_feature_matrix(billing, weather, market)
        app_state["feature_matrix"] = df
        app_state["feature_cols"] = feature_cols
        
        model = BillImpactModel()
        model.train(df[feature_cols], df[target])
        app_state["impact_model"] = model
        logger.info("Impact model trained and ready")
    except Exception as e:
        logger.warning(f"Impact model training failed: {e}")
    
    # Train forecast model
    try:
        from models.forecast_model import ForecastEnsemble
        billing = app_state["billing_df"]
        ensemble = ForecastEnsemble()
        ensemble.train_all(billing["total_bill"], billing["date"])
        app_state["forecast_model"] = ensemble
        logger.info("Forecast ensemble trained and ready")
    except Exception as e:
        logger.warning(f"Forecast model training failed: {e}")
    
    yield
    logger.info("Shutting down...")


# ===== FastAPI App =====
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

# Serve frontend static files
from fastapi.staticfiles import StaticFiles
frontend_dir = PROJECT_ROOT / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


# ===== Endpoints =====

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        models_loaded={
            "impact": app_state["impact_model"] is not None,
            "forecast": app_state["forecast_model"] is not None,
        },
        data_freshness=str(app_state["billing_df"]["date"].max()) 
            if app_state["billing_df"] is not None else None,
    )


@app.post("/forecast", response_model=ForecastResponse)
async def forecast_costs(req: ForecastRequest):
    """Generate electricity cost forecast."""
    if app_state["forecast_model"] is None:
        raise HTTPException(500, "Forecast model not loaded")
    
    try:
        ensemble = app_state["forecast_model"]
        preds = ensemble.predict_ensemble(steps=req.months_ahead)
        
        # Build forecast dates
        last_date = pd.to_datetime(app_state["billing_df"]["date"].max())
        future_dates = pd.date_range(last_date + pd.DateOffset(months=1),
                                     periods=req.months_ahead, freq="MS")
        
        forecasts = []
        for i in range(len(preds)):
            fp = ForecastPoint(
                month=future_dates[i].strftime("%Y-%m"),
                forecast=round(float(preds["forecast_ensemble"].iloc[i]), 2),
                lower=round(float(preds["lower"].iloc[i]), 2) if req.include_ci else None,
                upper=round(float(preds["upper"].iloc[i]), 2) if req.include_ci else None,
            )
            forecasts.append(fp)
        
        return ForecastResponse(
            model_type=req.model_type,
            horizon_months=req.months_ahead,
            forecasts=forecasts,
            metrics={"aic": float(ensemble.sarima.fitted.aic)} if ensemble.sarima.fitted else {},
        )
    except Exception as e:
        raise HTTPException(500, f"Forecast error: {str(e)}")


@app.post("/impact", response_model=ImpactResponse)
async def bill_impact_analysis(req: ImpactRequest):
    """Analyze drivers of electricity bill changes using SHAP."""
    model = app_state["impact_model"]
    if model is None:
        raise HTTPException(500, "Impact model not loaded")
    
    df = app_state["feature_matrix"]
    feature_cols = app_state["feature_cols"]
    
    try:
        explanation = model.explain(df[feature_cols])
        category_impacts = model.get_component_impact(df[feature_cols])
        
        drivers = []
        for item in explanation["latest_breakdown"][:req.top_n]:
            sv = item["shap_value"]
            drivers.append(ComponentImpact(
                feature=item["feature"],
                shap_value=round(sv, 4),
                direction="increases" if sv > 0 else "decreases",
                magnitude="high" if abs(sv) > 5 else ("medium" if abs(sv) > 1 else "low"),
            ))
        
        return ImpactResponse(
            base_value=round(explanation["base_value"], 2),
            predicted_value=round(explanation["predicted_value"], 2),
            top_drivers=drivers,
            category_impacts=category_impacts,
            model_metrics=model.metrics,
        )
    except Exception as e:
        raise HTTPException(500, f"Impact analysis error: {str(e)}")


@app.post("/benchmark", response_model=BenchmarkResponse)
async def state_benchmark(req: BenchmarkRequest):
    """Compare electricity rates across US states."""
    bench_df = app_state["benchmark_df"]
    if bench_df is None:
        raise HTTPException(500, "Benchmark data not loaded")
    
    year_data = bench_df[bench_df["year"] == req.year].copy()
    if year_data.empty:
        raise HTTPException(404, f"No data for year {req.year}")
    
    year_data = year_data.sort_values("avg_rate")
    year_data["rank"] = range(1, len(year_data) + 1)
    
    focus = year_data[year_data["state"] == req.compare_state]
    if focus.empty:
        raise HTTPException(404, f"State {req.compare_state} not found")
    
    focus_row = focus.iloc[0]
    
    states = [
        StateData(
            state=row["state"], avg_rate=round(row["avg_rate"], 4),
            avg_bill=round(row["avg_bill"], 2), rank=int(row["rank"]),
        ) for _, row in year_data.iterrows()
    ]
    
    return BenchmarkResponse(
        year=req.year,
        focus_state=StateData(
            state=focus_row["state"], avg_rate=round(focus_row["avg_rate"], 4),
            avg_bill=round(focus_row["avg_bill"], 2), rank=int(focus_row["rank"]),
        ),
        national_avg=round(year_data["avg_rate"].mean(), 4),
        states=states,
    )


@app.post("/plan-simulation", response_model=PlanSimResponse)
async def plan_simulation(req: PlanSimRequest):
    """Run Monte Carlo simulation comparing electricity plans."""
    plans_df = app_state["plans_df"]
    billing_df = app_state["billing_df"]
    if plans_df is None or billing_df is None:
        raise HTTPException(500, "Data not loaded")
    
    try:
        from models.simulation_model import PlanSimulator
        
        sim = PlanSimulator(
            n_simulations=req.n_simulations,
            horizon_months=req.horizon_months,
        )
        
        historical_usage = billing_df["usage_kwh"].values * (1 + req.usage_growth_pct/100)
        plans = plans_df.to_dict(orient="records")
        
        comparison = sim.compare_plans(plans, historical_usage)
        
        results = []
        for _, row in comparison.iterrows():
            results.append(PlanResult(
                provider=row["provider"],
                plan_type=row["plan_type"],
                rate=row["rate"],
                expected_annual_cost=round(row["expected_annual_cost"], 2),
                median_annual_cost=round(row["median_annual_cost"], 2),
                std_annual_cost=round(row["std_annual_cost"], 2),
                p5_annual_cost=round(row["p5_annual_cost"], 2),
                p95_annual_cost=round(row["p95_annual_cost"], 2),
                risk_score=round(row["risk_score"], 1),
                monthly_expected=row["monthly_expected"],
            ))
        
        default_cost = comparison[comparison["provider"].str.contains("BGS|PSE&G")]
        default_annual = default_cost["expected_annual_cost"].values[0] if len(default_cost) > 0 else results[0].expected_annual_cost
        best = comparison.iloc[0]
        
        return PlanSimResponse(
            comparison=results,
            recommended=best["provider"],
            savings_vs_default=round(default_annual - best["expected_annual_cost"], 2),
        )
    except Exception as e:
        raise HTTPException(500, f"Simulation error: {str(e)}")


@app.get("/bill-breakdown", response_model=list[BillBreakdownResponse])
async def bill_breakdown(months: int = Query(12, ge=1, le=84)):
    """Get detailed bill component breakdown for recent months."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    
    recent = billing.tail(months).copy()
    results = []
    for _, row in recent.iterrows():
        results.append(BillBreakdownResponse(
            date=str(row["date"].date()) if hasattr(row["date"], 'date') else str(row["date"]),
            total_bill=round(float(row["total_bill"]), 2),
            components={
                "bgs": round(float(row["bgs_cost"]), 2),
                "transmission": round(float(row["transmission_cost"]), 2),
                "distribution": round(float(row["distribution_cost"]), 2),
                "sbc": round(float(row["sbc_cost"]), 2),
                "nug": round(float(row["nug_cost"]), 2),
                "dr_credit": round(float(row["dr_credit"]), 2),
                "tax": round(float(row["sales_tax"]), 2),
            },
            rates={
                "bgs": round(float(row["bgs_rate"]), 5),
                "transmission": round(float(row["transmission_rate"]), 5),
                "distribution": round(float(row["distribution_rate"]), 5),
                "sbc": round(float(row["sbc_rate"]), 5),
                "nug": round(float(row["nug_rate"]), 5),
            },
            usage_kwh=round(float(row["usage_kwh"]), 1),
            effective_rate=round(float(row["total_bill"]) / float(row["usage_kwh"]), 5),
        ))
    return results


@app.get("/trends")
async def get_trends(months: int = Query(36, ge=6, le=84)):
    """Get historical trend data."""
    billing = app_state["billing_df"]
    if billing is None:
        raise HTTPException(500, "Data not loaded")
    
    df = billing.tail(months).copy()
    df["effective_rate"] = df["total_bill"] / df["usage_kwh"]
    df["yoy_change"] = df["total_bill"].pct_change(12) * 100
    
    return {
        "months": df["date"].dt.strftime("%Y-%m").tolist(),
        "total_bills": df["total_bill"].round(2).tolist(),
        "usage": df["usage_kwh"].round(1).tolist(),
        "rates": df["effective_rate"].round(5).tolist(),
        "yoy_changes": [round(x, 1) if pd.notna(x) else None for x in df["yoy_change"]],
    }


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
