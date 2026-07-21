"""
Celery Task Definitions for background workers.
Includes OCR parsing, forecast training, smart meter ingestion, LMP ingestion, and tariff optimization.
"""
from __future__ import annotations

import logging
import asyncio
from orchestration.celery_app import celery_app
from database.connection import get_sync_session, get_db
from database.auth_models import UserBill
from database.models import SmartMeterInterval, PjmLmpNode, PjmLmpHourly
from api.services.llm.llm_service import llm_service
from api.services.forecast_service import forecast_service
from orchestration.tasks import retrain_forecast_models_task, fetch_eia_demand_task

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.async_process_bill_ocr")
def async_process_bill_ocr(bill_id: str, bill_text: str) -> dict:
    """
    Asynchronously parses utility bill raw text using LLM and updates the database.
    """
    logger.info(f"Background task: processing OCR for bill {bill_id}")
    
    # We run the async llm_service using the async loop helper
    async def run():
        try:
            res = await llm_service.generate_explanation(
                task="ocr",
                context_data={"bill_text": bill_text},
                format="json"
            )
            return res
        except Exception as e:
            logger.error(f"Error calling LLM OCR in background worker: {e}")
            return None

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(run())

    with get_sync_session() as session:
        bill = session.query(UserBill).filter(UserBill.id == bill_id).first()
        if not bill:
            logger.error(f"Bill {bill_id} not found in database.")
            return {"error": "Bill not found"}

        if res and "text" in res:
            import json
            try:
                parsed = json.loads(res["text"])
                bill.bill_data = parsed
                bill.utility_provider = parsed.get("utility_name", bill.utility_provider)
                bill.usage_kwh = parsed.get("kwh_used", bill.usage_kwh)
                bill.total_bill = parsed.get("total_amount", bill.total_bill)
                bill.ai_status = "completed"
                bill.ai_explanation = parsed.get("insight", "")
            except Exception as e:
                logger.error(f"Failed to parse LLM response: {e}")
                bill.ai_status = "failed"
                bill.ai_error_reason = f"JSON parse error: {e}"
        else:
            bill.ai_status = "failed"
            bill.ai_error_reason = "LLM OCR returned empty result"

        session.commit()
        return {"status": bill.ai_status}


@celery_app.task(name="tasks.async_train_forecast")
def async_train_forecast() -> dict:
    """
    Offloads retraining of Prophet and SARIMAX ensembles.
    """
    logger.info("Background task: retraining forecasting models")
    try:
        retrain_forecast_models_task()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Forecasting retrain task failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="tasks.async_ingest_smart_meter")
def async_ingest_smart_meter(customer_id: str, file_content: str, file_type: str) -> dict:
    """
    Parses Green Button XML/JSON/CSV interval files and writes to database.
    """
    logger.info(f"Background task: ingesting smart meter data for {customer_id}")
    from api.services.smart_meter_service import smart_meter_service
    
    try:
        intervals = smart_meter_service.parse_file(file_content, file_type)
        inserted = smart_meter_service.save_intervals(customer_id, intervals)
        return {"status": "success", "records_inserted": inserted}
    except Exception as e:
        logger.error(f"Smart meter ingestion task failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="tasks.async_ingest_pjm_lmp")
def async_ingest_pjm_lmp() -> dict:
    """
    Syncs hourly PJM day-ahead and real-time LMP prices.
    """
    logger.info("Background task: syncing PJM grid node LMP prices")
    try:
        from data_pipeline.pjm_lmp_fetcher import sync_pjm_lmps
        count = sync_pjm_lmps()
        return {"status": "success", "records_synced": count}
    except Exception as e:
        logger.error(f"PJM LMP sync failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="tasks.async_run_tariff_optimization")
def async_run_tariff_optimization(customer_id: str) -> dict:
    """
    Runs tariff optimization engines across alternative options.
    """
    logger.info(f"Background task: running tariff optimization for customer {customer_id}")
    try:
        from api.services.tariff_optimization_engine import tariff_optimization_engine
        results = tariff_optimization_engine.optimize(customer_id)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Tariff optimization failed: {e}")
        return {"status": "failed", "error": str(e)}
