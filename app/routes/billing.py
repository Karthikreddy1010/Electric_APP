"""
Billing endpoints:
  GET /bill-breakdown  — detailed component breakdown for recent months
  GET /trends          — historical trend data
  GET /contribution    — component contribution analysis for a month
  GET /sensitivity     — sensitivity analysis (+/- pct change per component)
  POST /simulate-bill  — simulate a bill with overrides
"""
import logging

import pandas as pd
from flask import Blueprint, jsonify, request, current_app

from app.services.validators import validate_int_param, validate_float_param

billing_bp = Blueprint("billing", __name__)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
#  GET /bill-breakdown
# ─────────────────────────────────────────────────────

@billing_bp.route("/bill-breakdown", methods=["GET"])
def bill_breakdown():
    """Get detailed bill component breakdown for recent months."""
    billing = current_app.config.get("BILLING_DF")
    if billing is None:
        return jsonify({"error": "Data not loaded"}), 500

    months = validate_int_param("months", default=12, min_val=1, max_val=84)

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
                "bgs": round(float(row["bgs_cost"]), 2),
                "transmission": round(float(row["transmission_cost"]), 2),
                "distribution": round(float(row["distribution_cost"]), 2),
                "sbc": round(float(row["sbc_cost"]), 2),
                "nug": round(float(row["nug_cost"]), 2),
                "dr_credit": round(float(row["dr_credit"]), 2),
                "tax": round(float(row["sales_tax"]), 2),
            },
            "rates": {
                "bgs": round(float(row["bgs_rate"]), 5),
                "transmission": round(float(row["transmission_rate"]), 5),
                "distribution": round(float(row["distribution_rate"]), 5),
                "sbc": round(float(row["sbc_rate"]), 5),
                "nug": round(float(row["nug_rate"]), 5),
            },
            "usage_kwh": round(float(row["usage_kwh"]), 1),
            "effective_rate": round(float(row["total_bill"]) / float(row["usage_kwh"]), 5),
            "yoy_change_pct": yoy,
        })
    return jsonify(results)


# ─────────────────────────────────────────────────────
#  GET /trends
# ─────────────────────────────────────────────────────

@billing_bp.route("/trends", methods=["GET"])
def get_trends():
    """Get historical trend data."""
    billing = current_app.config.get("BILLING_DF")
    if billing is None:
        return jsonify({"error": "Data not loaded"}), 500

    months = validate_int_param("months", default=36, min_val=6, max_val=84)

    df = billing.tail(months).copy()
    df["effective_rate"] = df["total_bill"] / df["usage_kwh"]
    df["yoy_change"] = df["total_bill"].pct_change(12) * 100

    return jsonify({
        "months": df["date"].dt.strftime("%Y-%m").tolist(),
        "total_bills": df["total_bill"].round(2).tolist(),
        "usage": df["usage_kwh"].round(1).tolist(),
        "rates": df["effective_rate"].round(5).tolist(),
        "yoy_changes": [round(x, 1) if pd.notna(x) else None for x in df["yoy_change"]],
    })


# ─────────────────────────────────────────────────────
#  GET /contribution
# ─────────────────────────────────────────────────────

@billing_bp.route("/contribution", methods=["GET"])
def get_contribution():
    """Component contribution analysis for a specific month."""
    billing = current_app.config.get("BILLING_DF")
    if billing is None:
        return jsonify({"error": "Data not loaded"}), 500

    from shared.bill_analytics import compute_contributions, classify_components

    month_index = validate_int_param("month_index", default=-1, min_val=-84, max_val=-1)
    row = billing.iloc[month_index]
    contribs = compute_contributions(row)

    return jsonify({
        "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
        "total_bill": round(float(row["total_bill"]), 2),
        "contributions": [
            {
                "component": c.component, "label": c.label, "category": c.category,
                "driver": c.driver, "value": c.value,
                "pct_of_total": c.pct_of_total, "pct_of_subtotal": c.pct_of_subtotal,
            }
            for c in contribs
        ],
        "classification": classify_components(),
    })


# ─────────────────────────────────────────────────────
#  GET /sensitivity
# ─────────────────────────────────────────────────────

@billing_bp.route("/sensitivity", methods=["GET"])
def get_sensitivity():
    """Sensitivity analysis: impact of +/- pct% change per component."""
    billing = current_app.config.get("BILLING_DF")
    if billing is None:
        return jsonify({"error": "Data not loaded"}), 500

    from shared.bill_analytics import (
        compute_contributions, run_sensitivity, generate_insights,
    )

    month_index = validate_int_param("month_index", default=-1, min_val=-84, max_val=-1)
    pct = validate_float_param("pct", default=10.0, min_val=1, max_val=50)

    row = billing.iloc[month_index]
    results = run_sensitivity(row, pct_changes=[-pct, pct])
    contribs = compute_contributions(row)
    insights = generate_insights(contribs, results, row)

    return jsonify({
        "date": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
        "base_total": round(float(row["total_bill"]), 2),
        "pct_tested": pct,
        "results": [
            {
                "component": r.component, "label": r.label, "category": r.category,
                "pct_change": r.pct_change, "base_value": r.base_value,
                "delta": r.delta, "new_total": r.new_total,
                "total_delta": r.total_delta, "total_pct_change": r.total_pct_change,
                "elasticity": r.elasticity,
            }
            for r in results
        ],
        "insights": insights,
    })


# ─────────────────────────────────────────────────────
#  POST /simulate-bill
# ─────────────────────────────────────────────────────

@billing_bp.route("/simulate-bill", methods=["POST"])
def post_simulate_bill():
    """Simulate a bill with user-specified component overrides."""
    billing = current_app.config.get("BILLING_DF")
    if billing is None:
        return jsonify({"error": "Data not loaded"}), 500

    from shared.bill_analytics import simulate_bill

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    overrides = dict(body)
    row = billing.iloc[-1]
    usage = overrides.pop("usage_kwh", None)
    result = simulate_bill(row, overrides=overrides, usage_kwh=usage)
    return jsonify(result)
