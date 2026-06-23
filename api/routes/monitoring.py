"""GET /monitoring/health — system health, database freshness, weather API status, and data drift detection."""
import logging
import time
import pandas as pd
import numpy as np
import requests
from fastapi import APIRouter
from database.connection import get_sync_session
from database.models import DailySubBaDemand, WeatherOpenMeteo
from data_pipeline.weather_service import NJ_LAT, NJ_LON

logger = logging.getLogger(__name__)
router = APIRouter(tags=["monitoring"])

@router.get("/monitoring/health")
async def get_monitoring_health():
    """Enterprise-grade health check: database status, weather API status, and data drift detection."""
    health_status = {
        "status": "healthy",
        "timestamp": pd.Timestamp.now().isoformat(),
        "database": {"status": "ok", "demand_freshness": "ok", "weather_freshness": "ok"},
        "weather_api": {"status": "ok", "latency_ms": 0.0},
        "data_drift": {"status": "no_drift", "score": 0.0, "metrics": {}}
    }
    
    # ── 1. Database & Freshness Check ──
    try:
        with get_sync_session() as session:
            # Check demand records
            demand_q = session.query(DailySubBaDemand)
            demand_count = demand_q.count()
            last_demand = demand_q.order_by(DailySubBaDemand.period.desc()).first()
            
            # Check weather records
            weather_q = session.query(WeatherOpenMeteo)
            weather_count = weather_q.count()
            last_weather = weather_q.order_by(WeatherOpenMeteo.date.desc()).first()
            
        if demand_count == 0 or weather_count == 0:
            health_status["status"] = "degraded"
            health_status["database"]["status"] = "empty"
        
        # Freshness: Demand data shouldn't be older than 48 hours
        if last_demand:
            demand_age_days = (pd.Timestamp.now().date() - last_demand.period).days
            health_status["database"]["last_demand_date"] = str(last_demand.period)
            health_status["database"]["demand_age_days"] = demand_age_days
            if demand_age_days > 2:
                health_status["status"] = "degraded"
                health_status["database"]["demand_freshness"] = "stale"
                logger.warning(f"Database demand data is stale: {demand_age_days} days old.")
        else:
            health_status["database"]["demand_freshness"] = "missing"
            health_status["status"] = "degraded"
            
        if last_weather:
            weather_age_days = (pd.Timestamp.now().date() - last_weather.date).days
            health_status["database"]["last_weather_date"] = str(last_weather.date)
            health_status["database"]["weather_age_days"] = weather_age_days
            if weather_age_days > 2:
                health_status["status"] = "degraded"
                health_status["database"]["weather_freshness"] = "stale"
                logger.warning(f"Database weather data is stale: {weather_age_days} days old.")
        else:
            health_status["database"]["weather_freshness"] = "missing"
            health_status["status"] = "degraded"
            
        health_status["database"]["demand_records"] = demand_count
        health_status["database"]["weather_records"] = weather_count
        
    except Exception as e:
        logger.exception("Database health check failed")
        health_status["status"] = "unhealthy"
        health_status["database"] = {"status": "error", "error": str(e)}

    # ── 2. Weather API Status Check ──
    try:
        t0 = time.time()
        # Ping the Open-Meteo API using a lightweight request (1 forecast day)
        ping_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": NJ_LAT,
            "longitude": NJ_LON,
            "forecast_days": 1,
        }
        resp = requests.get(ping_url, params=params, timeout=5)
        latency = (time.time() - t0) * 1000
        health_status["weather_api"]["latency_ms"] = round(latency, 2)
        
        if resp.status_code != 200:
            health_status["status"] = "degraded"
            health_status["weather_api"]["status"] = f"error_code_{resp.status_code}"
            logger.error(f"Weather API check failed with status code {resp.status_code}")
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["weather_api"]["status"] = "unreachable"
        health_status["weather_api"]["error"] = str(e)
        logger.error(f"Weather API check failed to connect: {e}")

    # ── 3. Data Drift Detection ──
    # Check if weather distributions have drifted significantly.
    # Compare the last 30 days of average temperature against the historical average for the current month.
    try:
        with get_sync_session() as session:
            rows = session.query(WeatherOpenMeteo).order_by(WeatherOpenMeteo.date.asc()).all()
            
        if len(rows) >= 60:
            df = pd.DataFrame([{
                "date": pd.Timestamp(r.date),
                "temp_avg": r.temp_avg
            } for r in rows if r.temp_avg is not None])
            
            if not df.empty:
                df = df.set_index("date")
                recent = df.tail(30)
                
                # Get historical reference (same calendar month)
                curr_month = pd.Timestamp.now().month
                historical = df[df.index.month == curr_month]
                # Exclude the recent 30 days from reference
                historical = historical[~historical.index.isin(recent.index)]
                
                if len(historical) >= 30:
                    mu_hist = historical["temp_avg"].mean()
                    sigma_hist = historical["temp_avg"].std()
                    
                    mu_recent = recent["temp_avg"].mean()
                    
                    # Compute Z-score shift in mean
                    std_err = sigma_hist / np.sqrt(30) if sigma_hist > 0 else 1.0
                    z_score = abs(mu_recent - mu_hist) / std_err
                    
                    health_status["data_drift"]["score"] = round(z_score, 2)
                    health_status["data_drift"]["metrics"] = {
                        "historical_mean": round(mu_hist, 2),
                        "recent_mean": round(mu_recent, 2),
                        "std_dev_reference": round(sigma_hist, 2),
                        "drift_z_score": round(z_score, 2)
                    }
                    
                    if z_score > 3.0:
                        # Significant statistical drift (99.7% confidence shift)
                        health_status["data_drift"]["status"] = "drift_detected"
                        health_status["status"] = "degraded"
                        logger.warning(
                            f"Significant weather data drift detected: Z-Score = {z_score:.2f} "
                            f"(Historical Mean: {mu_hist:.1f}°C, Recent Mean: {mu_recent:.1f}°C)"
                        )
                else:
                    health_status["data_drift"]["status"] = "insufficient_reference_data"
            else:
                health_status["data_drift"]["status"] = "no_valid_weather_data"
        else:
            health_status["data_drift"]["status"] = "insufficient_historical_data"
            
    except Exception as e:
        logger.exception("Data drift check failed")
        health_status["data_drift"]["status"] = "error"
        health_status["data_drift"]["error"] = str(e)
        
    return health_status
