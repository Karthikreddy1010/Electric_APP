"""GET /forecast — electricity demand forecast via trained ensemble."""
import asyncio
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
            
        forecast_results = await asyncio.to_thread(ensemble.get_forecast, days=days_ahead, model_type=model)

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


# ── Anomaly Detection & Cleaning Extensions ───────────────────────────────────

from api.services.anomaly_detection_service import anomaly_detection_service
from fastapi import Body


@router.get("/forecast/anomalies")
def get_historical_anomalies(
    method: str = Query("mad", description="Anomaly detection method: 'mad', 'iforest', 'zscore'"),
    threshold: float = Query(3.0, description="Outlier threshold coefficient")
):
    """
    Scans historical billing records for data quality anomalies, shutdowns, and spikes.
    """
    billing = app_state.get("billing_df")
    if billing is None:
        raise HTTPException(500, "Historical data not loaded")

    # Run anomaly detection
    df_analyzed = anomaly_detection_service.detect_anomalies(
        df=billing,
        value_col="usage_kwh",
        date_col="date",
        method=method,
        threshold=threshold
    )

    records = []
    for _, row in df_analyzed.iterrows():
        records.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "usage_kwh": float(row["usage_kwh"]),
            "total_bill": float(row["total_bill"]),
            "is_anomaly": bool(row["is_anomaly"]),
            "anomaly_score": float(row["anomaly_score"])
        })
        
    return {
        "success": True,
        "anomalies": [r for r in records if r["is_anomaly"]],
        "all_records": records
    }


@router.post("/forecast/anomalies/resolve")
def resolve_anomalies(
    payload: dict = Body(..., example={"resolutions": {"2025-06-01": "replace", "2025-12-01": "keep"}})
):
    """
    Applies resolution actions to historical anomalies, updating the in-memory feature store.
    """
    billing = app_state.get("billing_df")
    if billing is None:
        raise HTTPException(500, "Historical data not loaded")

    # Clone df
    billing_cleaned = billing.copy()
    billing_cleaned["date"] = pd.to_datetime(billing_cleaned["date"])
    
    # Run base detection
    df_anom = anomaly_detection_service.detect_anomalies(billing_cleaned)
    
    resolutions = payload.get("resolutions", {})
    imputed_linear = anomaly_detection_service.impute_series(df_anom, method="linear")
    
    for idx, row in df_anom.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d")
        action = resolutions.get(date_str)
        
        if action == "replace" or (action is None and row["is_anomaly"]):
            # Replace with imputed value
            billing_cleaned.loc[idx, "usage_kwh"] = imputed_linear.loc[idx]
        elif action == "ignore":
            # Set to NaN or median
            billing_cleaned.loc[idx, "usage_kwh"] = billing["usage_kwh"].median()

    # Re-calculate total bills proportionally
    billing_cleaned["total_bill"] = billing_cleaned["usage_kwh"] * (billing["total_bill"] / billing["usage_kwh"].clip(lower=1))

    # Save to app_state
    app_state["billing_df"] = billing_cleaned
    
    return {
        "success": True,
        "message": f"Successfully applied {len(resolutions)} manual anomaly resolutions and re-seeded feature store."
    }


@router.get("/forecast/compare-cleaned")
def compare_cleaned_forecasts(
    imputation_method: str = Query("linear")
):
    """
    Ttrains forecasts on raw vs cleaned data and returns comparison accuracy metrics.
    """
    billing = app_state.get("billing_df")
    if billing is None:
        raise HTTPException(500, "Historical data not loaded")
        
    df_anom = anomaly_detection_service.detect_anomalies(billing)
    
    # Create clean copy
    cleaned_df = billing.copy()
    cleaned_df["usage_kwh"] = anomaly_detection_service.impute_series(df_anom, method=imputation_method)
    cleaned_df["total_bill"] = cleaned_df["usage_kwh"] * (billing["total_bill"] / billing["usage_kwh"].clip(lower=1))
    
    metrics = anomaly_detection_service.compare_forecasts(billing, cleaned_df)
    
    # Build before/after charts
    chart_data = []
    for i in range(len(billing)):
        date_str = pd.to_datetime(billing.loc[i, "date"]).strftime("%Y-%m-%d")
        chart_data.append({
            "date": date_str,
            "original_usage": float(billing.loc[i, "usage_kwh"]),
            "cleaned_usage": float(cleaned_df.loc[i, "usage_kwh"]),
            "is_anomaly": bool(df_anom.loc[i, "is_anomaly"])
        })
        
    return {
        "success": True,
        "metrics": metrics,
        "chart_data": chart_data
    }
