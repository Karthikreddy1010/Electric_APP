"""GET /forecast — electricity demand forecast via trained ensemble."""
import logging
from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.cache import cached

logger = logging.getLogger(__name__)
router = APIRouter(tags=["forecast"])

@router.get("/forecast")
@cached(ttl=600)
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

        import pandas as pd
        mapped_forecast = []
        for fc in forecast_results:
            # Anchor historical vs predicted values safely
            val = fc["predicted_demand"] if fc["predicted_demand"] is not None else fc["historical_demand"]
            low = fc["lower_band"] if fc["lower_band"] is not None else val
            upp = fc["upper_band"] if fc["upper_band"] is not None else val
            
            mapped_forecast.append({
                "date": fc["date"],
                "historical_demand": fc["historical_demand"],
                "predicted_demand": fc["predicted_demand"],
                "lower_band": fc["lower_band"],
                "upper_band": fc["upper_band"],
                "value": val,
                "lower": low,
                "upper": upp,
                "forecast": fc["predicted_demand"] if fc["predicted_demand"] is not None else fc["historical_demand"],
            })

        # FIX: 3 - Return metrics dict with MAE, RMSE, and MAPE rounded to 2 decimal places
        metrics_dict = ensemble.metrics.get(model, ensemble.metrics["ensemble"]) # FIX: 3
        
        def safe_round(v):
            return round(v, 2) if (v is not None and pd.notna(v)) else 0.0

        output = {
            "forecast": mapped_forecast,
            "forecasts": mapped_forecast,
            "metrics": {
                "MAE": safe_round(metrics_dict.get("MAE")),
                "RMSE": safe_round(metrics_dict.get("RMSE")),
                "MAPE": safe_round(metrics_dict.get("MAPE")),
            },
            "model_weights": ensemble.weights if model == "ensemble" else None,
            "confidence_score": safe_round(ensemble.confidence_scores.get(model, ensemble.confidence_scores["ensemble"])),
            "model_used": model
        }
        
        return output

    except RuntimeError as exc:
        # Weather API or forecast service failure — fail loud
        logger.critical(f"Forecast RuntimeError (weather/API failure): {exc}")
        raise HTTPException(
            503,
            f"Forecast service unavailable: {exc}. "
            f"Weather API may be down — retry later."
        )
    except ValueError as exc:
        # Data quality issue (missing weather, broken ingestion)
        logger.error(f"Forecast ValueError (data quality): {exc}")
        raise HTTPException(
            422,
            f"Forecast data quality error: {exc}"
        )
    except Exception as exc:
        logger.exception("Forecast error")
        raise HTTPException(500, f"Forecast error: {exc}")
