"""
Forecast Service — wraps the ForecastEnsemble for route consumption.
"""
import pandas as pd
from api.schemas import ForecastRequest, ForecastResponse, ForecastPoint


def run_forecast(ensemble, billing: pd.DataFrame, req: ForecastRequest) -> ForecastResponse:
    """Execute forecast and return structured response."""
    preds = ensemble.predict_ensemble(steps=req.months_ahead)

    last_date = pd.to_datetime(billing["date"].max())
    future_dates = pd.date_range(
        last_date + pd.DateOffset(months=1),
        periods=req.months_ahead,
        freq="MS",
    )

    forecasts = []
    for i in range(len(preds)):
        forecasts.append(ForecastPoint(
            month=future_dates[i].strftime("%Y-%m"),
            forecast=round(float(preds["forecast_ensemble"].iloc[i]), 2),
            lower=round(float(preds["lower"].iloc[i]), 2) if req.include_ci else None,
            upper=round(float(preds["upper"].iloc[i]), 2) if req.include_ci else None,
        ))

    metrics = {}
    if ensemble.sarima.fitted:
        metrics["aic"] = float(ensemble.sarima.fitted.aic)

    return ForecastResponse(
        model_type=req.model_type,
        horizon_months=req.months_ahead,
        forecasts=forecasts,
        metrics=metrics,
    )
