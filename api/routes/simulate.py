"""
Plan Simulation Engine Endpoints.
Provides Monte Carlo comparisons of fixed and variable rate energy tariffs under volatility.
"""
from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.schemas import SimulateRequest, SimulateResult
from api.services.bill_impact_engine import bill_impact_engine, COMPONENT_TYPES
from models.simulation_model import PlanSimulator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


class PlanSimulationRequest(BaseModel):
    monthly_usage_kwh: float = Field(750.0, ge=50, le=10000)
    n_simulations: int = Field(1000, ge=100, le=10000)
    horizon_months: int = Field(12, ge=1, le=24)


class PlanComparisonRecord(BaseModel):
    provider: str
    plan_type: str
    base_rate: float
    volatility: float
    expected_annual_cost: float
    std_annual_cost: float
    p5_cost: float
    p95_cost: float
    risk_score: float


class PlanSimulationResponse(BaseModel):
    comparison: List[PlanComparisonRecord]
    recommended: PlanComparisonRecord


@router.post("/simulate", response_model=SimulateResult)
async def simulate_impact(req: SimulateRequest):
    sim = bill_impact_engine.what_if_simulation(req.modifications, req.kwh)
    
    # Formula construction
    comp_labels = []
    for k, v in req.modifications.items():
        key = k
        if key not in COMPONENT_TYPES:
            if f"{key}_rate" in COMPONENT_TYPES:
                key = f"{key}_rate"
            elif f"{key}_charge" in COMPONENT_TYPES:
                key = f"{key}_charge"
        label = COMPONENT_TYPES[key]['label'] if key in COMPONENT_TYPES else k.upper()
        comp_labels.append(f"{label} ({v}%)")
        
    formula = "New Bill = Base Bill × (1 + Σ(% Change_i × Weight_i) × Elasticity)"
    
    return SimulateResult(
        old_bill=sim['base_bill'],
        new_bill=sim['new_bill'],
        delta_abs=sim['total_impact'],
        delta_pct=round((sim['total_impact'] / sim['base_bill'] * 100), 2) if sim['base_bill'] > 0 else 0,
        formula=formula,
        explanation=f"If {', '.join(comp_labels)} change, your bill increases/decreases by approximately {sim['total_impact']} based on historical elasticity."
    )


@router.post("/plan-simulation", response_model=PlanSimulationResponse)
async def run_plan_simulation(req: PlanSimulationRequest):
    """
    Runs a Monte Carlo simulation over fixed, variable, and green tariff plans
    to compare risk and expected costs over a horizon.
    """
    try:
        # Create dummy historical usage based on input average
        hist_usage = np.full(12, req.monthly_usage_kwh)
        
        # Fetch empirical EIA-923 wholesale natural gas price volatility & battery efficiency parameters
        gas_volatility = 0.08
        storage_eff = 81.4
        try:
            from api.services.eia923_service import get_eia923_fuel_cost_summary, get_eia923_storage_summary
            fc_info = get_eia923_fuel_cost_summary("NJ")
            st_info = get_eia923_storage_summary("NJ")
            if fc_info.get("trend_costs") and len(fc_info["trend_costs"]) > 1:
                std_dev = np.std(fc_info["trend_costs"])
                mean_val = np.mean(fc_info["trend_costs"])
                if mean_val > 0:
                    gas_volatility = float(round(std_dev / mean_val, 4))
            storage_eff = float(st_info.get("roundtrip_efficiency_pct", 81.4))
        except Exception as e_sim_eia:
            logger.warning(f"Failed to load EIA-923 parameters for simulation: {e_sim_eia}")

        # Define candidate plans calibrated with empirical EIA-923 parameters
        plans = [
            {"provider": "PSEG Standard Fixed", "type": "fixed", "rate": 0.125, "volatility": 0.0},
            {"provider": "CleanGreen Variable", "type": "variable", "rate": 0.115, "volatility": gas_volatility},
            {"provider": "Direct Energy Fixed", "type": "fixed", "rate": 0.132, "volatility": 0.0},
            {"provider": "Voltaic Storage Arbitrage", "type": "variable", "rate": 0.119 * (1.0 - (100.0 - storage_eff) / 100.0 * 0.1), "volatility": round(gas_volatility * 0.7, 4)}
        ]
        
        simulator = PlanSimulator(
            n_simulations=req.n_simulations,
            horizon_months=req.horizon_months,
            random_state=42
        )
        
        df_comparison = simulator.compare_plans(plans, hist_usage)
        records = df_comparison.to_dict(orient="records")
        
        # Select best plan based on expected annual cost
        best_record = min(records, key=lambda x: x["expected_annual_cost"])
        
        return PlanSimulationResponse(
            comparison=records,
            recommended=best_record
        )
    except Exception as e:
        logger.exception("Error executing plan simulation")
        raise HTTPException(500, f"Monte Carlo simulation failure: {str(e)}")
