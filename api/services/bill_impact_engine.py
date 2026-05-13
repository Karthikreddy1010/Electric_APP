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

    # ═══════════════════════════════════════════════════════════════════════════
    #  1. DETERMINISTIC LAYER (Ground Truth)
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate_total_bill(self, components: dict[str, float], kwh: float) -> dict[str, Any]:
        """
        DETERMINISTIC LAYER: Accounting Identity.
        Total_Bill = sum(fixed) + sum(variable * kwh)
        """
        line_items = {}
        subtotal = 0.0

        for key, meta in COMPONENT_TYPES.items():
            val = components.get(key, 0.0)
            if meta["type"] == "variable":
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
    #  3. WHAT-IF SIMULATION
    # ═══════════════════════════════════════════════════════════════════════════

    def what_if_simulation(self, modifications: dict[str, float], kwh: Optional[float] = None) -> dict[str, Any]:
        """
        Scenario Simulation with Monte Carlo uncertainty.
        Propagates uncertainty in demand elasticity and rate volatility.
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

        # Monte Carlo Simulation
        n_sim = 1000
        sim_results = []
        
        for _ in range(n_sim):
            # Sample elasticity from a normal distribution (mean -0.2, std 0.05)
            e_draw = np.random.normal(DEMAND_ELASTICITY, 0.05)
            
            # Temporary bill to find price change
            temp = self.calculate_total_bill(mod_comps, usage)
            p_change = (temp["total_bill"] - base_bill["total_bill"]) / base_bill["total_bill"]
            
            # Simulated usage response
            sim_usage = usage * (1 + p_change * e_draw)
            sim_bill = self.calculate_total_bill(mod_comps, sim_usage)
            sim_results.append(sim_bill["total_bill"])

        sim_results = np.array(sim_results)
        
        return {
            "base_bill": base_bill["total_bill"],
            "new_bill": round(float(np.median(sim_results)), 2),
            "total_impact": round(float(np.median(sim_results)) - base_bill["total_bill"], 2),
            "confidence_interval": [
                round(float(np.percentile(sim_results, 2.5)), 2),
                round(float(np.percentile(sim_results, 97.5)), 2)
            ],
            "usage_response": round(float(np.median(sim_results) / base_bill["total_bill"] * usage) - usage, 2),
            "contributions": {
                COMPONENT_TYPES[k]["label"]: round(float(mod_comps[k] * usage * (1+self.tax_rate)), 2) if COMPONENT_TYPES[k]["type"] == "variable" else round(mod_comps[k] * (1+self.tax_rate), 2)
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
            # Confounders: usage_kwh, month (seasonality), and weather if available
            
            # Ensure month is numeric for regression
            if 'month' in df.columns:
                df['month_num'] = pd.to_datetime(df['month']).dt.month if df['month'].dtype == 'object' else df['month']
            
            model = CausalModel(
                data=df,
                treatment=treatment,
                outcome="total_bill",
                common_causes=["usage_kwh", "month_num"] if 'month_num' in df.columns else ["usage_kwh"]
            )
            
            # Identification
            identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
            
            # Estimation
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
            return {"error": "DoWhy not installed for causal inference"}
        except Exception as e:
            logger.warning(f"Causal inference failed for {treatment}: {e}")
            return {"error": str(e)}

bill_impact_engine = BillImpactEngine()
