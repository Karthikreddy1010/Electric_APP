"""
Plan Simulation Model: Monte Carlo simulation for electricity plan comparison.
Compares fixed-rate vs variable-rate plans under usage/price uncertainty.
"""
import numpy as np
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PlanSimulator:
    """
    Monte Carlo simulator for comparing electricity supply plans.
    
    Simulates future costs under:
    - Usage uncertainty (seasonal patterns + random variation)
    - Price uncertainty (variable rate volatility, market shocks)
    - Regulatory risk (SBC/rider changes)
    """
    
    def __init__(self, n_simulations: int = 10_000, horizon_months: int = 12, seed: int = 42):
        self.n_simulations = n_simulations
        self.horizon_months = horizon_months
        self.seed = seed
    
    def simulate_usage(self, historical_usage: np.ndarray) -> np.ndarray:
        """
        Simulate future monthly usage using historical patterns.
        Returns: (n_simulations, horizon_months) array.
        """
        rng = np.random.default_rng(self.seed)
        
        # Fit monthly means and stds from historical data
        monthly_stats = {}
        for month in range(1, 13):
            # Assume historical_usage has at least some data
            idx = np.arange(len(historical_usage)) % 12 == (month - 1)
            if idx.sum() > 0:
                vals = historical_usage[idx]
                monthly_stats[month] = {"mean": vals.mean(), "std": vals.std()}
            else:
                monthly_stats[month] = {"mean": 750, "std": 80}
        
        # Generate simulated usage paths
        simulated = np.zeros((self.n_simulations, self.horizon_months))
        for m in range(self.horizon_months):
            month = (m % 12) + 1
            stats = monthly_stats[month]
            simulated[:, m] = rng.normal(stats["mean"], stats["std"],
                                         self.n_simulations)
        
        return np.clip(simulated, 200, 3000)
    
    def simulate_variable_rate(self, base_rate: float, volatility: float,
                                trend: float = 0.002,
                                seed_offset: int = 0) -> np.ndarray:
        """
        Simulate variable rate paths using geometric Brownian motion.
        seed_offset should differ per plan so each plan gets a unique simulation.
        Returns: (n_simulations, horizon_months) array.
        """
        rng = np.random.default_rng(self.seed + 1 + seed_offset)
        dt = 1/12  # monthly steps
        rates = np.zeros((self.n_simulations, self.horizon_months))
        rates[:, 0] = base_rate

        for t in range(1, self.horizon_months):
            z = rng.standard_normal(self.n_simulations)
            rates[:, t] = rates[:, t-1] * np.exp(
                (trend - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * z
            )
        
        return np.clip(rates, 0.03, 0.30)
    
    def compute_plan_costs(self, plan: dict, usage: np.ndarray,
                            variable_rates: np.ndarray = None,
                            seed_offset: int = 0) -> dict:
        """
        Compute total cost distribution for a plan.
        
        Args:
            plan: dict with keys: provider, type, rate, term_months, 
                  etf, green_pct, volatility
            usage: (n_simulations, horizon_months) usage array
            variable_rates: pre-simulated variable rate paths (if variable plan)
            seed_offset: unique offset per plan for independent RNG streams
        
        Returns:
            dict with cost statistics and distribution
        """
        if plan["type"] == "fixed":
            # Fixed rate: deterministic per-kWh, uncertainty only from usage
            supply_cost = usage * plan["rate"]
        else:
            # Variable rate: use simulated rate paths
            if variable_rates is None:
                variable_rates = self.simulate_variable_rate(
                    plan["rate"], plan.get("volatility", 0.015),
                    seed_offset=seed_offset,
                )
            supply_cost = usage * variable_rates[:, :self.horizon_months]
        
        # Add delivery charges (~$0.055/kWh for NJ PSE&G)
        delivery_rate = 0.055
        delivery_cost = usage * delivery_rate
        
        # Add riders/SBC (~$0.008/kWh)
        rider_cost = usage * 0.008
        
        # Total per-month cost
        monthly_total = supply_cost + delivery_cost + rider_cost
        
        # Tax (NJ 6.625%)
        monthly_total *= 1.06625
        
        # Annual total cost
        annual_total = monthly_total.sum(axis=1)
        
        return {
            "provider": plan["provider"],
            "plan_type": plan["type"],
            "rate": plan["rate"],
            "expected_annual_cost": float(np.mean(annual_total)),
            "median_annual_cost": float(np.median(annual_total)),
            "std_annual_cost": float(np.std(annual_total)),
            "p5_annual_cost": float(np.percentile(annual_total, 5)),
            "p95_annual_cost": float(np.percentile(annual_total, 95)),
            "worst_case": float(np.percentile(annual_total, 99)),
            "best_case": float(np.percentile(annual_total, 1)),
            "monthly_expected": np.mean(monthly_total, axis=0).tolist(),
            "var_95": float(np.percentile(annual_total, 95) - np.mean(annual_total)),
        }
    
    def compare_plans(self, plans: list[dict], 
                      historical_usage: np.ndarray) -> pd.DataFrame:
        """
        Run Monte Carlo comparison across all plans.
        Returns DataFrame with plan comparison metrics.
        """
        usage = self.simulate_usage(historical_usage)
        
        results = []
        for idx, plan in enumerate(plans):
            result = self.compute_plan_costs(plan, usage, seed_offset=idx)
            results.append(result)
            logger.info(f"  {plan['provider']}: ${result['expected_annual_cost']:.0f}/yr "
                       f"(±${result['std_annual_cost']:.0f})")
        
        comparison = pd.DataFrame(results)
        comparison["risk_score"] = (
            comparison["std_annual_cost"] / comparison["expected_annual_cost"] * 100
        ).round(1)
        comparison = comparison.sort_values("expected_annual_cost")
        
        return comparison
    
    def sensitivity_analysis(self, plan: dict, historical_usage: np.ndarray,
                              usage_change_pcts: list[float] = None) -> dict:
        """
        Analyze how cost changes with usage levels (e.g., ±10%, ±20%).
        """
        if usage_change_pcts is None:
            usage_change_pcts = [-20, -10, 0, 10, 20]
        
        base_usage = self.simulate_usage(historical_usage)
        results = {}
        
        for pct in usage_change_pcts:
            adjusted_usage = base_usage * (1 + pct/100)
            cost = self.compute_plan_costs(plan, adjusted_usage)
            results[f"{pct:+d}%"] = {
                "expected_cost": cost["expected_annual_cost"],
                "risk": cost["std_annual_cost"],
            }
        
        return {"plan": plan["provider"], "sensitivity": results}
