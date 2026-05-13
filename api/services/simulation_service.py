"""
Simulation Service — wraps PlanSimulator for /plan-simulation.
"""
import pandas as pd
from api.schemas import PlanSimRequest, PlanSimResponse, PlanResult


def run_plan_simulation(
    plans_df: pd.DataFrame,
    billing_df: pd.DataFrame,
    req: PlanSimRequest,
) -> PlanSimResponse:
    """Execute Monte Carlo simulation and return structured response."""
    from models.simulation_model import PlanSimulator

    sim = PlanSimulator(
        n_simulations=req.n_simulations,
        horizon_months=req.horizon_months,
    )

    historical_usage = billing_df["usage_kwh"].values * (1 + req.usage_growth_pct / 100)
    plans = plans_df.to_dict(orient="records")
    comparison = sim.compare_plans(plans, historical_usage)

    results = []
    for _, row in comparison.iterrows():
        results.append(PlanResult(
            provider=row["provider"],
            plan_type=row["plan_type"],
            rate=row["rate"],
            expected_annual_cost=round(row["expected_annual_cost"], 2),
            median_annual_cost=round(row["median_annual_cost"], 2),
            std_annual_cost=round(row["std_annual_cost"], 2),
            p5_annual_cost=round(row["p5_annual_cost"], 2),
            p95_annual_cost=round(row["p95_annual_cost"], 2),
            risk_score=round(row["risk_score"], 1),
            monthly_expected=row["monthly_expected"],
        ))

    default_cost = comparison[comparison["provider"].str.contains("BGS|PSE&G")]
    default_annual = (
        default_cost["expected_annual_cost"].values[0]
        if len(default_cost) > 0
        else results[0].expected_annual_cost
    )
    best = comparison.iloc[0]

    return PlanSimResponse(
        comparison=results,
        recommended=best["provider"],
        savings_vs_default=round(default_annual - best["expected_annual_cost"], 2),
    )
