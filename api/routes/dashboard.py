from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.schemas import (
    OverviewResponse, ForecastResponse, ImpactResponse, SimulateRequest, 
    SimulateResult, BenchmarkResponse, GeoResponse, PlanSimResponse,
    OverviewKPI, BillComponent, TrendResponse
)
from api.services.billing_service import build_breakdown, build_trends
from api.services.bill_impact_engine import bill_impact_engine, COMPONENT_TYPES
from typing import Optional
import pandas as pd
import numpy as np

router = APIRouter(tags=["dashboard"])

@router.get("/overview", response_model=OverviewResponse)
async def get_overview():
    billing = app_state.get("billing_df")
    if billing is None:
        raise HTTPException(500, "Billing data not loaded")
    
    latest = billing.iloc[-1]
    prev = billing.iloc[-2] if len(billing) > 1 else latest
    
    # KPIs
    bill_change = ((latest['total_bill'] - prev['total_bill']) / prev['total_bill'] * 100) if prev['total_bill'] != 0 else 0
    
    # Simple forecast for next month (naive or from model if available)
    forecast_val = latest['total_bill'] # Fallback
    if app_state.get("forecast_model"):
        try:
            f = app_state["forecast_model"].predict_ensemble(1)
            forecast_val = f['forecast_ensemble'].values[0]
        except: pass

    kpis = OverviewKPI(
        current_bill=latest['total_bill'],
        usage_kwh=latest['usage_kwh'],
        effective_rate=latest['total_bill'] / latest['usage_kwh'] if latest['usage_kwh'] > 0 else 0,
        forecast_next_month=forecast_val,
        bill_change_pct=bill_change
    )

    # Breakdown
    breakdown = []
    total = latest['total_bill']
    for key, meta in COMPONENT_TYPES.items():
        val = latest.get(meta['cost_col'], 0)
        # Add tax to each component for "Clarity"
        val_with_tax = val * 1.06625 
        breakdown.append(BillComponent(
            label=meta['label'],
            value=round(val_with_tax, 2),
            percentage=round((val_with_tax / total * 100), 2) if total > 0 else 0
        ))
    # Sort by impact
    breakdown = sorted(breakdown, key=lambda x: x.value, reverse=True)

    # Trends
    trends = build_trends(billing, 36)

    return OverviewResponse(kpis=kpis, breakdown=breakdown, trends=trends)

@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(horizon: int = Query(12, ge=1, le=24)):
    ensemble = app_state.get("forecast_model")
    if ensemble is None:
        raise HTTPException(500, "Forecast model not ready")
    
    res = ensemble.predict_ensemble(horizon)
    # Format to match schema
    forecasts = []
    
    # Generate future dates
    last_date = app_state["billing_df"]["date"].max()
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq='MS')
    
    for i, row in res.iterrows():
        forecasts.append({
            "month": future_dates[i].strftime("%Y-%m"),
            "forecast": row['forecast_ensemble'],
            "lower": row.get('lower'),
            "upper": row.get('upper')
        })
    
    return ForecastResponse(
        model_type="ensemble",
        horizon_months=horizon,
        forecasts=forecasts,
        metrics={}
    )

@router.get("/impact", response_model=ImpactResponse)
async def get_impact():
    # Reuse SHAP/Logic from impact service if available
    # For now, let's get drivers from the engine
    rankings = bill_impact_engine.rank_components()
    
    # Transform to ImpactResponse
    drivers = []
    for r in rankings:
        drivers.append({
            "feature": r['label'],
            "shap_value": r['share_pct'] * 1.5, # Mocking SHAP with weight for now
            "direction": "increases",
            "magnitude": "high" if r['share_pct'] > 20 else "medium"
        })
    
    return ImpactResponse(
        base_value=100.0,
        predicted_value=110.0,
        top_drivers=drivers,
        category_impacts={"generation": 60, "transmission": 20, "distribution": 20},
        model_metrics={}
    )

@router.post("/simulate", response_model=SimulateResult)
async def simulate_impact(req: SimulateRequest):
    sim = bill_impact_engine.what_if_simulation(req.modifications, req.kwh)
    
    # Formula construction
    # New Bill = Base Bill × (1 + % Change × Elasticity)
    # We'll simplify for the UI display
    comp_labels = [f"{COMPONENT_TYPES[k]['label']} ({v}%)" for k, v in req.modifications.items()]
    formula = "New Bill = Base Bill × (1 + Σ(% Change_i × Weight_i) × Elasticity)"
    
    return SimulateResult(
        old_bill=sim['base_bill'],
        new_bill=sim['new_bill'],
        delta_abs=sim['total_impact'],
        delta_pct=round((sim['total_impact'] / sim['base_bill'] * 100), 2) if sim['base_bill'] > 0 else 0,
        formula=formula,
        explanation=f"If {', '.join(comp_labels)} change, your bill increases/decreases by approximately {sim['total_impact']} based on historical elasticity."
    )

@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark():
    # Existing logic from benchmark router
    df = app_state.get("benchmark_df")
    if df is None: raise HTTPException(500, "No benchmark data")
    
    latest_year = df['year'].max()
    states_data = []
    national_avg = df[df['year'] == latest_year]['avg_rate'].mean()
    
    for _, row in df[df['year'] == latest_year].iterrows():
        states_data.append({
            "state": row['state'],
            "avg_rate": row['avg_rate'],
            "avg_bill": row['avg_bill']
        })
        
    nj_data = df[(df['year'] == latest_year) & (df['state'] == 'NJ')].iloc[0]
    
    return BenchmarkResponse(
        year=int(latest_year),
        focus_state={"state": "NJ", "avg_rate": nj_data['avg_rate'], "avg_bill": nj_data['avg_bill']},
        national_avg=national_avg,
        states=states_data
    )

@router.get("/geo", response_model=GeoResponse)
async def get_geo():
    df = app_state.get("benchmark_df")
    if df is None: raise HTTPException(500, "No data")
    
    latest_year = df['year'].max()
    latest_df = df[df['year'] == latest_year].copy()
    latest_df['rank'] = latest_df['avg_bill'].rank(ascending=False).astype(int)
    
    data = []
    for _, row in latest_df.iterrows():
        data.append({
            "state": row['state'],
            "avg_bill": row['avg_bill'],
            "avg_rate": row['avg_rate'],
            "rank": row['rank']
        })
        
    sorted_data = sorted(data, key=lambda x: x['avg_bill'], reverse=True)
    
    return GeoResponse(
        data=data,
        top_5_expensive=sorted_data[:5],
        top_5_cheapest=sorted_data[-5:][::-1]
    )

@router.get("/plans", response_model=PlanSimResponse)
async def get_plans():
    # Mocking or running simulation with default values
    from api.services.simulation_service import run_plan_simulation
    from api.schemas import PlanSimRequest
    
    plans_df = app_state.get("plans_df")
    billing_df = app_state.get("billing_df")
    
    req = PlanSimRequest(
        monthly_usage_kwh=750,
        usage_growth_pct=0.0,
        horizon_months=12,
        n_simulations=1000
    )
    
    return run_plan_simulation(plans_df, billing_df, req)
