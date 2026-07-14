"""
Monte Carlo Plan Simulator for energy bill risk evaluation and plan comparisons.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any


class PlanSimulator:
    """
    Monte Carlo simulator for evaluating energy plan costs under usage and rate volatility.
    """

    def __init__(self, n_simulations: int = 1000, horizon_months: int = 12, random_state: int = 42):
        self.n_simulations = n_simulations
        self.horizon_months = horizon_months
        self.rng = np.random.default_rng(random_state)

    def simulate_usage(self, historical_usage: np.ndarray) -> np.ndarray:
        """
        Simulate monthly usage trajectories (shape: n_simulations x horizon_months)
        based on mean/std of historical usage.
        """
        if len(historical_usage) >= self.horizon_months:
            full_years = len(historical_usage) // 12
            reshaped = historical_usage[: full_years * 12].reshape(full_years, 12)
            monthly_mean = reshaped.mean(axis=0)[: self.horizon_months]
            monthly_std = reshaped.std(axis=0)[: self.horizon_months]
            monthly_std = np.maximum(monthly_std, monthly_mean * 0.05)
        else:
            monthly_mean = np.resize(historical_usage, self.horizon_months)
            monthly_std = monthly_mean * 0.1

        noise = self.rng.normal(0, 1, size=(self.n_simulations, self.horizon_months))
        simulated = monthly_mean + noise * monthly_std
        return np.maximum(simulated, 200.0)

    def simulate_variable_rate(self, base_rate: float, volatility: float) -> np.ndarray:
        """
        Simulate rate random walks for variable rate plans.
        """
        if volatility == 0:
            return np.full((self.n_simulations, self.horizon_months), base_rate)

        shocks = self.rng.normal(0, volatility, size=(self.n_simulations, self.horizon_months))
        rates = base_rate * np.exp(np.cumsum(shocks, axis=1))
        return np.maximum(rates, 0.03)

    def compare_plans(self, plans: List[Dict[str, Any]], historical_usage: np.ndarray) -> pd.DataFrame:
        """
        Compare energy plans using Monte Carlo simulations.
        """
        simulated_usage = self.simulate_usage(historical_usage)
        results = []

        for plan in plans:
            rate = plan.get("rate", 0.10)
            volatility = plan.get("volatility", 0.0)
            plan_type = plan.get("type", "fixed")

            if plan_type == "variable" and volatility > 0:
                simulated_rates = self.simulate_variable_rate(rate, volatility)
            else:
                simulated_rates = np.full((self.n_simulations, self.horizon_months), rate)

            annual_costs = (simulated_usage * simulated_rates).sum(axis=1)

            mean_cost = float(np.mean(annual_costs))
            std_cost = float(np.std(annual_costs))
            p5 = float(np.percentile(annual_costs, 5))
            p95 = float(np.percentile(annual_costs, 95))
            risk_score = float(std_cost / mean_cost) if mean_cost > 0 else 0.0

            results.append({
                "provider": plan.get("provider", "Unknown"),
                "plan_type": plan_type,
                "base_rate": rate,
                "volatility": volatility,
                "expected_annual_cost": round(mean_cost, 2),
                "std_annual_cost": round(std_cost, 2),
                "p5_cost": round(p5, 2),
                "p95_cost": round(p95, 2),
                "risk_score": round(risk_score, 4),
            })

        return pd.DataFrame(results)
