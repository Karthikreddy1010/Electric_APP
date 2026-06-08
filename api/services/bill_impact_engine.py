"""
Bill Impact Engine — Deterministic, Statistical, and Causal Analysis of Electricity Costs.

This module implements:
1. Deterministic Layer (Accounting Identity): Bill = Sum(Components)
2. Statistical Layer (Regression): Partial correlations and elasticity
3. Causal Layer (DoWhy/DML): True impact of rate changes controlling for usage/weather.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from api.state import app_state

logger = logging.getLogger(__name__)

# Constants
NJ_SALES_TAX_RATE = 0.06625

COMPONENT_TYPES = {
    "customer_charge": {
        "label": "Customer Charge",
        "type": "fixed",
        "cost_col": "customer_charge",
        "driver": "fixed",
        "reasoning": "Fixed impact independent of consumption; reflects the cost of maintaining the account and meter connection.",
    },
    "bgs_rate": {
        "label": "BGS Supply",
        "type": "variable",
        "cost_col": "bgs_cost",
        "driver": "market",
        "reasoning": "High impact because scales with usage (kWh). Reflects wholesale electricity supply prices.",
    },
    "distribution_rate": {
        "label": "Distribution Charge",
        "type": "variable",
        "cost_col": "distribution_cost",
        "driver": "infrastructure",
        "reasoning": "Significant impact scaling with usage; funds local delivery infrastructure.",
    },
    "transmission_rate": {
        "label": "Transmission Charge",
        "type": "variable",
        "cost_col": "transmission_cost",
        "driver": "market",
        "reasoning": "Scales with usage; reflects regional high-voltage grid costs.",
    },
    "sbc_rate": {
        "label": "Societal Benefits Charge",
        "type": "variable",
        "cost_col": "sbc_cost",
        "driver": "policy",
        "reasoning": "Lower impact scaling with usage; funds energy efficiency and social programs.",
    },
    "transition_rate": {
        "label": "Transition Charge",
        "type": "variable",
        "cost_col": "transition_cost",
        "driver": "regulatory",
        "reasoning": "Scaling impact; handles stranded costs and legacy regulatory adjustments.",
    },
}

class BillImpactEngine:
    def __init__(self):
        self.tax_rate = NJ_SALES_TAX_RATE

    def get_elasticity(self) -> float:
        demand_model = app_state.get("demand_model")
        if demand_model and demand_model.is_trained:
            return demand_model.get_learned_elasticity()
        return -0.20

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. DETERMINISTIC LAYER (Ground Truth)
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate_total_bill(self, components: dict[str, float], kwh: float) -> dict[str, Any]:
        """
        DETERMINISTIC LAYER: Accounting Identity.
        Total_Bill = sum(fixed) + sum(variable * kwh)
        Upgraded to use loss-adjusted consumption for the energy/supply (bgs_rate) component.
        """
        from models.pjm_market_physics import DEFAULT_PJM, compute_effective_kwh

        line_items = {}
        subtotal = 0.0

        for key, meta in COMPONENT_TYPES.items():
            val = components.get(key, 0.0)
            if meta["type"] == "variable":
                if key == "bgs_rate":
                    # Loss-adjusted consumption for energy supply
                    eff_kwh = compute_effective_kwh(kwh, DEFAULT_PJM.total_loss_factor)
                    cost = round(val * eff_kwh, 2)
                else:
                    cost = round(val * kwh, 2)
            else:
                cost = round(val, 2)
            
            line_items[meta["cost_col"]] = cost
            subtotal += cost

        # Add tax
        tax = round(subtotal * self.tax_rate, 2)
        total = round(subtotal + tax, 2)

        return {
            "total_bill": total,
            "subtotal": subtotal,
            "sales_tax": tax,
            "line_items": line_items,
            "usage_kwh": kwh
        }

    def calculate_total_bill_pjm(
        self,
        components: dict[str, float],
        kwh: float,
        lmp_da_mwh: Optional[float] = None,
        lmp_rt_mwh: Optional[float] = None,
        congestion_mwh: Optional[float] = None,
        loss_factor: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        PJM M28/M15 Settlement Accounting Bill.
        Uses two-settlement energy charge and loss-adjusted consumption.
        """
        from models.pjm_market_physics import (
            DEFAULT_PJM,
            compute_effective_kwh,
            compute_energy_charge_two_settlement,
            compute_transmission_rate,
            compute_total_bill,
        )

        lf = loss_factor if loss_factor is not None else DEFAULT_PJM.total_loss_factor
        effective_kwh = compute_effective_kwh(kwh, lf)

        # Base rates from components dictionary
        customer_charge = components.get("customer_charge", 0.0)
        distribution_rate = components.get("distribution_rate", 0.0)
        base_transmission = components.get("transmission_rate", 0.0)
        sbc_rate = components.get("sbc_rate", 0.0)
        transition_rate = components.get("transition_rate", 0.0)
        
        # Policy charges
        policy_rate = sbc_rate + transition_rate
        policy_charges = policy_rate * kwh

        # LMP or bgs_rate as proxy (if no LMP provided)
        bgs_rate = components.get("bgs_rate", 0.0)
        da_price = lmp_da_mwh if lmp_da_mwh is not None else (bgs_rate * 1000.0)
        rt_price = lmp_rt_mwh if lmp_rt_mwh is not None else da_price
        
        # Two-settlement energy charge
        settlement = compute_energy_charge_two_settlement(
            effective_kwh=effective_kwh,
            da_price_mwh=da_price,
            rt_price_mwh=rt_price,
            da_fraction=DEFAULT_PJM.da_settlement_fraction
        )
        energy_charge = settlement["total_energy_charge"]

        # Transmission with congestion pass-through
        cong_component = (congestion_mwh / 1000.0) if congestion_mwh is not None else 0.0
        transmission_rate = compute_transmission_rate(base_transmission, cong_component)
        transmission_cost = transmission_rate * kwh

        # Distribution cost
        distribution_cost = distribution_rate * kwh

        # Assemble the bill
        bill_res = compute_total_bill(
            customer_charge=customer_charge,
            energy_charge=energy_charge,
            distribution_cost=distribution_cost,
            transmission_cost=transmission_cost,
            policy_charges=policy_charges,
            tax_rate=self.tax_rate
        )

        # Prepare line items matching expected shape in COMPONENT_TYPES
        line_items = {
            "customer_charge": round(customer_charge, 2),
            "bgs_cost": round(energy_charge, 2),
            "distribution_cost": round(distribution_cost, 2),
            "transmission_cost": round(transmission_cost, 2),
            "sbc_cost": round(sbc_rate * kwh, 2),
            "transition_cost": round(transition_rate * kwh, 2),
        }

        return {
            "total_bill": round(bill_res["total_bill"], 2),
            "subtotal": round(bill_res["subtotal"], 2),
            "sales_tax": round(bill_res["tax"], 2),
            "line_items": line_items,
            "usage_kwh": kwh,
            "effective_kwh": round(effective_kwh, 2),
            "da_energy_charge": round(settlement["da_charge"], 2),
            "rt_deviation_charge": round(settlement["rt_charge"], 2),
            "loss_factor": lf,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  2. SENSITIVITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def sensitivity_analysis(self, component: str, change_pct: float, kwh: Optional[float] = None) -> dict[str, Any]:
        """
        Deterministic + Statistical Sensitivity Analysis using Monte Carlo simulation.
        """
        # Reuse What-If logic for a single component to get Monte Carlo benefits
        sim_res = self.what_if_simulation({component: change_pct}, kwh)
        
        if "error" in sim_res:
            return sim_res

        return {
            "component": component,
            "label": COMPONENT_TYPES[component]["label"],
            "base_bill": sim_res["base_bill"],
            "new_bill": sim_res["new_bill"],
            "absolute_impact": sim_res["total_impact"],
            "percent_impact": round((sim_res["total_impact"] / sim_res["base_bill"]) * 100, 4) if sim_res["base_bill"] else 0.0,
            "elasticity": round((sim_res["total_impact"] / sim_res["base_bill"]) / (change_pct / 100.0), 4) if change_pct != 0 and sim_res["base_bill"] else 0.0,
            "confidence_interval": sim_res["confidence_interval"],
            "component_type": COMPONENT_TYPES[component]["type"],
            "reasoning": COMPONENT_TYPES[component]["reasoning"],
            "details": {
                "change_pct": change_pct,
                "usage_adjustment": sim_res["usage_response"]
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  3. WHAT-IF SIMULATION (V1 and V2)
    # ═══════════════════════════════════════════════════════════════════════════

    def what_if_simulation(self, modifications: dict[str, float], kwh: Optional[float] = None) -> dict[str, Any]:
        """
        Scenario Simulation V1 - backward compatible.
        Delegates to V2 engine but returns the expected shape.
        """
        return self.what_if_simulation_v2(modifications, kwh=kwh)

    def what_if_simulation_v2(self, modifications: dict[str, float], kwh: Optional[float] = None,
                              scenario: Optional[str] = None, n_sim: int = 2000) -> dict[str, Any]:
        """
        Scenario Simulation V2 with learned demand model, weather variations,
        and full multivariate Monte Carlo simulation.
        """
        from api.services.simulation_service_v2 import simulate_v2, build_weather_stats

        billing_df = app_state.get("billing_df")
        if billing_df is None or len(billing_df) == 0:
            return {"error": "Billing data not loaded"}

        feature_df = app_state.get("feature_matrix")
        demand_model = app_state.get("demand_model")
        rate_cov = app_state.get("rate_cov_matrix")
        
        weather_stats = None
        if feature_df is not None:
            weather_stats = build_weather_stats(feature_df)

        try:
            res = simulate_v2(
                modifications=modifications,
                billing_df=billing_df,
                feature_df=feature_df,
                demand_model=demand_model,
                rate_cov=rate_cov,
                weather_stats=weather_stats,
                scenario=scenario,
                kwh_override=kwh,
                n_sim=n_sim
            )
            return res
        except Exception as e:
            logger.exception("Simulation V2 failed")
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════════
    #  4. IMPACT RANKING
    # ═══════════════════════════════════════════════════════════════════════════

    def rank_components(self) -> List[Dict[str, Any]]:
        """
        Rank components by share of total bill and elasticity.
        """
        df = app_state.get("billing_df")
        latest = df.iloc[-1].to_dict()
        total = float(latest.get("total_bill", 1.0))
        
        ranks = []
        for key, meta in COMPONENT_TYPES.items():
            cost = float(latest.get(meta["cost_col"], 0.0))
            share = (cost * (1 + self.tax_rate)) / total
            ranks.append({
                "component": key,
                "label": meta["label"],
                "share_pct": round(share * 100, 2),
                "elasticity": round(share, 4),
                "type": meta["type"],
                "reasoning": meta["reasoning"]
            })
            
        return sorted(ranks, key=lambda x: x["share_pct"], reverse=True)

    # ═══════════════════════════════════════════════════════════════════════════
    #  5. CAUSAL INFERENCE (Advanced Layer)
    # ═══════════════════════════════════════════════════════════════════════════

    def get_causal_impact(self, treatment: str) -> dict[str, Any]:
        """
        Estimate causal effect of a rate component on the total bill using Double ML.
        """
        actual_treatment = "avg_lmp" if treatment == "lmp" else treatment
        causal_service = app_state.get("causal_service")
        
        # If DML service is available, use it
        if causal_service and causal_service.is_fitted:
            res = causal_service.get_causal_impact_legacy(actual_treatment)
            res["treatment"] = treatment
            return res
            
        # Fallback to older dowhy if DML is not available
        try:
            from dowhy import CausalModel
            
            df = app_state.get("billing_df").copy()
            if df is None or len(df) < 24:
                return {"error": "Insufficient data for causal inference (min 24 months)"}

            # If treatment is avg_lmp and not in df, try to merge market data
            if actual_treatment == "avg_lmp" and "avg_lmp" not in df.columns:
                market_df = app_state.get("market_df")
                if market_df is not None:
                    from data_pipeline.features import merge_market_monthly
                    df = merge_market_monthly(df, market_df)

            if actual_treatment not in df.columns:
                return {"error": f"Treatment variable {treatment} not found in billing data"}

            if 'month' in df.columns:
                df['month_num'] = pd.to_datetime(df['month']).dt.month if df['month'].dtype == 'object' else df['month']
            
            model = CausalModel(
                data=df,
                treatment=actual_treatment,
                outcome="total_bill",
                common_causes=["usage_kwh", "month_num"] if 'month_num' in df.columns else ["usage_kwh"]
            )
            
            identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
            estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression",
                test_significance=True
            )
            
            return {
                "treatment": treatment,
                "causal_effect_estimate": round(float(estimate.value), 4),
                "p_value": round(float(estimate.test_stat_significance().get("p_value", 0.0)), 4),
                "interpretation": f"Controlling for usage and seasonality, a $1 unit increase in {treatment} causes an average bill increase of ${round(float(estimate.value), 2)}.",
                "caveat": "Estimated using observational data; results assume no unobserved confounders."
            }
        except ImportError:
            return {"error": "Causal inference services not available"}
        except Exception as e:
            logger.warning(f"Causal inference failed for {treatment}: {e}")
            return {"error": str(e)}

    def get_causal_impact_v2(self, treatment: str) -> dict[str, Any]:
        """
        Get the full rich CausalV2Response from the DML causal model.
        """
        actual_treatment = "avg_lmp" if treatment == "lmp" else treatment
        causal_service = app_state.get("causal_service")
        if causal_service and causal_service.is_fitted:
            res = causal_service.estimate(actual_treatment)
            res = dict(res)
            res["treatment"] = treatment
            return res
        return {"error": "Causal model not fitted"}

bill_impact_engine = BillImpactEngine()
