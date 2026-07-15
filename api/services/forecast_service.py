"""
Forecast Service — wraps the ForecastEnsemble for route consumption.
"""
import logging
import pandas as pd
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc
from database.auth_models import UserBill
from api.state import app_state
from api.cache import invalidate_all_caches
from api.schemas import ForecastRequest, ForecastResponse, ForecastPoint

logger = logging.getLogger(__name__)


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


async def recalculate_user_forecasts(user_id: str, db: AsyncSession, active_bill_id: Optional[str] = None):
    """
    Recalculates next month bill forecast for user based on all uploaded bills,
    validates preconditions, and persists forecast_results on the active bill.
    """
    # 1. Fetch all bills for the user
    res = await db.execute(
        select(UserBill)
        .where(UserBill.user_id == user_id, UserBill.status == "active")
        .order_by(asc(UserBill.bill_date))
    )
    bills = res.scalars().all()
    count = len(bills)
    
    # Identify the active bill
    if not bills:
        return
        
    if active_bill_id:
        active_bill = next((b for b in bills if b.id == active_bill_id), bills[-1])
    else:
        active_bill = bills[-1]
        
    # Precondition Checks
    # a. Check minimum count
    if count < 3:
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": "Upload at least 3–6 consecutive monthly bills to generate a reliable forecast.",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": round(min(100.0, (count / 3.0) * 100.0), 2)
        }
        db.add(active_bill)
        return

    # b. Check billing periods are consecutive (no gap > 45 days)
    consecutive = True
    bill_dates = [b.bill_date for b in bills]
    for i in range(1, len(bill_dates)):
        gap = (bill_dates[i] - bill_dates[i-1]).days
        if gap < 15 or gap > 45:
            consecutive = False
            break
            
    if not consecutive:
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": "Billing periods are not consecutive. Upload consecutive monthly bills to generate a reliable forecast.",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": 100.0
        }
        db.add(active_bill)
        return

    # c. Check bills belong to the same utility/account
    utilities = {b.utility_provider for b in bills if b.utility_provider}
    accounts = {b.bill_data.get("account_number") for b in bills if b.bill_data.get("account_number")}
    if len(utilities) > 1 or len(accounts) > 1:
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": "Bills belong to different utility providers or accounts. Ensure all uploaded bills are for the same account.",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": 100.0
        }
        db.add(active_bill)
        return

    # d. Check usage data exists
    has_usage = all(b.usage_kwh is not None and b.usage_kwh > 0 for b in bills)
    if not has_usage:
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": "Usage data is missing or invalid in one or more bills.",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": 100.0
        }
        db.add(active_bill)
        return

    # e. Check billing dates are valid
    has_valid_dates = all(b.bill_date is not None for b in bills)
    if not has_valid_dates:
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": "One or more bills contain invalid billing dates.",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": 100.0
        }
        db.add(active_bill)
        return

    # f. Check tariff information exists
    has_tariff = all(b.bill_data.get("rate_schedule") is not None for b in bills)
    if not has_tariff:
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": "Tariff/Rate schedule information is missing in one or more bills.",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": 100.0
        }
        db.add(active_bill)
        return

    # g. Retrieve weather/forecasting model
    ensemble = app_state.get("forecast_model")
    if ensemble is None:
        try:
            from models.forecast_model import ElectricityDemandForecaster
            import asyncio
            ensemble = ElectricityDemandForecaster()
            await asyncio.to_thread(ensemble.train_and_evaluate)
            app_state["forecast_model"] = ensemble
        except Exception as exc:
            logger.error(f"Failed to initialize grid forecast model: {exc}")
            active_bill.forecast_results = {
                "status": "unavailable",
                "reason": "Grid demand/weather forecasting system is offline.",
                "bills_available": count,
                "bills_required": 3,
                "readiness_pct": 100.0
            }
            db.add(active_bill)
            return

    # h. Model inference
    try:
        import asyncio
        forecast_results = await asyncio.to_thread(ensemble.get_forecast, days=30, model_type="ensemble")
        if not forecast_results:
            raise ValueError("Grid forecast returned empty results.")
    except Exception as exc:
        logger.error(f"Forecast model inference failed: {exc}")
        active_bill.forecast_results = {
            "status": "unavailable",
            "reason": f"Model inference failed: {str(exc)}",
            "bills_available": count,
            "bills_required": 3,
            "readiness_pct": 100.0
        }
        db.add(active_bill)
        return

    # 2. Perform forecasting calculations
    # Calculate user average daily usage
    days = active_bill.bill_data.get("days", 30)
    if not days or days <= 0:
        days = 30
    avg_daily = active_bill.usage_kwh / days
    
    # Scale user daily usage based on grid daily predictions
    valid_preds = [fc["predicted_demand"] for fc in forecast_results if fc["predicted_demand"] is not None]
    avg_grid = sum(valid_preds) / len(valid_preds) if len(valid_preds) > 0 else 1.0
    
    rate = active_bill.bill_data.get("effective_rate")
    if not rate or rate <= 0:
        rate = active_bill.total_bill / active_bill.usage_kwh if active_bill.usage_kwh > 0 else 0.185
        
    scaled_forecast = []
    for fc in forecast_results:
        grid_val = fc["predicted_demand"] if fc["predicted_demand"] is not None else fc["historical_demand"]
        ratio = grid_val / avg_grid if avg_grid > 0 else 1.0
        user_day_usage = avg_daily * ratio
        
        # Calculate bounds
        grid_lower = fc.get("lower_band") or grid_val
        grid_upper = fc.get("upper_band") or grid_val
        user_day_lower = avg_daily * (grid_lower / avg_grid) if avg_grid > 0 else avg_daily
        user_day_upper = avg_daily * (grid_upper / avg_grid) if avg_grid > 0 else avg_daily
        
        scaled_forecast.append({
            "date": fc["date"],
            "predicted_demand": round(user_day_usage, 2),
            "lower_band": round(user_day_lower, 2),
            "upper_band": round(user_day_upper, 2),
            "predicted_cost": round(user_day_usage * rate, 2),
            "lower_cost": round(user_day_lower * rate, 2),
            "upper_cost": round(user_day_upper * rate, 2)
        })
        
    # Aggregate values for next month (last 30 days of forecast)
    forecast_points = scaled_forecast[-30:]
    predicted_usage = round(sum(pt["predicted_demand"] for pt in forecast_points), 2)
    predicted_bill = round(sum(pt["predicted_cost"] for pt in forecast_points), 2)
    predicted_bill_lower = round(sum(pt["lower_cost"] for pt in forecast_points), 2)
    predicted_bill_upper = round(sum(pt["upper_cost"] for pt in forecast_points), 2)
    
    # Calculate Expected Change (%)
    expected_change_pct = round(((predicted_bill - active_bill.total_bill) / active_bill.total_bill * 100.0), 2) if active_bill.total_bill > 0 else 0.0
    
    # Confidence Score & Level
    base_score = 70.0 + min(20.0, (count - 3) * 5.0)
    grid_score = ensemble.confidence_scores.get("ensemble", 90.0)
    if pd.isna(grid_score) or grid_score is None:
        grid_score = 90.0
    confidence_score = round(0.6 * base_score + 0.4 * grid_score, 1)
    
    if confidence_score >= 95.0:
        confidence_level = "Very High"
    elif confidence_score >= 85.0:
        confidence_level = "High"
    elif confidence_score >= 70.0:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"

    # Key Drivers
    key_drivers = []
    month_active = active_bill.bill_date.month
    month_forecast = (active_bill.bill_date.month % 12) + 1
    
    cdd_map = {1:0.0, 2:0.0, 3:0.0, 4:5.0, 5:45.0, 6:180.0, 7:310.0, 8:260.0, 9:100.0, 10:15.0, 11:0.0, 12:0.0}
    hdd_map = {1:950.0, 2:820.0, 3:650.0, 4:350.0, 5:120.0, 6:10.0, 7:0.0, 8:0.0, 9:30.0, 10:220.0, 11:500.0, 12:820.0}
    
    if cdd_map[month_forecast] > cdd_map[month_active] + 20:
        key_drivers.append("Higher Cooling Demand")
    elif cdd_map[month_forecast] < cdd_map[month_active] - 20:
        key_drivers.append("Lower Cooling Demand")
        
    if hdd_map[month_forecast] > hdd_map[month_active] + 50:
        key_drivers.append("Higher Heating Demand")
    elif hdd_map[month_forecast] < hdd_map[month_active] - 50:
        key_drivers.append("Lower Heating Demand")
        
    usages = [b.usage_kwh for b in bills[-3:]]
    if len(usages) >= 3:
        trend = usages[-1] - usages[-3]
        if trend > 0.05 * usages[-3]:
            key_drivers.append("Increased Consumption Trend")
        elif trend < -0.05 * usages[-3]:
            key_drivers.append("Decreased Consumption Trend")
            
    if len(bills) >= 2:
        last_rate = bills[-1].bill_data.get("effective_rate")
        prev_rate = bills[-2].bill_data.get("effective_rate")
        if last_rate and prev_rate and abs(last_rate - prev_rate) / prev_rate > 0.02:
            key_drivers.append("Rate Schedule Change")
            
    if month_forecast in [6, 7, 8, 12, 1, 2]:
        key_drivers.append("Seasonal Pattern")
        
    key_drivers.append("Weather Forecast")
    
    # Try calling LLM, fallback deterministic
    drivers_str = " and ".join(key_drivers[:3])
    explanation = f"The predicted next month bill is ${predicted_bill:.2f} ({'+' if expected_change_pct >= 0 else ''}{expected_change_pct:.1f}% change). This forecast is primarily driven by {drivers_str} based on {len(bills)} months of billing history and grid weather indicators."
    
    try:
        from api.services.llm.llm_service import llm_service
        ctx = {
            "bill": {
                "utility": active_bill.utility_provider,
                "usage_kwh": active_bill.usage_kwh,
                "total_bill": active_bill.total_bill
            },
            "forecast": {
                "predicted_kwh": predicted_usage,
                "predicted_cost": predicted_bill,
                "expected_change_pct": expected_change_pct,
                "key_drivers": key_drivers
            }
        }
        res = await llm_service.generate_explanation(
            task="forecast",
            context_data=ctx
        )
        if res.get("success") and res.get("explanation"):
            explanation = res["explanation"]
    except Exception as e:
        logger.warning(f"LLM forecast explanation failed: {e}. Using fallback explanation.")
        
    # Save results
    active_bill.forecast_results = {
        "status": "success",
        "predicted_bill": predicted_bill,
        "predicted_usage_kwh": predicted_usage,
        "expected_change_pct": expected_change_pct,
        "confidence_interval": [predicted_bill_lower, predicted_bill_upper],
        "confidence_score": confidence_score,
        "confidence_level": confidence_level,
        "forecast_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "model_used": "Prophet + SARIMAX Ensemble",
        "model_version": "v1.0.0",
        "key_drivers": key_drivers,
        "explanation": explanation,
        "historical_bills": [
            {"date": str(b.bill_date), "total_bill": b.total_bill, "usage_kwh": b.usage_kwh}
            for b in bills
        ],
        "forecast_points": [
            {
                "date": pt["date"],
                "predicted_cost": pt["predicted_cost"],
                "predicted_demand": pt["predicted_demand"],
                "lower_band": pt["lower_band"],
                "upper_band": pt["upper_band"]
            }
            for pt in scaled_forecast
        ]
    }
    db.add(active_bill)

