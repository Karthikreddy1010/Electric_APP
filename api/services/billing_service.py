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
