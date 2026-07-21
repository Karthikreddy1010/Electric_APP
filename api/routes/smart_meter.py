"""
FastAPI router for real-time Smart Meter analytics and ingestion.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from api.services.smart_meter_service import smart_meter_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/smart-meter", tags=["smart-meter"])


@router.post("/upload")
async def upload_smart_meter_data(
    customer_id: str = Form(..., description="The unique customer identifier"),
    file: UploadFile = File(...)
):
    """
    Accepts utility Smart Meter interval records (XML, JSON, CSV) and ingests them into the DW.
    """
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="ignore")
        
        # Determine file type
        file_type = "csv"
        if file.filename:
            if file.filename.endswith(".xml"):
                file_type = "xml"
            elif file.filename.endswith(".json"):
                file_type = "json"

        # Call ingestion task (sync fallback / eager celery)
        from orchestration.worker_tasks import async_ingest_smart_meter
        result = async_ingest_smart_meter.delay(customer_id, content, file_type)
        
        # Get result
        res_data = result.get(timeout=10)
        if res_data.get("status") == "success":
            return {
                "success": True,
                "message": f"Successfully processed smart meter file. Ingested {res_data.get('records_inserted', 0)} interval readings.",
                "records_inserted": res_data.get("records_inserted", 0)
            }
        else:
            raise HTTPException(400, f"Ingestion pipeline failed: {res_data.get('error')}")
            
    except Exception as e:
        logger.exception("Error processing smart meter upload")
        raise HTTPException(500, f"Internal file processor failure: {str(e)}")


@router.get("/hourly")
def get_hourly_usage(
    customer_id: str = Query(..., description="Customer ID"),
    days_back: int = Query(7, description="Number of days history to retrieve")
):
    """
    Retrieves hourly interval demand usage curves.
    """
    curves = smart_meter_service.get_load_curves(customer_id)
    # return the hourly load curves
    return {
        "success": True,
        "customer_id": customer_id,
        "hourly_data": curves["load_curve_24h"]
    }


@router.get("/daily")
def get_daily_usage(
    customer_id: str = Query(..., description="Customer ID"),
    days_back: int = Query(30, description="Number of days history to retrieve")
):
    """
    Retrieves aggregated daily electricity usage.
    """
    curves = smart_meter_service.get_load_curves(customer_id)
    return {
        "success": True,
        "customer_id": customer_id,
        "daily_data": curves["trends"]
    }


@router.get("/live-status")
def get_live_status(
    customer_id: str = Query(..., description="Customer ID")
):
    """
    Returns real-time aggregated metrics (Current demand kW, power factor, alerts).
    """
    kpis = smart_meter_service.get_kpis(customer_id)
    return kpis


@router.get("/demand-history")
def get_demand_history(
    customer_id: str = Query(..., description="Customer ID")
):
    """
    Returns demand history and heatmaps for load analysis.
    """
    curves = smart_meter_service.get_load_curves(customer_id)
    return {
        "success": True,
        "customer_id": customer_id,
        "heatmap": curves["heatmap"]
    }
