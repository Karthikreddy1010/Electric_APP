"""
Background AI Generation Worker Service.
Executes LLM narrative generation asynchronously without blocking HTTP response threads.
Persists AI state, latency, model tags, and fallback diagnostics to SQLite/PostgreSQL database.
"""
import time
import logging
from datetime import datetime, timezone
from typing import Union

from database.connection import get_sync_session
from database.models import CustomerBill
from database.auth_models import UserBill
from api.services.llm.llm_service import llm_service
from api.services.llm.context_builder import ContextBuilder
from api.services.llm.deterministic_fallback import DeterministicFallback

logger = logging.getLogger(__name__)


def process_bill_ai_task(bill_id: Union[str, int]):
    """
    Background worker that generates AI explanation text for a bill asynchronously.
    Runs via FastAPI BackgroundTasks without keeping the HTTP connection open.
    Supports both UserBill (UUID string) and CustomerBill (int ID).
    """
    logger.info(f"[Background AI Worker] Starting non-blocking AI task for Bill ID: {bill_id}...")
    start_time = time.time()

    with get_sync_session() as db:
        bill = None
        if isinstance(bill_id, str):
            bill = db.query(UserBill).filter(UserBill.id == bill_id).first()
        if not bill:
            try:
                numeric_id = int(bill_id)
                bill = db.query(CustomerBill).filter(CustomerBill.id == numeric_id).first()
            except (ValueError, TypeError):
                pass
        if not bill and isinstance(bill_id, str):
            # Check UserBill one more time
            bill = db.query(UserBill).filter(UserBill.id == bill_id).first()

        if not bill:
            logger.error(f"[Background AI Worker] Bill ID {bill_id} not found in database.")
            return

        # Mark state as generating
        bill.ai_status = "generating"
        db.commit()

        # Build bill dictionary for context builder
        usage = float(getattr(bill, "usage_kwh", 0.0) or 0.0)
        total = float(getattr(bill, "total_bill", 0.0) or 0.0)
        utility = getattr(bill, "utility_provider", None) or getattr(bill, "utility", "PSE&G") or "PSE&G"
        
        bill_data = {
            "id": str(bill.id),
            "bill_date": str(bill.bill_date),
            "billing_period": getattr(bill, "billing_period", "") or "",
            "usage_kwh": usage,
            "monthly_service_charge": round(total * 0.06, 2),
            "delivery_charge": round(total * 0.30, 2),
            "supply_charge": round(total * 0.58, 2),
            "tax": round(total * 0.06, 2),
            "total_bill": total,
            "utility": utility,
            "canonical_bill": {
                "components": [
                    {"name": "Customer Charge", "value": round(total * 0.06, 2)},
                    {"name": "Distribution Charge", "value": round(total * 0.30, 2)},
                    {"name": "BGS Supply", "value": round(total * 0.58, 2)},
                    {"name": "NJ Sales Tax", "value": round(total * 0.06, 2)},
                ]
            }
        }

        ctx = ContextBuilder.build_bill_analysis_context(bill_data)

        # Fast pre-flight check: if provider is offline, fall back immediately without queuing retries
        if not llm_service.provider.is_available():
            fallback_text = DeterministicFallback.get_fallback("bill_analysis", ctx)
            bill.ai_status = "offline"
            bill.ai_explanation = fallback_text
            bill.ai_recommendations = "Target variable usage charges during peak summer cooling hours."
            bill.ai_error_reason = "Ollama server unreachable. Used deterministic fallback."
            bill.ai_latency_ms = round((time.time() - start_time) * 1000, 2)
            bill.ai_generated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"[Background AI Worker] Ollama offline. Persisted fallback for Bill ID {bill_id}.")
            return

        try:
            import asyncio
            res = asyncio.run(
                llm_service.generate_explanation(
                    task="bill_analysis",
                    context_data=ctx,
                    bypass_cache=False
                )
            )

            explanation_text = res.get("explanation") or res.get("text", "")
            meta = res.get("metadata", {})
            fallback_used = meta.get("fallback_used", False)

            bill.ai_explanation = explanation_text
            bill.ai_recommendations = "Target BGS Supply component for supply-side rate optimization."
            bill.ai_model = meta.get("model", llm_service.provider.model)
            bill.ai_prompt_version = meta.get("prompt_version", "v1.0")
            bill.ai_latency_ms = meta.get("latency_ms", round((time.time() - start_time) * 1000, 2))
            bill.ai_generated_at = datetime.now(timezone.utc)

            if fallback_used:
                bill.ai_status = "fallback"
                bill.ai_error_reason = meta.get("fallback_reason", "Validation failed twice.")
            else:
                bill.ai_status = "completed"
                bill.ai_error_reason = None

            db.commit()
            logger.info(f"✓ [Background AI Worker] Completed AI task for Bill ID {bill_id} (Status: {bill.ai_status}).")

        except Exception as e:
            logger.error(f"[Background AI Worker] AI generation error for Bill ID {bill_id}: {e}")
            fallback_text = DeterministicFallback.get_fallback("bill_analysis", ctx)
            bill.ai_status = "failed"
            bill.ai_explanation = fallback_text
            bill.ai_error_reason = str(e)
            bill.ai_latency_ms = round((time.time() - start_time) * 1000, 2)
            bill.ai_generated_at = datetime.now(timezone.utc)
            db.commit()
