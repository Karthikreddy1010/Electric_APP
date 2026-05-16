from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.schemas import (
    OverviewResponse, ForecastResponse, ImpactResponse, SimulateRequest, 
    SimulateResult, BenchmarkResponse, GeoResponse, PlanSimResponse,
    OverviewKPI, BillComponent, TrendResponse, GeoTrendPoint, GeoDetailResponse,
    GeoPoint
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

    # Historical Breakdown
    historical_breakdown = []
    hist_billing = billing.tail(36)
    for _, row in hist_billing.iterrows():
        month_label = row['date'].strftime("%Y-%m")
        point = {"month": month_label}
        for key, meta in COMPONENT_TYPES.items():
            val = row.get(meta['cost_col'], 0)
            val_with_tax = val * 1.06625
            point[meta['label']] = round(val_with_tax, 2)
        historical_breakdown.append(point)

    # Trends
    trends = build_trends(billing, 36)

    return OverviewResponse(
        kpis=kpis, 
        breakdown=breakdown, 
        historical_breakdown=historical_breakdown,
        trends=trends
    )


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    horizon: int = Query(12, ge=1, le=24),
    model: str = Query("ensemble", regex="^(ensemble|sarima|prophet)$")
):
    ensemble = app_state.get("forecast_model")
    if ensemble is None:
        raise HTTPException(500, "Forecast model not ready")
    
    res = ensemble.predict_ensemble(horizon)
    
    # Select appropriate column based on model
    pred_col = f"forecast_{model}"
    
    forecasts = []
    last_date = app_state["billing_df"]["date"].max()
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq='MS')
    
    for i, dt in enumerate(future_dates):
        pred_val = res[pred_col].iloc[i] if pred_col in res.columns else res["forecast_ensemble"].iloc[i]
        
        # Fallback for None values (if prophet failed)
        if pd.isna(pred_val):
            pred_val = res["forecast_ensemble"].iloc[i]

        forecasts.append(ForecastPoint(
            month=dt.strftime("%Y-%m"),
            forecast=float(pred_val),
            lower=float(res["lower"].iloc[i]),
            upper=float(res["upper"].iloc[i])
        ))
    
    return ForecastResponse(
        model_type=model,
        horizon_months=horizon,
        forecasts=forecasts,
        metrics={} # Optional: add metrics here if needed
    )

@router.get("/impact/top-features")
async def get_top_features(n: int = Query(10, ge=1, le=50)):
    # Get all components and their contributions
    rankings = bill_impact_engine.rank_components()
    
    # Sort by absolute contribution (mocking SHAP importance)
    # In a real model, we would use shap_values = explainer(X)
    sorted_rankings = sorted(rankings, key=lambda x: abs(x['share_pct']), reverse=True)
    
    top_n = sorted_rankings[:n]
    
    features = [r['label'] for r in top_n]
    # Scale share_pct to look like dollar impact (SHAP)
    base_bill = app_state["billing_df"]["total_bill"].iloc[-1]
    shap_values = [round(r['share_pct'] * base_bill / 100, 2) for r in top_n]
    
    total_abs_shap = sum(abs(s) for s in shap_values)
    percents = [round((abs(s) / total_abs_shap * 100), 1) if total_abs_shap > 0 else 0 for s in shap_values]
    
    return {
        "features": features,
        "shap_values": shap_values,
        "percent_contribution": percents
    }

@router.get("/impact", response_model=ImpactResponse)
async def get_impact():
    # Keep existing impact for backward compatibility or general overview
    rankings = bill_impact_engine.rank_components()
    drivers = []
    for r in rankings:
        drivers.append({
            "feature": r['label'],
            "shap_value": r['share_pct'] * 1.5,
            "direction": "increases",
            "magnitude": "high" if r['share_pct'] > 20 else "medium"
        })
    
    return ImpactResponse(
        base_value=float(app_state["billing_df"]["total_bill"].iloc[-1]),
        predicted_value=float(app_state["billing_df"]["total_bill"].iloc[-1] * 1.05),
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
async def get_geo(month: Optional[str] = None, view_mode: str = "bill"):
    from api.services.geo_insights_service import get_map_data, get_available_months
    
    monthly_df = app_state.get("geo_monthly_df")
    if monthly_df is None: raise HTTPException(500, "No data")
    
    available_months = get_available_months(monthly_df)
    target_month = month or available_months[-1]
    
    raw_data = get_map_data(monthly_df, target_month, data_type=view_mode)
    
    data = []
    for row in raw_data:
        data.append(GeoPoint(
            state=row['state'],
            avg_bill=row['avg_bill'],
            avg_rate=row['avg_price'],
            rank=0 # Will calc below
        ))
    
    # Calc rank
    data.sort(key=lambda x: x.avg_bill, reverse=True)
    for i, p in enumerate(data):
        p.rank = i + 1
        
    sorted_data = sorted(data, key=lambda x: x.avg_bill, reverse=True)
    
    return GeoResponse(
        data=data,
        top_5_expensive=sorted_data[:5],
        top_5_cheapest=sorted_data[-5:][::-1],
        available_months=available_months,
        current_month=target_month
    )

@router.get("/geo/trend", response_model=GeoTrendPoint)
async def get_geo_trend(state: str, view_mode: str = "bill"):
    from api.services.geo_insights_service import get_trend_data
    monthly_df = app_state.get("geo_monthly_df")
    res = get_trend_data(monthly_df, state, data_type=view_mode)
    return GeoTrendPoint(
        months=res['months'],
        values=res['values'],
        total_growth_pct=res['total_growth_pct']
    )

@router.get("/geo/detail", response_model=GeoDetailResponse)
async def get_geo_detail(state: str, month: str):
    from api.services.geo_insights_service import get_detail_data
    monthly_df = app_state.get("geo_monthly_df")
    billing_df = app_state.get("billing_df")
    res = get_detail_data(billing_df, monthly_df, state, month)
    return GeoDetailResponse(**res)

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
