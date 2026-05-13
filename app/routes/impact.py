"""
POST /impact        — deterministic component contribution + sensitivity
GET  /contribution  — component contribution for a specific month
GET  /sensitivity   — sensitivity analysis (+/- pct% per component)
POST /simulate-bill — simulate a bill with user overrides
"""
import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
impact_bp = Blueprint("impact", __name__)


# ── /impact ───────────────────────────────────────────────────────────────────

@impact_bp.post("/impact")
def bill_impact_analysis():
    """
    Deterministic component contribution and sensitivity analysis.
    Uses the latest billing row as the reference record.
    """
    svc = current_app.extensions["svc"]
    if svc.impact_model is None:
        return jsonify({"error": "Impact model not loaded"}), 503
    if svc.billing_df is None:
        return jsonify({"error": "Billing data not loaded"}), 503

    body = request.get_json(silent=True) or {}

    try:
        top_n = int(body.get("top_n", 10))
        if not (1 <= top_n <= 30):
            return jsonify({"error": "top_n must be between 1 and 30"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "top_n must be an integer"}), 400

    try:
        row = svc.billing_df.iloc[-1].to_dict()
        result = svc.impact_model.get_analysis(row)

        if not result:
            return jsonify({"error": "Impact analysis returned empty (zero total bill)"}), 500

        # Slice top_n contributions
        contribs = result.get("contributions", {})
        sorted_contribs = sorted(
            contribs.items(), key=lambda x: abs(x[1]["value"]), reverse=True
        )
        top_drivers = [
            {
                "feature":      k,
                "shap_value":   round(v["value"], 4),
                "direction":    "increases" if v["value"] >= 0 else "decreases",
                "magnitude":    "high" if abs(v["value"]) > 50 else (
                                "medium" if abs(v["value"]) > 10 else "low"),
                "pct_of_total": v["percent"],
            }
            for k, v in sorted_contribs[:top_n]
        ]

        return jsonify({
            "total_bill":    result.get("total_bill"),
            "top_drivers":   top_drivers,
            "contributions": contribs,
            "sensitivity":   result.get("sensitivity", {}),
            "insights":      result.get("insights", []),
        })

    except Exception as exc:
        logger.exception("impact error")
        return jsonify({"error": f"Impact analysis error: {exc}"}), 500


# ── /contribution ─────────────────────────────────────────────────────────────

@impact_bp.get("/contribution")
def get_contribution():
    """Component contribution analysis for a specific month (by index)."""
    svc = current_app.extensions["svc"]
    if svc.billing_df is None:
        return jsonify({"error": "Billing data not loaded"}), 503

    try:
        month_index = int(request.args.get("month_index", -1))
        if not (-84 <= month_index <= -1):
            return jsonify({"error": "month_index must be between -84 and -1"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "month_index must be an integer"}), 400

    try:
        from shared.bill_analytics import compute_contributions, classify_components

        row = svc.billing_df.iloc[month_index]
        contribs = compute_contributions(row)
        date_str = str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"])

        return jsonify({
            "date":       date_str,
            "total_bill": round(float(row["total_bill"]), 2),
            "contributions": [
                {
                    "component":       c.component,
                    "label":           c.label,
                    "category":        c.category,
                    "driver":          c.driver,
                    "value":           c.value,
                    "pct_of_total":    c.pct_of_total,
                    "pct_of_subtotal": c.pct_of_subtotal,
                }
                for c in contribs
            ],
            "classification": classify_components(),
        })

    except Exception as exc:
        logger.exception("contribution error")
        return jsonify({"error": str(exc)}), 500


# ── /sensitivity ──────────────────────────────────────────────────────────────

@impact_bp.get("/sensitivity")
def get_sensitivity():
    """Sensitivity analysis — impact of ±pct% change per component."""
    svc = current_app.extensions["svc"]
    if svc.billing_df is None:
        return jsonify({"error": "Billing data not loaded"}), 503

    try:
        month_index = int(request.args.get("month_index", -1))
        pct = float(request.args.get("pct", 10.0))
        if not (-84 <= month_index <= -1):
            return jsonify({"error": "month_index must be between -84 and -1"}), 400
        if not (1.0 <= pct <= 50.0):
            return jsonify({"error": "pct must be between 1 and 50"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid query parameters"}), 400

    try:
        from shared.bill_analytics import (
            compute_contributions, run_sensitivity, generate_insights,
        )

        row = svc.billing_df.iloc[month_index]
        results = run_sensitivity(row, pct_changes=[-pct, pct])
        contribs = compute_contributions(row)
        insights = generate_insights(contribs, results, row)
        date_str = str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"])

        return jsonify({
            "date":       date_str,
            "base_total": round(float(row["total_bill"]), 2),
            "pct_tested": pct,
            "results": [
                {
                    "component":        r.component,
                    "label":            r.label,
                    "category":         r.category,
                    "pct_change":       r.pct_change,
                    "base_value":       r.base_value,
                    "delta":            r.delta,
                    "new_total":        r.new_total,
                    "total_delta":      r.total_delta,
                    "total_pct_change": r.total_pct_change,
                    "elasticity":       r.elasticity,
                }
                for r in results
            ],
            "insights": insights,
        })

    except Exception as exc:
        logger.exception("sensitivity error")
        return jsonify({"error": str(exc)}), 500


# ── /simulate-bill ────────────────────────────────────────────────────────────

@impact_bp.post("/simulate-bill")
def post_simulate_bill():
    """Simulate a bill with user-specified component overrides."""
    svc = current_app.extensions["svc"]
    if svc.billing_df is None:
        return jsonify({"error": "Billing data not loaded"}), 503

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "JSON body required"}), 400

    try:
        from shared.bill_analytics import simulate_bill

        row = svc.billing_df.iloc[-1]
        overrides = dict(body)
        usage = overrides.pop("usage_kwh", None)
        result = simulate_bill(row, overrides=overrides, usage_kwh=usage)
        return jsonify(result)

    except Exception as exc:
        logger.exception("simulate-bill error")
        return jsonify({"error": str(exc)}), 500
