"""
Health check endpoint.
GET /health → system status, loaded model flags, data freshness.
"""
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    billing = current_app.config.get("BILLING_DF")
    data_freshness = None
    if billing is not None:
        data_freshness = str(billing["date"].max())

    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "models_loaded": {
            "impact": current_app.config.get("IMPACT_MODEL") is not None,
            "forecast": current_app.config.get("FORECAST_MODEL") is not None,
        },
        "data_freshness": data_freshness,
    })
