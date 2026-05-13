"""
Impact analysis endpoint:
  POST /impact — bill impact driver analysis using the BillImpactModel.

The existing impact_model.py has two interfaces:
  1. model.train() / model.explain() / model.get_component_impact() — XGBoost + SHAP
     (only works if the model can actually be trained on the feature matrix)
  2. model.get_analysis(row) — deterministic contribution/sensitivity (always works)

This route tries the SHAP path first (matching the FastAPI endpoint contract).
If the model wasn't trained (no .explain method), it falls back to get_analysis().
"""
import logging

from flask import Blueprint, jsonify, request, current_app

impact_bp = Blueprint("impact", __name__)
logger = logging.getLogger(__name__)


@impact_bp.route("/impact", methods=["POST"])
def bill_impact_analysis():
    """Analyze drivers of electricity bill changes."""
    model = current_app.config.get("IMPACT_MODEL")
    df = current_app.config.get("FEATURE_MATRIX")
    feature_cols = current_app.config.get("FEATURE_COLS")

    body = request.get_json(silent=True) or {}
    top_n = body.get("top_n", 10)
    if not isinstance(top_n, int) or not (1 <= top_n <= 30):
        return jsonify({"error": "top_n must be an integer between 1 and 30"}), 422

    # ── Path A: SHAP-based (if model was trained successfully) ───
    if model is not None and hasattr(model, "explain") and df is not None:
        try:
            explanation = model.explain(df[feature_cols])
            category_impacts = model.get_component_impact(df[feature_cols])

            drivers = []
            for item in explanation["latest_breakdown"][:top_n]:
                sv = item["shap_value"]
                drivers.append({
                    "feature": item["feature"],
                    "shap_value": round(sv, 4),
                    "direction": "increases" if sv > 0 else "decreases",
                    "magnitude": "high" if abs(sv) > 5 else ("medium" if abs(sv) > 1 else "low"),
                })

            return jsonify({
                "base_value": round(explanation["base_value"], 2),
                "predicted_value": round(explanation["predicted_value"], 2),
                "top_drivers": drivers,
                "category_impacts": category_impacts,
                "model_metrics": model.metrics,
            })
        except Exception as e:
            logger.warning(f"SHAP path failed, falling back to deterministic: {e}")

    # ── Path B: Deterministic fallback via get_analysis() ────────
    billing = current_app.config.get("BILLING_DF")
    if billing is None:
        return jsonify({"error": "Data not loaded"}), 500

    try:
        from models.impact_model import BillImpactModel

        impact = BillImpactModel()
        row = billing.iloc[-1]
        analysis = impact.get_analysis(dict(row))

        if not analysis:
            return jsonify({"error": "Impact analysis returned empty (zero total bill)"}), 500

        # Reshape to match the FastAPI /impact response contract
        contributions = analysis.get("contributions", {})
        sensitivity = analysis.get("sensitivity", {})

        drivers = []
        sorted_contribs = sorted(
            contributions.items(), key=lambda kv: abs(kv[1]["value"]), reverse=True
        )
        for key, data in sorted_contribs[:top_n]:
            drivers.append({
                "feature": key,
                "shap_value": round(data["value"], 4),
                "direction": "increases" if data["value"] > 0 else "decreases",
                "magnitude": "high" if abs(data["value"]) > 30 else (
                    "medium" if abs(data["value"]) > 10 else "low"
                ),
            })

        # Build category breakdown
        category_impacts = {}
        for key, data in contributions.items():
            category_impacts[key] = {
                "absolute": data["value"],
                "pct": data["percent"],
            }

        return jsonify({
            "base_value": 0.0,
            "predicted_value": analysis.get("total_bill", 0.0),
            "top_drivers": drivers,
            "category_impacts": category_impacts,
            "model_metrics": {},
            "sensitivity": sensitivity,
            "insights": analysis.get("insights", []),
        })

    except Exception as e:
        logger.exception("Impact analysis error")
        return jsonify({"error": f"Impact analysis error: {str(e)}"}), 500
