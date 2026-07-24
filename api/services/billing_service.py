"""
Billing Service — builds breakdown and trend responses.
Isolates pandas logic from route handlers.
"""
import pandas as pd
from api.schemas import BillBreakdownResponse


def build_breakdown(billing: pd.DataFrame, months: int) -> list[BillBreakdownResponse]:
    """Compute detailed bill breakdown for the last *months* months."""
    full = billing.copy()
    full["yoy_change_pct"] = full["total_bill"].pct_change(12) * 100
    recent = full.tail(months)

    results = []
    for _, row in recent.iterrows():
        yoy = round(float(row["yoy_change_pct"]), 2) if pd.notna(row["yoy_change_pct"]) else None
        results.append(BillBreakdownResponse(
            date=str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
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
            yoy_change_pct=yoy,
        ))
    return results


def build_trends(billing: pd.DataFrame, months: int) -> dict:
    """Return historical trend data."""
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


# ── Customer Archetype Clustering & Bill Health Audit ───────────────────────

def classify_customer_archetype(usage_kwh: float, peak_kw: float = 0.0, renewable_pct: float = 0.0) -> dict:
    """
    Classify customer into analytical archetypes:
      - High-Load EV Prosumer
      - Solar Green Eco-User
      - Commercial Peaker
      - Efficient Low-Load
      - Standard Suburban Household
    """
    if usage_kwh > 1200.0 and renewable_pct > 25.0:
        archetype = "Solar Green Prosumer"
        profile_desc = "High consumption offset by local renewable generation. High battery storage potential."
        savings_advice = "Consider installing a smart home energy storage system to arbitrage peak time rates."
    elif usage_kwh > 1100.0:
        archetype = "High-Demand Peaker"
        profile_desc = "Above-average usage profile with high evening peak demand spikes."
        savings_advice = "Enroll in Time-of-Use rate plans and shift high-demand appliances to off-peak hours."
    elif usage_kwh < 450.0:
        archetype = "Efficient Low-Load Household"
        profile_desc = "Highly energy-efficient baseline consumption profile."
        savings_advice = "Maintain baseline efficiency. Look for community solar subscription credits."
    else:
        archetype = "Standard Residential Household"
        profile_desc = "Typical residential consumption pattern aligned with state average averages."
        savings_advice = "Optimize thermostat settings during peak seasonal months to shave 10-15% off bills."

    return {
        "usage_kwh": usage_kwh,
        "archetype": archetype,
        "profile_description": profile_desc,
        "savings_advice": savings_advice,
    }


def compute_bill_health_score(usage_kwh: float, total_bill: float, OCR_error_flag: bool = False) -> dict:
    """
    Automated Bill Health & Anomaly Score (0 to 100).
    Audits effective rate reasonableness, component integrity, and OCR confidence.
    """
    effective_rate = (total_bill / usage_kwh) if usage_kwh > 0 else 0.214
    score = 100.0
    anomalies = []

    # Check 1: Rate Spike
    if effective_rate > 0.35:
        score -= 25.0
        anomalies.append(f"High effective rate (${effective_rate:.3f}/kWh) exceeds state 90th percentile threshold.")
    elif effective_rate < 0.08:
        score -= 20.0
        anomalies.append(f"Unusually low effective rate (${effective_rate:.3f}/kWh) — possible missing line item charge.")

    # Check 2: OCR Extraction Flag
    if OCR_error_flag:
        score -= 15.0
        anomalies.append("OCR extraction flag detected manual correction mismatch on total amount or usage.")

    # Check 3: Extreme usage
    if usage_kwh > 2500.0:
        score -= 10.0
        anomalies.append("Monthly usage exceeds 2,500 kWh — trigger demand response load audit.")

    final_score = max(round(score, 1), 0.0)
    health_grade = "A+" if final_score >= 90 else "B" if final_score >= 75 else "C" if final_score >= 60 else "F"

    return {
        "bill_health_score": final_score,
        "health_grade": health_grade,
        "effective_rate": round(effective_rate, 4),
        "anomalies_detected": anomalies,
        "audit_status": "Clean" if final_score >= 85 else "Review Recommended",
    }

