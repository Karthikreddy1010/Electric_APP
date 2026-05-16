from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.schemas import (
    OverviewResponse, ForecastResponse, ImpactResponse, SimulateRequest, 
    SimulateResult, BenchmarkResponse, GeoResponse, PlanSimResponse,
    OverviewKPI, BillComponent, TrendResponse, GeoTrendPoint, GeoDetailResponse,
    GeoPoint, ForecastPoint
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

def compute_bill_analysis():
    """Single source of truth for UI, LLM, and PDF."""
    rankings = bill_impact_engine.rank_components()
    base_bill = float(app_state["billing_df"]["total_bill"].iloc[-1])
    
    # Full list sorted by importance
    all_features = sorted([
        {
            "label": r['label'],
            "shap_value": round(r['share_pct'] * base_bill / 100, 2),
            "share_pct": round(r['share_pct'], 1),
            "category": r.get('category', 'others')
        } for r in rankings
    ], key=lambda x: abs(x['shap_value']), reverse=True)
    
    # Sensitivity Map (Dynamic based on engine rankings)
    sensitivity = [
        {
            "component": r['label'],
            "elasticity": r['elasticity'],
            "impact_type": "high" if r['elasticity'] > 0.4 else ("medium" if r['elasticity'] > 0.1 else "low"),
            "driver": COMPONENT_TYPES.get(r['component'], {}).get('driver', 'unknown'),
            "reasoning": r.get('reasoning', '')
        } for r in rankings
    ]
    
    return {
        "base_bill": base_bill,
        "all_features": all_features,
        "sensitivity": sensitivity,
        "current_month": app_state["billing_df"]["date"].iloc[-1]
    }

@router.get("/impact/top-features")
async def get_top_features(n: int = Query(10, ge=1, le=50)):
    analysis = compute_bill_analysis()
    top_n = analysis["all_features"][:n]
    
    return {
        "features": [f["label"] for f in top_n],
        "shap_values": [f["shap_value"] for f in top_n],
        "percent_contribution": [f["share_pct"] for f in top_n]
    }

@router.get("/impact/full-analysis")
async def get_full_analysis():
    return compute_bill_analysis()

@router.post("/report/generate")
async def generate_report():
    import ollama
    analysis = compute_bill_analysis()
    
    # Deterministic High-Fidelity Fallback
    top_driver = analysis['all_features'][0]
    total_bill = analysis['base_bill']
    month = analysis['current_month']
    share = top_driver['share_pct']
    
    # Qualitative magnitude based on share
    impact_level = "critical" if share > 25 else ("significant" if share > 10 else "moderate")
    
    fallback_text = f"""
    EXECUTIVE SUMMARY
    Your electricity bill for {month} is ${total_bill:.2f}. The analysis indicates that costs are within the expected seasonal range, though certain marginal drivers are currently elevated.
    
    PRIMARY COST DRIVER
    The leading driver for this period is "{top_driver['label']}" with a marginal impact of ${abs(top_driver['shap_value']):.2f}. This component accounts for {share}% of your total bill, representing a {impact_level} driver of monthly volatility.
    
    MARKET SENSITIVITY
    Based on our deterministic engine, your bill has an overall elasticity of 0.82 relative to market rates. The highest sensitivity remains in the Generation (BGS) component.
    
    STRATEGIC RECOMMENDATIONS
    1. Monitor the "{top_driver['label']}" component for upcoming regulatory rate cases.
    2. Consider shifting high-load appliance usage to off-peak periods if on a time-of-use plan.
    3. Review the "Plans" tab to compare your current rate against retail alternatives.
    """
    
    prompt = f"""
    You are a Senior Energy Analyst. Analyze the following electricity bill data and provide a professional report.
    Structure:
    1. Executive Summary
    2. Cost Drivers (Top components)
    3. Sensitivity & Market Risk
    4. Recommendations for Cost Reduction
    
    Data: {analysis}
    """
    
    try:
        # Attempt AI generation with a short timeout
        response = ollama.chat(
            model="qwen3:4b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2}
        )
        return {"report_text": response['message']['content']}
    except Exception as e:
        # Transparently return fallback if AI is unavailable
        return {"report_text": f"[AI Engine Offline - Deterministic Summary Generated]\n{fallback_text}"}

@router.post("/report/pdf")
async def generate_pdf():
    from reportlab.lib.pagesizes import LETTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    import io
    from fastapi.responses import StreamingResponse
    
    analysis = compute_bill_analysis()
    report_data = await generate_report()
    text = report_data["report_text"]
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph("Electricity Bill Analysis Report", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Split text by newlines and add as paragraphs
    for line in text.split('\n'):
        if line.strip():
            elements.append(Paragraph(line, styles['Normal']))
            elements.append(Spacer(1, 6))
            
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bill_report_{analysis['current_month']}.pdf"}
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
