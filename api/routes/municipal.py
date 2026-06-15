from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.cache import cached
import pandas as pd

router = APIRouter(prefix="/municipal", tags=["municipal"])


@router.get("/list")
@cached(ttl=600)
async def get_municipalities():
    """Get unique sorted list of NJ municipalities in our community dataset."""
    df = app_state.get("community_energy_df")
    if df is None or df.empty:
        raise HTTPException(500, "Community energy dataset not loaded")
    
    munis = sorted(df["municipality"].dropna().unique().tolist())
    return {"count": len(munis), "municipalities": munis}


@router.get("/benchmark")
@cached(ttl=600)
async def get_municipal_benchmark(
    name: str = Query("Aberdeen Twp", description="NJ Municipality name")
):
    """Retrieve annual energy consumption statistics and utility details for a municipality."""
    comm_df = app_state.get("community_energy_df")
    if comm_df is None or comm_df.empty:
        raise HTTPException(500, "Community energy dataset not loaded")

    # Match name case-insensitively
    muni_data = comm_df[comm_df["municipality"].str.lower() == name.lower()].copy()
    if muni_data.empty:
        muni_data = comm_df[comm_df["municipality"].str.lower().str.contains(name.lower())].copy()

    if muni_data.empty:
        raise HTTPException(404, f"No municipal data found for '{name}'")

    muni_data = muni_data.sort_values("year")

    history = []
    for _, row in muni_data.iterrows():
        history.append({
            "year": int(row["year"]),
            "residential_electricity_kwh": float(row.get("residential_electricity", 0)),
            "commercial_electricity_kwh": float(row.get("commercial_electricity", 0)),
            "industrial_electricity_kwh": float(row.get("industrial_electricity", 0)),
            "total_electricity_kwh": float(row.get("total_electricity_kwh", 0)),
            "residential_natural_gas_therms": float(row.get("residential_natural_gas", 0)),
            "commercial_natural_gas_therms": float(row.get("commercial_natural_gas", 0)),
            "total_natural_gas_therms": float(row.get("total_natural_gas_therms", 0)),
        })

    latest_row = muni_data.iloc[-1]

    return {
        "municipality": latest_row["municipality"],
        "county": latest_row["county"],
        "electric_utility": latest_row.get("electric_utility", "Unknown"),
        "natural_gas_utility": latest_row.get("natural_gas_utility", "Unknown"),
        "history": history
    }
