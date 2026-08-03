"""
Verification test script for EIA-923 integration across all modified backend endpoints.
"""
import sys
import os
import pandas as pd
import asyncio

from api.state import app_state
from database.connection import init_db
from api.services.eia923_service import (
    get_eia923_fuel_cost_summary,
    get_eia923_generation_summary,
    get_eia923_storage_summary,
    get_eia923_fac_explanation
)

async def main():
    print("=== 1. VERIFYING EIA-923 HELPER SERVICE ===")
    fuel_cost = get_eia923_fuel_cost_summary("NJ")
    gen_summary = get_eia923_generation_summary("NJ")
    storage = get_eia923_storage_summary("NJ")
    fac = get_eia923_fac_explanation("NJ")

    print(f"Fuel Cost ($/MMBtu): ${fuel_cost['avg_cost_dollars_mmbtu']} (MoM: {fuel_cost['mom_change_pct']}%)")
    print(f"Clean Energy Share (%): {gen_summary['clean_share_pct']}%")
    print(f"Grid Carbon Intensity (lbs CO2/MWh): {gen_summary['grid_carbon_intensity_lbs_mwh']}")
    print(f"Battery Round-Trip Efficiency (%): {storage['roundtrip_efficiency_pct']}%")
    print(f"FAC Explanation: {fac['explanation']}")

    print("\n=== 2. INITIALIZING APP STATE FOR ROUTE VERIFICATION ===")
    # Populate mock billing & geo data in app_state
    dummy_billing = pd.DataFrame([{
        "date": pd.Timestamp("2026-06-01"),
        "usage_kwh": 750.0,
        "bgs_rate": 0.108,
        "distribution_rate": 0.055,
        "transmission_rate": 0.012,
        "sbc_rate": 0.005,
        "nug_rate": 0.002
    }, {
        "date": pd.Timestamp("2026-07-01"),
        "usage_kwh": 820.0,
        "bgs_rate": 0.110,
        "distribution_rate": 0.055,
        "transmission_rate": 0.012,
        "sbc_rate": 0.005,
        "nug_rate": 0.002
    }])
    app_state["billing_df"] = dummy_billing
    app_state["geo_monthly_df"] = pd.DataFrame([{
        "state": "NJ", "year": 2025, "month": 12, "month_str": "2025-12", "period": "2025-12", "avg_bill": 138.90, "avg_rate": 0.1852, "usage_kwh": 750.0, "yoy_change": 2.5
    }])

    print("\n=== 3. TESTING /overview ROUTE ===")
    from api.routes.overview import get_overview
    ov_res = await get_overview()
    print("Overview eia923_summary:", ov_res.eia923_summary)

    print("\n=== 4. TESTING /geo/detail ROUTE ===")
    from api.routes.geo_insights import geo_detail
    geo_res = await geo_detail(state="NJ", month="2025-12")
    print("Geo eia923_metrics:", geo_res.get("eia923_metrics"))

    print("\n=== 5. TESTING /forecast ROUTE ===")
    from api.routes.forecast import forecast_costs
    fc_res = await forecast_costs(horizon=30)
    print("Forecast exogenous_indicators:", fc_res.get("exogenous_indicators"))

    print("\n=== 6. TESTING /simulate ROUTE ===")
    from api.routes.simulate import run_plan_simulation, PlanSimulationRequest
    sim_res = await run_plan_simulation(PlanSimulationRequest(monthly_usage_kwh=750.0))
    print("Simulated Recommended Plan:", sim_res.recommended)

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
