from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.cache import cached
from api.schemas import (
    OverviewResponse, ForecastResponse, ImpactResponse, SimulateRequest, 
    SimulateResult, BenchmarkResponse, GeoResponse, PlanSimResponse,
    OverviewKPI, BillComponent, TrendResponse, GeoTrendPoint, GeoDetailResponse,
    GeoPoint, ForecastPoint, EIA861MSummary
)
from api.services.billing_service import build_breakdown, build_trends
from api.services.bill_impact_engine import bill_impact_engine, COMPONENT_TYPES
from typing import Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])

@router.get("/overview", response_model=OverviewResponse)
@cached(ttl=300)
async def get_overview():
    billing = app_state.get("billing_df")
    if billing is None:
        raise HTTPException(500, "Billing data not loaded")
    
    latest = billing.iloc[-1]
    prev = billing.iloc[-2] if len(billing) > 1 else latest
    
    # Lookup real tariff fixed customer charge from PSEG history if available
    fixed_charge = 8.24  # Standard PSE&G residential service customer charge
    pseg_df = app_state.get("pseg_history_df")
    if pseg_df is not None and not pseg_df.empty:
        try:
            fixed_charge = float(pseg_df["fixed_charge_per_month"].dropna().iloc[-1])
        except Exception:
            pass

    # 1. Compute Core Metrics (MANDATORY) using tariff + usage
    latest_kwh = float(latest["usage_kwh"])
    latest_bgs = float(latest["bgs_rate"])
    latest_dist = float(latest["distribution_rate"])
    latest_riders = float(latest.get("transmission_rate", 0)) + float(latest.get("sbc_rate", 0)) + float(latest.get("nug_rate", 0))
    
    # Calculate computed components
    supply_val = latest_kwh * latest_bgs
    dist_val = latest_kwh * latest_dist
    riders_val = latest_kwh * latest_riders
    fixed_val = fixed_charge
    
    comp_subtotal = supply_val + dist_val + riders_val + fixed_val
    tax_val = comp_subtotal * 0.06625  # NJ Utility Sales Tax
    latest_total_bill = comp_subtotal + tax_val
    latest_effective_rate = latest_total_bill / latest_kwh if latest_kwh > 0 else 0.0
    
    # Compute same metrics for previous month to get change indicators
    prev_kwh = float(prev["usage_kwh"])
    prev_bgs = float(prev["bgs_rate"])
    prev_dist = float(prev["distribution_rate"])
    prev_riders = float(prev.get("transmission_rate", 0)) + float(prev.get("sbc_rate", 0)) + float(prev.get("nug_rate", 0))
    prev_subtotal = prev_kwh * (prev_bgs + prev_dist + prev_riders) + fixed_charge
    prev_total_bill = prev_subtotal * 1.06625
    prev_effective_rate = prev_total_bill / prev_kwh if prev_kwh > 0 else 0.0
    
    bill_change = ((latest_total_bill - prev_total_bill) / prev_total_bill * 100) if prev_total_bill != 0 else 0.0
    usage_change = ((latest_kwh - prev_kwh) / prev_kwh * 100) if prev_kwh != 0 else 0.0
    rate_change = ((latest_effective_rate - prev_effective_rate) / prev_effective_rate * 100) if prev_effective_rate != 0 else 0.0
    
    # Simple forecast for next month (naive or from model if available)
    forecast_val = latest_total_bill  # Fallback
    if app_state.get("forecast_model"):
        try:
            f = app_state["forecast_model"].get_forecast(1)
            forecast_val = f[-1]['predicted_demand']
        except Exception:
            pass

    kpis = OverviewKPI(
        current_bill=round(latest_total_bill, 2),
        usage_kwh=round(latest_kwh, 1),
        effective_rate=round(latest_effective_rate, 5),
        forecast_next_month=round(forecast_val, 2),
        bill_change_pct=round(bill_change, 2),
        usage_change_pct=round(usage_change, 2),
        rate_change_pct=round(rate_change, 2)
    )

    # 2. Component Breakdown (FROM TARIFF MODEL)
    breakdown = [
        BillComponent(label="BGS Supply", value=round(supply_val, 2), percentage=round((supply_val / latest_total_bill * 100), 2) if latest_total_bill > 0 else 0),
        BillComponent(label="Distribution Charge", value=round(dist_val, 2), percentage=round((dist_val / latest_total_bill * 100), 2) if latest_total_bill > 0 else 0),
        BillComponent(label="Riders & Delivery", value=round(riders_val, 2), percentage=round((riders_val / latest_total_bill * 100), 2) if latest_total_bill > 0 else 0),
        BillComponent(label="Customer Charge", value=round(fixed_val, 2), percentage=round((fixed_val / latest_total_bill * 100), 2) if latest_total_bill > 0 else 0),
        BillComponent(label="Sales Tax", value=round(tax_val, 2), percentage=round((tax_val / latest_total_bill * 100), 2) if latest_total_bill > 0 else 0)
    ]
    breakdown = sorted(breakdown, key=lambda x: x.value, reverse=True)

    # 3. Add Benchmark Comparison
    benchmark_df = app_state.get("benchmark_df")
    vs_national = 0.0
    vs_national_label = "Your rate is on par with the national average"
    state_rank = 10
    state_percentile = 80.0
    national_avg = 0.1648  # Default national average rate ($/kWh)
    
    if benchmark_df is not None and not benchmark_df.empty:
        try:
            latest_year = int(benchmark_df["year"].max())
            year_df = benchmark_df[benchmark_df["year"] == latest_year]
            national_avg = float(year_df["avg_rate"].mean())
            vs_national = ((latest_effective_rate - national_avg) / national_avg) * 100
            
            nj_data = year_df[year_df["state"] == "NJ"]
            if not nj_data.empty:
                state_rank = int(nj_data.iloc[0].get("rank", 10))
                state_percentile = float(nj_data.iloc[0].get("percentile", 80.0))
                
            direction = "higher" if vs_national > 0 else "lower"
            vs_national_label = f"Your electricity rate is {abs(vs_national):.1f}% {direction} than the national average"
        except Exception:
            pass

    # 4. Add Trend Data (12/24/36 months calculated dynamically)
    trends_total_bills = []
    trends_usage = []
    trends_rates = []
    trends_months = []
    historical_breakdown = []
    
    hist_billing = billing.tail(36)
    for _, row in hist_billing.iterrows():
        month_label = row['date'].strftime("%Y-%m")
        k = float(row["usage_kwh"])
        bgs = float(row["bgs_rate"])
        dist = float(row["distribution_rate"])
        riders = float(row.get("transmission_rate", 0)) + float(row.get("sbc_rate", 0)) + float(row.get("nug_rate", 0))
        
        s_val = k * bgs
        d_val = k * dist
        r_val = k * riders
        
        sub = s_val + d_val + r_val + fixed_charge
        tax = sub * 0.06625
        t_bill = sub + tax
        
        trends_total_bills.append(round(t_bill, 2))
        trends_usage.append(round(k, 1))
        trends_rates.append(round(t_bill / k, 5) if k > 0 else 0.0)
        trends_months.append(month_label)
        
        historical_breakdown.append({
            "month": month_label,
            "BGS Supply": round(s_val, 2),
            "Distribution Charge": round(d_val, 2),
            "Riders & Delivery": round(r_val, 2),
            "Customer Charge": round(fixed_charge, 2),
            "Sales Tax": round(tax, 2)
        })
        
    yoy_changes = []
    mom_changes = []
    for i in range(len(trends_total_bills)):
        if i >= 12:
            prev_bill_yoy = trends_total_bills[i-12]
            yoy = (trends_total_bills[i] - prev_bill_yoy) / prev_bill_yoy * 100
            yoy_changes.append(round(yoy, 1))
        else:
            yoy_changes.append(None)
            
        if i >= 1:
            prev_bill_mom = trends_total_bills[i-1]
            mom = (trends_total_bills[i] - prev_bill_mom) / prev_bill_mom * 100
            mom_changes.append(round(mom, 1))
        else:
            mom_changes.append(None)
            
    trends = TrendResponse(
        months=trends_months,
        total_bills=trends_total_bills,
        usage=trends_usage,
        rates=trends_rates,
        yoy_changes=yoy_changes,
        mom_changes=mom_changes
    )

    # 5. Smart Insights & Alerts (Analytics Layer)
    insights = []
    
    # Cost driver insight
    costs_dict = {
        "Supply charges": supply_val,
        "Distribution costs": dist_val,
        "Riders & delivery costs": riders_val,
        "Fixed service charges": fixed_val
    }
    sorted_costs = sorted(costs_dict.items(), key=lambda x: x[1], reverse=True)
    primary_driver, primary_val = sorted_costs[0]
    primary_pct = (primary_val / latest_total_bill) * 100
    insights.append(f"{primary_driver} account for {primary_pct:.1f}% of your bill.")
    
    if dist_val > supply_val:
        insights.append("Distribution costs are the largest contributor to your bill.")
        
    # Trend insight
    trend_direction = "increased" if bill_change > 0 else "decreased"
    insights.append(f"Your bill {trend_direction} by {abs(bill_change):.1f}% compared to last month.")
    
    # Benchmark insight
    bench_direction = "above" if vs_national > 0 else "below"
    insights.append(f"Your rate is {abs(vs_national):.1f}% {bench_direction} the national average rate of ${national_avg:.4f}/kWh.")
    
    # Dynamic Alerts
    alerts = []
    usage_change = ((latest_kwh - prev_kwh) / prev_kwh * 100) if prev_kwh > 0 else 0.0
    if usage_change > 20.0:
        alerts.append(f"Your usage increased {usage_change:.1f}% compared to last month.")
    elif usage_change < -20.0:
        alerts.append(f"Excellent! Your usage decreased {abs(usage_change):.1f}% compared to last month.")
        
    latest_month = latest["date"].month
    if latest_month in [6, 7, 8]:
        alerts.append("Rates are higher this season due to summer peak pricing.")
    else:
        alerts.append("Rates are currently in the standard winter pricing tier.")

    # 4. EIA-861M monthly summary
    eia861m_summary = None
    eia861m_df = app_state.get("eia861m_df")
    if eia861m_df is not None and not eia861m_df.empty:
        try:
            totals = eia861m_df[eia861m_df["sector"] == "total"].copy()
            if not totals.empty:
                latest_period = totals["period"].max()
                latest_data = totals[totals["period"] == latest_period]
                if not latest_data.empty:
                    eia861m_summary = EIA861MSummary(
                        year=int(latest_data["year"].iloc[0]),
                        month=int(latest_data["month"].iloc[0]),
                        period=str(latest_period),
                        monthly_sales_mwh=float(latest_data["sales_mwh"].sum()),
                        monthly_revenue_k=float(latest_data["revenue_k_dollars"].sum()),
                        customer_count=int(latest_data["customers"].sum()),
                        avg_price_cents_kwh=round(float(latest_data["price_cents_kwh"].mean()), 4)
                    )
        except Exception as e_summary:
            logger.warning(f"Error computing eia861m_summary: {e_summary}")

    return OverviewResponse(
        kpis=kpis, 
        breakdown=breakdown, 
        historical_breakdown=historical_breakdown,
        trends=trends,
        vs_national_pct=round(vs_national, 2),
        vs_national_label=vs_national_label,
        state_rank=state_rank,
        state_percentile=state_percentile,
        insights=insights,
        alerts=alerts,
        eia861m_summary=eia861m_summary
    )



def compute_bill_analysis():
    """Single source of truth for UI, LLM, and PDF, backed by BillImpactModel."""
    from models.impact_model import BillImpactModel
    model = BillImpactModel()
    
    billing = app_state["billing_df"]
    latest_row = billing.iloc[-1].to_dict()
    prev_row = billing.iloc[-2].to_dict() if len(billing) > 1 else latest_row
    
    analysis = model.get_analysis(latest_row, prev_row)
    base_bill = analysis["total_bill"]
    
    # Map contributions to features
    all_features = []
    labels_map = {
        "customer": ("Customer Charge", "Fixed"),
        "distribution": ("Distribution Charge", "Infrastructure"),
        "transition": ("Transition Charges", "Regulatory"),
        "sbc": ("Societal Benefits Charge", "Policy"),
        "transmission": ("Transmission Charge", "Market"),
        "rider": ("Rider Charges", "Regulatory"),
        "bgs": ("BGS Supply", "Market"),
        "weather": ("Weather Impact", "External"),
        "behavioral_usage": ("Discretionary Usage", "Behavioral"),
        "nug": ("Non-Utility Generation Charge", "Regulatory"),
        "tax": ("Sales Tax", "Policy")
    }
    
    for short_key, data in analysis["contributions"].items():
        label, driver = labels_map.get(short_key, (short_key.capitalize(), "External"))
        all_features.append({
            "label": label,
            "shap_value": data["value"],
            "share_pct": data["percent"],
            "category": driver
        })
        
    # Sort features by absolute contribution descending
    all_features = sorted(all_features, key=lambda x: abs(x["shap_value"]), reverse=True)
    
    # Map sensitivity dictionary to the UI format
    sensitivity = []
    descriptions = {
        "Customer Charge": "Fixed monthly customer charge independent of usage changes.",
        "Distribution Charge": "Local distribution grid maintenance costs, weather-normalized.",
        "Transition Charges": "Stranded cost recoveries and policy transition adjustments.",
        "Societal Benefits Charge": "Funds state-mandated energy efficiency and assistance programs.",
        "Transmission Charge": "High-voltage transmission grid service cost share.",
        "Rider Charges": "Temporary regulatory tariff adjustments for utility costs.",
        "BGS Supply": "Basic Generation Service market price for wholesale supply.",
        "Weather Impact": "Attributed cooling/heating demand costs based on NOAA degree-day anomalies.",
        "Discretionary Usage": "Behavioral consumption changes unrelated to seasonal temperature anomalies.",
        "Non-Utility Generation Charge": "Historical independent power producer contract recovery.",
        "Sales Tax": "New Jersey state utility sales tax (6.625%) on all components."
    }
    
    for short_key, impacts in analysis["sensitivity"].items():
        label, driver = labels_map.get(short_key, (short_key.capitalize(), "External"))
        elasticity = abs(impacts.get("+10%", 0)) / (base_bill * 0.10) if base_bill else 0.0
        
        sensitivity.append({
            "component": label,
            "elasticity": round(elasticity, 4),
            "impact_type": "high" if elasticity > 0.3 else ("medium" if elasticity > 0.1 else "low"),
            "driver": driver,
            "reasoning": descriptions.get(label, "Variable billing component sensitivity.")
        })
        
    # Sort sensitivity by elasticity descending
    sensitivity = sorted(sensitivity, key=lambda x: x["elasticity"], reverse=True)
    
    # Format date cleanly
    current_m = billing["date"].iloc[-1]
    if hasattr(current_m, "strftime"):
        current_m = current_m.strftime("%Y-%m")
    else:
        current_m = str(current_m)[:7]
        
    return {
        "base_bill": base_bill,
        "all_features": all_features,
        "sensitivity": sensitivity,
        "current_month": current_m,
        "insights": analysis["insights"],
        "latest_row": {
            "usage_kwh": float(latest_row.get("usage_kwh", 750)),
            "base_bill": float(latest_row.get("total_bill", base_bill)),
            "bgs_rate": float(latest_row.get("bgs_rate", 0.11)),
            "distribution_rate": float(latest_row.get("distribution_rate", 0.04)),
            "transmission_rate": float(latest_row.get("transmission_rate", 0.02)),
            "sbc_rate": float(latest_row.get("sbc_rate", 0.008)),
            "nug_rate": float(latest_row.get("nug_rate", 0.002)),
            "customer_charge": 8.24,
            "cdd": float(analysis.get("weather_cdd", 0.0)),
            "hdd": float(analysis.get("weather_hdd", 0.0))
        },
        "alpha": analysis.get("alpha", 0.85),
        "beta": analysis.get("beta", 0.45),
        "base_usage": analysis.get("base_usage", 450.0),
        "confidence": analysis.get("confidence", "High")
    }

@router.get("/impact/top-features")
@cached(ttl=300)
async def get_top_features(n: int = Query(10, ge=1, le=50)):
    analysis = compute_bill_analysis()
    top_n = analysis["all_features"][:n]
    
    return {
        "features": [f["label"] for f in top_n],
        "shap_values": [f["shap_value"] for f in top_n],
        "percent_contribution": [f["share_pct"] for f in top_n]
    }

@router.get("/impact/full-analysis")
@cached(ttl=300)
async def get_full_analysis():
    return compute_bill_analysis()

def _get_report_data_and_prompt():
    analysis = compute_bill_analysis()
    
    # Deterministic High-Fidelity Fallback
    top_driver = analysis['all_features'][0]
    total_bill = analysis['base_bill']
    month = analysis['current_month']
    share = top_driver['share_pct']
    
    weather_insights = "\n".join(f"    - {ins}" for ins in analysis["insights"] if "demand" in ins.lower() or "cooling" in ins.lower() or "heating" in ins.lower() or "weather" in ins.lower() or "non-weather" in ins.lower())
    
    fallback_text = f"""
    Your electricity bill for {month} is mainly driven by {top_driver['label']} costs, which account for about {share:.1f}% of the total (${abs(top_driver['shap_value']):.2f}). These costs depend on market electricity prices and are not directly controllable.
    
    Other utility fees and delivery charges constitute the remaining portion of your cost structure.
    
    Seasonal Cost and Weather Drivers:
{weather_insights if weather_insights else "    - Standard baseline seasonal temperatures."}
    
    To reduce your overall bill:
    1. Focus on lowering overall usage (kWh), as all delivery charges directly scale with consumption.
    2. Reduce peak-time consumption when grid congestion is highest.
    3. Monitor and manage high-load appliances.
    """
    
    prompt = f"""
    You are an electricity billing expert.

    Explain the user's bill using:
    - total bill: ${total_bill:.2f}
    - component breakdown: {analysis}

    Focus on:
    1. Which components contribute the most (such as {top_driver['label']} at {share:.1f}%)
    2. What is controllable vs uncontrollable
    3. Why the bill changed
    4. What actions the user can take
    5. Highlight seasonal weather demand (cooling/heating loads) vs behavioral usage

    Do NOT mention SHAP, models, or AI.
    Use simple, practical language.
    """
    return prompt, fallback_text, month, analysis

@router.post("/report/generate")
async def generate_report():
    from fastapi.responses import StreamingResponse
    import ollama
    import time
    import asyncio
    import socket
    
    prompt, fallback_text, _, _ = _get_report_data_and_prompt()
    
    async def generate_stream():
        try:
            # Step 1: Rapid socket check to see if Ollama is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            res = sock.connect_ex(('127.0.0.1', 11434))
            sock.close()
            if res != 0:
                raise RuntimeError("Ollama daemon offline")

            client = ollama.AsyncClient(timeout=1.5)
            response = await client.chat(
                model="qwen3:4b",
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.2,
                    "num_predict": 250
                },
                stream=True
            )
            
            start_time = time.time()
            # Step 2: Retrieve streamed tokens with a strict timeout to prevent hangs
            while True:
                try:
                    chunk = await asyncio.wait_for(response.__anext__(), timeout=1.0)
                    if 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']
                    if time.time() - start_time > 10.0:
                        yield "\n\n[Generation stopped: Time limit exceeded]"
                        break
                except StopAsyncIteration:
                    break
        except Exception as e:
            # Transparently return fallback if AI is offline, slow, or times out
            logger.warning(f"Ollama streaming report generation failed: {e or type(e).__name__}. Using deterministic fallback.")
            yield f"[AI Engine Offline - Deterministic Summary Generated]\n{fallback_text}"
            
    return StreamingResponse(generate_stream(), media_type="text/plain")

@router.post("/report/pdf")
async def generate_pdf():
    from reportlab.lib.pagesizes import LETTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    import io
    from fastapi.responses import StreamingResponse
    import ollama
    import asyncio
    
    prompt, fallback_text, month, analysis = _get_report_data_and_prompt()
    
    try:
        # Step 1: Rapid socket check to see if Ollama is listening
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        res = sock.connect_ex(('127.0.0.1', 11434))
        sock.close()
        if res != 0:
            raise RuntimeError("Ollama daemon offline")

        # Non-streaming for PDF
        client = ollama.AsyncClient(timeout=1.5)
        
        async def fetch_chat():
            return await client.chat(
                model="qwen3:4b",
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.2,
                    "num_predict": 250
                }
            )
        
        # Enforce 1.5s strict timeout
        response = await asyncio.wait_for(fetch_chat(), timeout=1.5)
        text = response['message']['content']
    except Exception as e:
        logger.warning(f"Ollama PDF report generation failed: {e or type(e).__name__}. Using deterministic fallback.")
        text = f"[AI Engine Offline - Deterministic Summary Generated]\n{fallback_text}"
    
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
        headers={"Content-Disposition": f"attachment; filename=bill_report_{month}.pdf"}
    )

@router.post("/simulate", response_model=SimulateResult)
async def simulate_impact(req: SimulateRequest):
    sim = bill_impact_engine.what_if_simulation(req.modifications, req.kwh)
    
    # Formula construction
    # New Bill = Base Bill × (1 + % Change × Elasticity)
    # We'll simplify for the UI display
    comp_labels = []
    for k, v in req.modifications.items():
        key = k
        if key not in COMPONENT_TYPES:
            if f"{key}_rate" in COMPONENT_TYPES:
                key = f"{key}_rate"
            elif f"{key}_charge" in COMPONENT_TYPES:
                key = f"{key}_charge"
        label = COMPONENT_TYPES[key]['label'] if key in COMPONENT_TYPES else k.upper()
        comp_labels.append(f"{label} ({v}%)")
        
    formula = "New Bill = Base Bill × (1 + Σ(% Change_i × Weight_i) × Elasticity)"
    
    return SimulateResult(
        old_bill=sim['base_bill'],
        new_bill=sim['new_bill'],
        delta_abs=sim['total_impact'],
        delta_pct=round((sim['total_impact'] / sim['base_bill'] * 100), 2) if sim['base_bill'] > 0 else 0,
        formula=formula,
        explanation=f"If {', '.join(comp_labels)} change, your bill increases/decreases by approximately {sim['total_impact']} based on historical elasticity."
    )




@router.get("/geo", response_model=GeoResponse)
@cached(ttl=300)
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


@router.get("/plans", response_model=PlanSimResponse)
@cached(ttl=300)
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
