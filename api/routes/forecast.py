"""GET /forecast — electricity demand forecast via trained ensemble."""
import logging
from fastapi import APIRouter, HTTPException, Query
from api.state import app_state

logger = logging.getLogger(__name__)
router = APIRouter(tags=["forecast"])

@router.get("/forecast")
async def forecast_costs(
    horizon: int = Query(30),
    model: str = Query("ensemble")
):
    """Generate electricity demand forecast."""
    try:
        days_ahead = horizon
        if days_ahead not in [7, 30]:
            days_ahead = 30

        ensemble = app_state.get("forecast_model")
        if ensemble is None:
            # We can lazy-load it if it failed during startup
            from models.forecast_model import ElectricityDemandForecaster
            ensemble = ElectricityDemandForecaster()
            ensemble.train_and_evaluate()
            app_state["forecast_model"] = ensemble
            
        forecast_results = ensemble.get_forecast(days=days_ahead, model_type=model)

        # FIX: 3 - Return metrics dict with MAE, RMSE, and MAPE rounded to 2 decimal places
        metrics_dict = ensemble.metrics.get(model, ensemble.metrics["ensemble"]) # FIX: 3
        output = {
            "forecast": forecast_results,
            "metrics": {
                "MAE": round(metrics_dict["MAE"], 2), # FIX: 3
                "RMSE": round(metrics_dict["RMSE"], 2), # FIX: 3
                "MAPE": round(metrics_dict["MAPE"], 2),  # FIX: 3
            },
            "model_weights": ensemble.weights if model == "ensemble" else None, # FIX: 3
            "confidence_score": ensemble.confidence_scores.get(model, ensemble.confidence_scores["ensemble"]),
            "model_used": model
        }
        
        return output

    except Exception as exc:
        logger.exception("Forecast error")
        raise HTTPException(500, f"Forecast error: {exc}")
