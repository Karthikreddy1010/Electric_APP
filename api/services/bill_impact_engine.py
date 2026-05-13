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
from sklearn.linear_model import RidgeCV

from api.state import app_state

logger = logging.getLogger(__name__)

# Constants
NJ_SALES_TAX_RATE = 0.06625
DEMAND_ELASTICITY = -0.2  # Typical short-run electricity price elasticity

COMPONENT_TYPES = {
    "bgs_rate": {
        "label": "BGS Supply",
        "type": "variable",
        "cost_col": "bgs_cost",
        "driver": "market",
        "reasoning": "High impact because it is the largest portion of the supply stack and scales directly with usage (kWh).",
    },
    "transmission_rate": {
        "label": "Transmission Charge",
        "type": "variable",
        "cost_col": "transmission_cost",
        "driver": "market",
        "reasoning": "Significant impact scaling with usage; driven by regional grid maintenance and congestion.",
    },
    "distribution_rate": {
        "label": "Distribution Charge",
        "type": "variable",
        "cost_col": "distribution_cost",
        "driver": "infrastructure",
        "reasoning": "Stable but substantial impact proportional to consumption; funds local delivery network.",
    },
    "sbc_rate": {
        "label": "Societal Benefits Charge",
        "type": "variable",
        "cost_col": "sbc_cost",
        "driver": "policy",
        "reasoning": "Lower impact scaling with usage; funds energy efficiency and social programs.",
    },
    "nug_rate": {
        "label": "Non-Utility Generation",
        "type": "variable",
        "cost_col": "nug_cost",
        "driver": "regulatory",
        "reasoning": "Scaling impact; tied to legacy power purchase agreements.",
    },
}

class BillImpactEngine:
    def __init__(self):
        self.tax_rate = NJ_SALES_TAX_RATE

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. DETERMINISTIC LAYER (Ground Truth)
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate_total_bill(self, components: dict[str, float], kwh: float) -> dict[str, Any]:
        """
        Calculates the total bill using the deterministic summation identity.
        """
        line_items = {}
        subtotal = 0.0

        for key, meta in COMPONENT_TYPES.items():
            rate = components.get(key, 0.0)
            cost = round(rate * kwh, 2)
            line_items[meta["cost_col"]] = cost
            subtotal += cost

        # Add fixed components if any (none in current simplified model besides BGS/etc)
        # Handle adjustments like DR credit if present
        dr_credit = components.get("dr_credit", 0.0)
        line_items["dr_credit"] = dr_credit
        subtotal += dr_credit

        tax = round(subtotal * self.tax_rate, 2)
        total = round(subtotal + tax, 2)

        return {
            "total_bill": total,
            "subtotal": subtotal,
            "sales_tax": tax,
            "line_items": line_items,
            "usage_kwh": kwh
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  2. SENSITIVITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def sensitivity_analysis(self, component: str, change_pct: float, kwh: Optional[float] = None) -> dict[str, Any]:
        """
        Computes deterministic + analytical impact of changing one component.
        """
        df = app_state.get("billing_df")
        if df is None or df.empty:
            return {"error": "No billing data available"}

        latest = df.iloc[-1].to_dict()
        usage = kwh if kwh is not None else float(latest.get("usage_kwh", 750))
        
        if component not in COMPONENT_TYPES:
            return {"error": f"Invalid component: {component}"}

        # Base components
        base_comps = {k: float(latest.get(k, 0.0)) for k in COMPONENT_TYPES.keys()}
        base_bill = self.calculate_total_bill(base_comps, usage)

        # Modified component
        mod_comps = dict(base_comps)
        orig_rate = base_comps[component]
        mod_comps[component] = orig_rate * (1 + change_pct / 100.0)
        
        new_bill = self.calculate_total_bill(mod_comps, usage)

        abs_impact = round(new_bill["total_bill"] - base_bill["total_bill"], 2)
        pct_impact = round((abs_impact / base_bill["total_bill"]) * 100, 4) if base_bill["total_bill"] else 0.0
        
        # Elasticity (Calculated mathematically: share of bill)
        # Elasticity = (dTotal/Total) / (dRate/Rate)
        elasticity = round(pct_impact / change_pct, 4) if change_pct != 0 else 0.0

        return {
            "component": component,
            "label": COMPONENT_TYPES[component]["label"],
            "base_bill": base_bill["total_bill"],
            "new_bill": new_bill["total_bill"],
            "absolute_impact": abs_impact,
            "percent_impact": pct_impact,
            "elasticity": elasticity,
            "component_type": COMPONENT_TYPES[component]["type"],
            "reasoning": COMPONENT_TYPES[component]["reasoning"],
            "details": {
                "original_rate": round(orig_rate, 6),
                "new_rate": round(mod_comps[component], 6),
                "usage_used": usage
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    #  3. WHAT-IF SIMULATION
    # ═══════════════════════════════════════════════════════════════════════════

    def what_if_simulation(self, modifications: dict[str, float], kwh: Optional[float] = None) -> dict[str, Any]:
        """
        Simulate bill changes for multiple component modifications.
        Includes demand elasticity (optional/analytical).
        """
        df = app_state.get("billing_df")
        latest = df.iloc[-1].to_dict()
        usage = kwh if kwh is not None else float(latest.get("usage_kwh", 750))

        base_comps = {k: float(latest.get(k, 0.0)) for k in COMPONENT_TYPES.keys()}
        base_bill = self.calculate_total_bill(base_comps, usage)

        mod_comps = dict(base_comps)
        for comp, pct in modifications.items():
            if comp in mod_comps:
                mod_comps[comp] *= (1 + pct / 100.0)

        # Analytical Demand Elasticity: If avg price changes, usage might change
        # Avg Price = Total Bill / Usage
        base_avg_price = base_bill["total_bill"] / usage
        temp_new_bill = self.calculate_total_bill(mod_comps, usage)
        new_avg_price = temp_new_bill["total_bill"] / usage
        
        price_change_pct = (new_avg_price - base_avg_price) / base_avg_price
        new_usage = usage * (1 + price_change_pct * DEMAND_ELASTICITY)
        
        # Final result with demand response
        final_bill = self.calculate_total_bill(mod_comps, new_usage)

        return {
            "base_bill": base_bill["total_bill"],
            "new_bill": final_bill["total_bill"],
            "total_impact": round(final_bill["total_bill"] - base_bill["total_bill"], 2),
            "usage_response": round(new_usage - usage, 2),
            "contributions": {
                COMPONENT_TYPES[k]["label"]: round((mod_comps[k] * new_usage * (1+self.tax_rate)), 2)
                for k in mod_comps
            }
        }

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
        Estimate causal effect of a rate component on the total bill using DoWhy.
        This distinguishes correlation from causation by controlling for confounders.
        """
        try:
            from dowhy import CausalModel
            
            df = app_state.get("billing_df").copy()
            if df is None or len(df) < 24:
                return {"error": "Insufficient data for causal inference (min 24 months)"}

            # Define causal variables
            # Treatment: component rate
            # Outcome: total bill
            # Confounders: usage_kwh, weather (if available)
            
            # For simplicity, we use usage_kwh as the primary confounder
            model = CausalModel(
                data=df,
                treatment=treatment,
                outcome="total_bill",
                common_causes=["usage_kwh"]
            )
            
            # Identification
            identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
            
            # Estimation (using Linear Regression as a baseline, but DML is preferred)
            # Since we have small data, Linear Regression with controls is safer than complex DML
            estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression",
                test_significance=True
            )
            
            return {
                "treatment": treatment,
                "causal_effect_estimate": round(float(estimate.value), 4),
                "p_value": round(float(estimate.test_stat_significance().get("p_value", 0.0)), 4),
                "interpretation": f"Controlling for usage, a $1 unit increase in {treatment} causes an average bill increase of ${round(float(estimate.value), 2)}.",
                "caveat": "Estimated using observational data; results assume no unobserved confounders."
            }
        except ImportError:
            return {"error": "DoWhy not installed for causal inference"}
        except Exception as e:
            logger.warning(f"Causal inference failed for {treatment}: {e}")
            return {"error": str(e)}

bill_impact_engine = BillImpactEngine()
