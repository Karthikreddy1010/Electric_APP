"""
Forecast endpoint:
  POST /forecast — generate electricity cost forecast via trained ensemble.
"""
import logging

import pandas as pd
from flask import Blueprint, jsonify, request, current_app

forecast_bp = Blueprint("forecast", __name__)
logger = logging.getLogger(__name__)


@forecast_bp.route("/forecast", methods=["POST"])
def forecast_costs():
    """Generate electricity cost forecast."""
    ensemble = current_app.config.get("FORECAST_MODEL")
    if ensemble is None:
        return jsonify({"error": "Forecast model not loaded"}), 500

    body = request.get_json(silent=True) or {}

    # ── Manual validation (Flask has no built-in Pydantic) ───────
    months_ahead = body.get("months_ahead", 12)
    if not isinstance(months_ahead, int) or not (1 <= months_ahead <= 36):
        return jsonify({"error": "months_ahead must be an integer between 1 and 36"}), 422

    model_type = body.get("model_type", "ensemble")
    include_ci = body.get("include_ci", True)

    try:
        billing_df = current_app.config["BILLING_DF"]
        preds = ensemble.predict_ensemble(steps=months_ahead)

        # Build forecast dates
        last_date = pd.to_datetime(billing_df["date"].max())
        future_dates = pd.date_range(
            last_date + pd.DateOffset(months=1),
            periods=months_ahead,
            freq="MS",
        )

        forecasts = []
        for i in range(len(preds)):
            fp = {
                "month": future_dates[i].strftime("%Y-%m"),
                "forecast": round(float(preds["forecast_ensemble"].iloc[i]), 2),
                "lower": round(float(preds["lower"].iloc[i]), 2) if include_ci else None,
                "upper": round(float(preds["upper"].iloc[i]), 2) if include_ci else None,
            }
            forecasts.append(fp)

        metrics = {}
        if ensemble.sarima.fitted:
            metrics["aic"] = float(ensemble.sarima.fitted.aic)

        return jsonify({
            "model_type": model_type,
            "horizon_months": months_ahead,
            "forecasts": forecasts,
            "metrics": metrics,
        })

    except Exception as e:
        logger.exception("Forecast error")
        return jsonify({"error": f"Forecast error: {str(e)}"}), 500
