"""
Forecast Features Generation pipeline.
Combines historical billing usage with the new HistoricalUtilityTariff engine 
to build robust training datasets for the forecast engine.
"""
import pandas as pd
from sqlalchemy.orm import Session
from database.connection import get_sync_session
from api.services.tariff_lookup_service import get_active_tariff

def generate_forecast_features(utility_code: str, schedule: str, base_usage_kwh: pd.Series) -> pd.DataFrame:
    """
    Generate future bill projections based on the active tariff for the given utility and schedule.
    This creates a base dataset for the forecasting model, using exact known current rates
    rather than purely autoregressive predictions on the total bill cost.
    """
    with get_sync_session() as session:
        active_rates = get_active_tariff(session, utility_code, schedule)
        
    if not active_rates:
        raise ValueError(f"No active rates found for {utility_code} - {schedule}")
        
    # Calculate known fixed and volumetric components
    fixed_charge = sum(r["rate"] for r in active_rates if r["category"] == "fixed")
    volumetric_rate = sum(r["rate"] for r in active_rates if r["category"] == "volumetric")
    
    # Generate the dataset
    df = pd.DataFrame({"projected_usage_kwh": base_usage_kwh})
    
    # Calculate baseline costs assuming current rates hold flat
    df["projected_fixed_cost"] = fixed_charge
    df["projected_volumetric_cost"] = df["projected_usage_kwh"] * volumetric_rate
    df["projected_total_cost"] = df["projected_fixed_cost"] + df["projected_volumetric_cost"]
    
    return df

if __name__ == "__main__":
    # Example usage during ETL or scheduled task
    usage_scenarios = pd.Series([500.0, 600.0, 700.0, 1000.0, 1200.0])
    df = generate_forecast_features("PSEG", "RS", usage_scenarios)
    print("Forecast Feature Projections:")
    print(df)
