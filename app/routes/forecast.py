"""
GET /forecast — generate electricity demand forecast via trained ensemble.
"""
import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
forecast_bp = Blueprint("forecast", __name__)

@forecast_bp.get("/forecast")
def forecast_costs():
    """Generate electricity demand forecast."""
    try:
        days_ahead = int(request.args.get("horizon", 30))
        if days_ahead not in [7, 30]:
            days_ahead = 30
    except (TypeError, ValueError):
        days_ahead = 30
        
    model_type = request.args.get("model", "ensemble")

    try:
        from models.forecast_model import ElectricityDemandForecaster
        
        svc = current_app.extensions["svc"]
        if not hasattr(svc, "demand_forecaster") or svc.demand_forecaster is None:
            svc.demand_forecaster = ElectricityDemandForecaster()
            # Note: training might take some time on the first request
            svc.demand_forecaster.train_and_evaluate()
            
        forecaster = svc.demand_forecaster
        forecast_results = forecaster.get_forecast(days=days_ahead, model_type=model_type)

        output = {
            "forecast": forecast_results,
            "metrics": forecaster.metrics.get(model_type, forecaster.metrics["ensemble"]),
            "model_weights": forecaster.weights if model_type == "ensemble" else None,
            "confidence_score": forecaster.confidence_scores.get(model_type, forecaster.confidence_scores["ensemble"]),
            "model_used": model_type
        }
        
        return jsonify(output)

    except Exception as exc:
        logger.exception("Forecast error")
        return jsonify({"error": f"Forecast error: {exc}"}), 500
