"""
FastAPI router for Enterprise Tariff Optimization.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query
from api.services.tariff_optimization_engine import tariff_optimization_engine
from database.connection import get_sync_session
from database.auth_models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/impact/tariff-optimization", tags=["Tariffs"])


@router.get("")
def get_tariff_optimization(
    customer_id: str = Query(..., description="Unique customer/user ID to optimize for")
):
    """
    Evaluates available rate plans for a customer's ZIP code and utility.
    Returns comparison matrix and highest-savings plan recommendation.
    """
    try:
        results = tariff_optimization_engine.optimize(customer_id)
        return results
    except Exception as e:
        logger.exception("Error executing tariff optimization")
        raise HTTPException(500, f"Engine simulation failure: {str(e)}")


@router.post("/apply")
def apply_optimized_tariff(
    customer_id: str = Query(..., description="Customer ID"),
    tariff_id: int = Query(..., description="The ID of the tariff schedule to apply")
):
    """
    Updates the customer's active tariff reference to the recommended rate schedule.
    """
    with get_sync_session() as session:
        user = session.query(User).filter(User.id == customer_id).first()
        if not user:
            raise HTTPException(404, "User profile not found")
        
        # In a real environment, we'd update a Column like active_tariff_id.
        # Let's save it to user preferences JSON blob.
        if not user.preferences:
            user.preferences = {}
        user.preferences["active_tariff_id"] = tariff_id
        session.commit()
        
    return {
        "success": True,
        "message": f"Successfully switched rate structure to tariff plan ID {tariff_id}."
    }


# ── Retail Supplier ETF & Risk Evaluation Endpoints ─────────────────────────

@router.get("/evaluate-supplier-plan")
async def evaluate_supplier_plan(
    plan_name: str = Query("CleanGreen Fixed 12"),
    supplier_name: str = Query("Green Mountain Energy"),
    rate_type: str = Query("fixed"),
    current_rate_kwh: float = Query(0.214, ge=0),
    proposed_rate_kwh: float = Query(0.178, ge=0),
    monthly_kwh: float = Query(750.0, ge=0),
    contract_months: int = Query(12, ge=1),
    cancellation_fee: float = Query(150.0, ge=0),
    remaining_contract_months: int = Query(6, ge=0),
):
    """Evaluate retail supplier plan exit penalties (ETF), volatility score, supplier risk, and break-even month."""
    return tariff_optimization_engine.evaluate_supplier_plan(
        plan_name=plan_name,
        supplier_name=supplier_name,
        rate_type=rate_type,
        current_rate_kwh=current_rate_kwh,
        proposed_rate_kwh=proposed_rate_kwh,
        monthly_kwh=monthly_kwh,
        contract_months=contract_months,
        cancellation_fee=cancellation_fee,
        remaining_contract_months=remaining_contract_months,
    )

