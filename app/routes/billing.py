"""
GET  /bill-breakdown
GET  /trends
"""
import logging

import pandas as pd
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
billing_bp = Blueprint("billing", __name__)


# ── /bill-breakdown ───────────────────────────────────────────────────────────

@billing_bp.get("/bill-breakdown")
def bill_breakdown():
    """Get detailed bill component breakdown for recent months."""
    svc = current_app.extensions["svc"]
    if svc.billing_df is None:
        return jsonify({"error": "Data not loaded"}), 503

    try:
        months = int(request.args.get("months", 12))
        if not (1 <= months <= 84):
            return jsonify({"error": "months must be between 1 and 84"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "months must be an integer"}), 400

    billing = svc.billing_df
    full = billing.copy()
    full["yoy_change_pct"] = full["total_bill"].pct_change(12) * 100
    recent = full.tail(months)

    results = []
    for _, row in recent.iterrows():
        yoy = round(float(row["yoy_change_pct"]), 2) if pd.notna(row["yoy_change_pct"]) else None
        results.append({
            "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
            "total_bill": round(float(row["total_bill"]), 2),
            "components": {
                "bgs":          round(float(row["bgs_cost"]), 2),
                "transmission": round(float(row["transmission_cost"]), 2),
                "distribution": round(float(row["distribution_cost"]), 2),
                "sbc":          round(float(row["sbc_cost"]), 2),
                "nug":          round(float(row["nug_cost"]), 2),
                "dr_credit":    round(float(row["dr_credit"]), 2),
                "tax":          round(float(row["sales_tax"]), 2),
            },
            "rates": {
                "bgs":          round(float(row["bgs_rate"]), 5),
                "transmission": round(float(row["transmission_rate"]), 5),
                "distribution": round(float(row["distribution_rate"]), 5),
                "sbc":          round(float(row["sbc_rate"]), 5),
                "nug":          round(float(row["nug_rate"]), 5),
            },
            "usage_kwh":      round(float(row["usage_kwh"]), 1),
            "effective_rate":  round(float(row["total_bill"]) / float(row["usage_kwh"]), 5),
            "yoy_change_pct": yoy,
        })
    return jsonify(results)


# ── /trends ───────────────────────────────────────────────────────────────────

@billing_bp.get("/trends")
def get_trends():
    """Get historical trend data."""
    svc = current_app.extensions["svc"]
    if svc.billing_df is None:
        return jsonify({"error": "Data not loaded"}), 503

    try:
        months = int(request.args.get("months", 36))
        if not (6 <= months <= 84):
            return jsonify({"error": "months must be between 6 and 84"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "months must be an integer"}), 400

    df = svc.billing_df.tail(months).copy()
    df["effective_rate"] = df["total_bill"] / df["usage_kwh"]
    df["yoy_change"] = df["total_bill"].pct_change(12) * 100

    return jsonify({
        "months":      df["date"].dt.strftime("%Y-%m").tolist(),
        "total_bills": df["total_bill"].round(2).tolist(),
        "usage":       df["usage_kwh"].round(1).tolist(),
        "rates":       df["effective_rate"].round(5).tolist(),
        "yoy_changes": [round(x, 1) if pd.notna(x) else None for x in df["yoy_change"]],
    })
