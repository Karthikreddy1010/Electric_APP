from fastapi import APIRouter, HTTPException
from api.state import app_state
from api.cache import cached
from api.schemas import GeoResponse, GeoPoint
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


@router.get("/geo", response_model=GeoResponse)
@cached(ttl=300)
async def get_geo(month: Optional[str] = None, view_mode: str = "bill"):
    from api.services.geo_insights_service import get_map_data, get_available_months
    
    monthly_df = app_state.get("geo_monthly_df")
    if monthly_df is None: 
        raise HTTPException(500, "No data")
    
    available_months = get_available_months(monthly_df)
    target_month = month or available_months[-1]
    
    raw_data = get_map_data(monthly_df, target_month, data_type=view_mode)
    
    data = []
    for row in raw_data:
        data.append(GeoPoint(
            state=row['state'],
            avg_bill=row['avg_bill'],
            avg_rate=row['avg_price'],
            rank=0
        ))
    
    # Calc rank
    data.sort(key=lambda x: x.avg_bill, reverse=True)
    for i, p in enumerate(data):
        p.rank = i + 1
        
    sorted_data = sorted(data, key=lambda x: x.avg_bill, reverse=True)
    
    return GeoResponse(
        data=data,
        top_5_expensive=sorted_data[:5],
        top_5_cheapest=sorted_data[-5:][::-1],
        available_months=available_months,
        current_month=target_month
    )


@router.get("/weather-kpis")
@cached(ttl=300)
async def get_weather_kpis(
    year: Optional[int] = None,
    month: Optional[int] = None,
    location: Optional[str] = None,
):
    """
    Weather KPI cards for the Dashboard.
    Returns: current temp, avg temp, humidity, rainfall, solar radiation,
    wind speed, weather severity, and monthly summary.
    """
    try:
        from backend.analytics.weather import weather_service
        summary = weather_service.get_weather_summary(
            location=location, year=year, month=month
        )

        if not summary.get("available"):
            return {"available": False, "message": "Weather data not available. Run NREL ingestion first."}

        return {
            "available": True,
            "kpis": summary,
        }
    except Exception as e:
        logger.error(f"Weather KPI error: {e}")
        return {"available": False, "error": str(e)}


@router.get("/weather-timeline")
@cached(ttl=600)
async def get_weather_timeline(
    location: Optional[str] = None,
    start_year: int = 2020,
    end_year: int = 2025,
):
    """
    Weather timeline data for Dashboard charts.
    Returns monthly time series for temperature, rainfall, solar, severity.
    """
    try:
        from data_pipeline.nrel_processor import get_nrel_processor
        processor = get_nrel_processor()
        monthly = processor.load_monthly(location=location)

        if monthly.empty:
            return {"available": False}

        monthly = monthly[
            (monthly["year"] >= start_year) & (monthly["year"] <= end_year)
        ].copy()

        monthly = monthly.sort_values(["year", "month"])

        # Aggregate across counties if no specific location
        if location is None:
            agg_cols = {}
            for col in ["temp_avg_c", "temp_avg_f", "monthly_hdd", "monthly_cdd",
                         "humidity_avg_pct", "monthly_solar_kwh_m2",
                         "monthly_precip_mm", "wind_speed_avg_ms",
                         "avg_weather_severity", "extreme_heat_days"]:
                if col in monthly.columns:
                    agg_cols[col] = (col, "mean")

            monthly = monthly.groupby(["year", "month"]).agg(**agg_cols).reset_index()

        # Build time series
        monthly["period"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)

        timeline = {
            "available": True,
            "periods": monthly["period"].tolist(),
        }

        col_map = {
            "temperature_f": "temp_avg_f",
            "temperature_c": "temp_avg_c",
            "hdd": "monthly_hdd",
            "cdd": "monthly_cdd",
            "humidity_pct": "humidity_avg_pct",
            "solar_kwh_m2": "monthly_solar_kwh_m2",
            "precipitation_mm": "monthly_precip_mm",
            "wind_speed_ms": "wind_speed_avg_ms",
            "severity_score": "avg_weather_severity",
            "extreme_heat_days": "extreme_heat_days",
        }

        for key, col in col_map.items():
            if col in monthly.columns:
                timeline[key] = [
                    round(float(v), 2) if not (isinstance(v, float) and v != v) else None
                    for v in monthly[col].values
                ]

        return timeline

    except Exception as e:
        logger.error(f"Weather timeline error: {e}")
        return {"available": False, "error": str(e)}
