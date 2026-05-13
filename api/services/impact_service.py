"""
Impact Service — wraps BillImpactModel and shared.bill_analytics
for /impact, /contribution, /sensitivity, /simulate-bill.
"""
import pandas as pd

from shared.bill_analytics import (
    compute_contributions,
    classify_components,
    run_sensitivity,
    generate_insights,
    simulate_bill,
)


def run_impact_analysis(model, billing: pd.DataFrame, top_n: int) -> dict:
    """
    Deterministic component contribution + sensitivity analysis
    using the BillImpactModel.get_analysis() API.
    """
    row = billing.iloc[-1].to_dict()
    result = model.get_analysis(row)

    if not result:
        raise ValueError("Impact analysis returned empty (zero total bill)")

    contribs = result.get("contributions", {})
    sorted_contribs = sorted(
        contribs.items(), key=lambda x: abs(x[1]["value"]), reverse=True
    )

    top_drivers = [
        {
            "feature": k,
            "shap_value": round(v["value"], 4),
            "direction": "increases" if v["value"] >= 0 else "decreases",
            "magnitude": (
                "high" if abs(v["value"]) > 50
                else ("medium" if abs(v["value"]) > 10 else "low")
            ),
            "pct_of_total": v["percent"],
        }
        for k, v in sorted_contribs[:top_n]
    ]

    return {
        "total_bill": result.get("total_bill"),
        "top_drivers": top_drivers,
        "contributions": contribs,
        "sensitivity": result.get("sensitivity", {}),
        "insights": result.get("insights", []),
        "category_impacts": {
            k: {"absolute": v["value"], "pct": v["percent"]}
            for k, v in contribs.items()
        },
        "model_metrics": {},
    }


def run_contribution(billing: pd.DataFrame, month_index: int) -> dict:
    """Component contribution analysis for a specific month."""
    row = billing.iloc[month_index]
    contribs = compute_contributions(row)
    date_str = str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"])

    return {
        "date": date_str,
        "total_bill": round(float(row["total_bill"]), 2),
        "contributions": [
            {
                "component": c.component,
                "label": c.label,
                "category": c.category,
                "driver": c.driver,
                "value": c.value,
                "pct_of_total": c.pct_of_total,
                "pct_of_subtotal": c.pct_of_subtotal,
            }
            for c in contribs
        ],
        "classification": classify_components(),
    }


def run_sensitivity_analysis(billing: pd.DataFrame, month_index: int, pct: float) -> dict:
    """Sensitivity analysis: impact of +/- pct% change per component."""
    row = billing.iloc[month_index]
    results = run_sensitivity(row, pct_changes=[-pct, pct])
    contribs = compute_contributions(row)
    insights = generate_insights(contribs, results, row)
    date_str = str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"])

    return {
        "date": date_str,
        "base_total": round(float(row["total_bill"]), 2),
        "pct_tested": pct,
        "results": [
            {
                "component": r.component,
                "label": r.label,
                "category": r.category,
                "pct_change": r.pct_change,
                "base_value": r.base_value,
                "delta": r.delta,
                "new_total": r.new_total,
                "total_delta": r.total_delta,
                "total_pct_change": r.total_pct_change,
                "elasticity": r.elasticity,
            }
            for r in results
        ],
        "insights": insights,
    }


def run_bill_simulation(billing: pd.DataFrame, overrides: dict) -> dict:
    """Simulate a bill with user-specified component overrides."""
    row = billing.iloc[-1]
    usage = overrides.pop("usage_kwh", None)
    return simulate_bill(row, overrides=overrides, usage_kwh=usage)
