"""
GET /health — system status, loaded model flags, data freshness.
"""
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    svc = current_app.extensions["svc"]
    data_freshness = None
    if svc.billing_df is not None:
        data_freshness = str(svc.billing_df["date"].max())

    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "models_loaded": {
            "impact":   svc.impact_model is not None,
            "forecast": svc.forecast_model is not None,
        },
        "data_freshness": data_freshness,
    })
