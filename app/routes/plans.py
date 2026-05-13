"""
Plan simulation endpoint:
  POST /plan-simulation — Monte Carlo comparison of electricity plans.
"""
import logging

from flask import Blueprint, jsonify, request, current_app

plans_bp = Blueprint("plans", __name__)
logger = logging.getLogger(__name__)


@plans_bp.route("/plan-simulation", methods=["POST"])
def plan_simulation():
    """Run Monte Carlo simulation comparing electricity plans."""
    plans_df = current_app.config.get("PLANS_DF")
    billing_df = current_app.config.get("BILLING_DF")
    if plans_df is None or billing_df is None:
        return jsonify({"error": "Data not loaded"}), 500

    body = request.get_json(silent=True) or {}

    # ── Manual validation ────────────────────────────────────────
    monthly_usage_kwh = body.get("monthly_usage_kwh", 750)
    usage_growth_pct = body.get("usage_growth_pct", 0.0)
    horizon_months = body.get("horizon_months", 12)
    n_simulations = body.get("n_simulations", 10000)

    errors = []
    if not (100 <= monthly_usage_kwh <= 5000):
        errors.append("monthly_usage_kwh must be between 100 and 5000")
    if not (-50 <= usage_growth_pct <= 50):
        errors.append("usage_growth_pct must be between -50 and 50")
    if not (1 <= horizon_months <= 36):
        errors.append("horizon_months must be between 1 and 36")
    if not (1000 <= n_simulations <= 100000):
        errors.append("n_simulations must be between 1000 and 100000")
    if errors:
        return jsonify({"error": "Validation Error", "details": errors}), 422

    try:
        from models.simulation_model import PlanSimulator

        sim = PlanSimulator(
            n_simulations=n_simulations,
            horizon_months=horizon_months,
        )

        historical_usage = billing_df["usage_kwh"].values * (1 + usage_growth_pct / 100)
        plans = plans_df.to_dict(orient="records")

        comparison = sim.compare_plans(plans, historical_usage)

        results = []
        for _, row in comparison.iterrows():
            results.append({
                "provider": row["provider"],
                "plan_type": row["plan_type"],
                "rate": row["rate"],
                "expected_annual_cost": round(row["expected_annual_cost"], 2),
                "median_annual_cost": round(row["median_annual_cost"], 2),
                "std_annual_cost": round(row["std_annual_cost"], 2),
                "p5_annual_cost": round(row["p5_annual_cost"], 2),
                "p95_annual_cost": round(row["p95_annual_cost"], 2),
                "risk_score": round(row["risk_score"], 1),
                "monthly_expected": row["monthly_expected"],
            })

        default_cost = comparison[comparison["provider"].str.contains("BGS|PSE&G")]
        default_annual = (
            default_cost["expected_annual_cost"].values[0]
            if len(default_cost) > 0
            else results[0]["expected_annual_cost"]
        )
        best = comparison.iloc[0]

        return jsonify({
            "comparison": results,
            "recommended": best["provider"],
            "savings_vs_default": round(default_annual - best["expected_annual_cost"], 2),
        })

    except Exception as e:
        logger.exception("Simulation error")
        return jsonify({"error": f"Simulation error: {str(e)}"}), 500
