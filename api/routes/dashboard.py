from fastapi import APIRouter, HTTPException
from api.state import app_state
from api.cache import cached
from api.schemas import GeoResponse, PlanSimResponse, GeoPoint
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


@router.get("/plans", response_model=PlanSimResponse)
@cached(ttl=300)
async def get_plans(customer_id: str = None):
    from api.services.simulation_service import run_plan_simulation
    from api.schemas import PlanSimRequest
    from database.connection import get_sync_session
    from database.models import CustomerBill
    
    plans_df = app_state.get("plans_df")
    billing_df = app_state.get("billing_df")
    
    monthly_usage = 750.0
    if customer_id:
        with get_sync_session() as session:
            bills = session.query(CustomerBill).filter(CustomerBill.customer_id == customer_id).all()
            if bills:
                monthly_usage = sum(b.usage_kwh for b in bills) / len(bills)
    
    req = PlanSimRequest(
        monthly_usage_kwh=round(monthly_usage, 2),
        usage_growth_pct=0.0,
        horizon_months=12,
        n_simulations=1000
    )
    
    return run_plan_simulation(plans_df, billing_df, req)
