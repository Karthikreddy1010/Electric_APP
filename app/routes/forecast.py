"""
POST /forecast — generate electricity cost forecast via trained ensemble.
"""
import logging

import pandas as pd
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
forecast_bp = Blueprint("forecast", __name__)


@forecast_bp.post("/forecast")
def forecast_costs():
    """Generate electricity cost forecast."""
    svc = current_app.extensions["svc"]
    if svc.forecast_model is None:
        return jsonify({"error": "Forecast model not loaded"}), 503
    if svc.billing_df is None:
        return jsonify({"error": "Billing data not loaded"}), 503

    body = request.get_json(silent=True) or {}

    # ── Validate ─────────────────────────────────────────────────────────────
    try:
        months_ahead = int(body.get("months_ahead", 12))
        if not (1 <= months_ahead <= 36):
            return jsonify({"error": "months_ahead must be between 1 and 36"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "months_ahead must be an integer"}), 400

    model_type = body.get("model_type", "ensemble")
    include_ci = body.get("include_ci", True)

    try:
        ensemble = svc.forecast_model
        preds = ensemble.predict_ensemble(steps=months_ahead)

        last_date = pd.to_datetime(svc.billing_df["date"].max())
        future_dates = pd.date_range(
            last_date + pd.DateOffset(months=1),
            periods=months_ahead,
            freq="MS",
        )

        forecasts = []
        for i in range(len(preds)):
            forecasts.append({
                "month":    future_dates[i].strftime("%Y-%m"),
                "forecast": round(float(preds["forecast_ensemble"].iloc[i]), 2),
                "lower":    round(float(preds["lower"].iloc[i]), 2) if include_ci else None,
                "upper":    round(float(preds["upper"].iloc[i]), 2) if include_ci else None,
            })

        metrics = {}
        if ensemble.sarima.fitted:
            metrics["aic"] = float(ensemble.sarima.fitted.aic)

        return jsonify({
            "model_type":     model_type,
            "horizon_months": months_ahead,
            "forecasts":      forecasts,
            "metrics":        metrics,
        })

    except Exception as exc:
        logger.exception("Forecast error")
        return jsonify({"error": f"Forecast error: {exc}"}), 500
