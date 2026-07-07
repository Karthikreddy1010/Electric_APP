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
    from api.services.tariff_service import get_default_residential_tariff

    sim = PlanSimulator(
        n_simulations=req.n_simulations,
        horizon_months=req.horizon_months,
    )

    historical_usage = billing_df["usage_kwh"].values * (1 + req.usage_growth_pct / 100)
    
    # Add green_pct if available in DataFrame
    plans = plans_df.to_dict(orient="records")
    comparison = sim.compare_plans(plans, historical_usage)

    # Get default tariff for PSE&G (15477)
    pseg_tariff = get_default_residential_tariff(15477)

    results = []
    for _, row in comparison.iterrows():
        provider = row["provider"]
        plan_type = row["plan_type"]
        rate = float(row["rate"])
        
        # Match with plans_df record for green_pct
        matching_plan = next((p for p in plans if p["provider"] == provider), {})
        green_pct = float(matching_plan.get("green_pct", 0.0))

        if "BGS" in provider or "PSE&G" in provider:
            utility_name = "PSE&G"
            tariff_name = pseg_tariff.get("name") if pseg_tariff else "RS - BGS"
            fixed_charge = float(pseg_tariff.get("fixed_charge") or 2.28) if pseg_tariff else 2.28
            energy_charge = float(pseg_tariff.get("energy_rate") or rate) if pseg_tariff else rate
            service_type = pseg_tariff.get("service_type") if pseg_tariff else "Bundled"
            rate_structure = "Residential Service Rate (RS)"
            effective_date = pseg_tariff.get("start_date") if pseg_tariff else "2024-06-01"
        else:
            utility_name = "PSE&G (Delivery)"
            tariff_name = "Third-Party Supplier Plan"
            fixed_charge = 0.0
            energy_charge = rate
            service_type = "Supply Only"
            rate_structure = "Fixed/Variable Supplier Contract"
            effective_date = "2024-01-01"

        results.append(PlanResult(
            provider=provider,
            plan_type=plan_type,
            rate=rate,
            expected_annual_cost=round(row["expected_annual_cost"], 2),
            median_annual_cost=round(row["median_annual_cost"], 2),
            std_annual_cost=round(row["std_annual_cost"], 2),
            p5_annual_cost=round(row["p5_annual_cost"], 2),
            p95_annual_cost=round(row["p95_annual_cost"], 2),
            risk_score=round(row["risk_score"], 1),
            monthly_expected=row["monthly_expected"],
            
            # New integration fields
            utility_name=utility_name,
            tariff_name=tariff_name,
            fixed_charge=fixed_charge,
            energy_charge=energy_charge,
            service_type=service_type,
            rate_structure=rate_structure,
            effective_date=str(effective_date) if effective_date else None,
            green_pct=green_pct,
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

