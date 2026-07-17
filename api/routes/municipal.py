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


@router.get("/rankings")
@cached(ttl=600)
async def get_municipal_rankings(
    county: str | None = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve municipal rankings sorted by total electricity usage."""
    df = app_state.get("community_energy_df")
    if df is None or df.empty:
        raise HTTPException(500, "Community energy dataset not loaded")
        
    sub_df = df
    if county:
        sub_df = df[df["county"].str.lower() == county.lower()]
        
    if sub_df.empty:
        raise HTTPException(404, f"No municipal data found for county '{county}'")
        
    # Get latest year records
    latest_year = sub_df["year"].max()
    year_df = sub_df[sub_df["year"] == latest_year].copy()
    
    # Sort and rank by total electricity consumption
    year_df = year_df.sort_values("total_electricity_kwh", ascending=False).reset_index(drop=True)
    
    rankings = []
    for i, row in year_df.head(limit).iterrows():
        total_kwh = float(row.get("total_electricity_kwh", 0))
        res_kwh = float(row.get("residential_electricity", 0))
        com_kwh = float(row.get("commercial_electricity", 0))
        gas_therms = float(row.get("total_natural_gas_therms", 0))
        
        rankings.append({
            "rank": i + 1,
            "municipality": row["municipality"],
            "county": row["county"],
            "total_electricity_kwh": total_kwh,
            "residential_share_pct": round(res_kwh / max(total_kwh, 1) * 100, 1),
            "commercial_share_pct": round(com_kwh / max(total_kwh, 1) * 100, 1),
            "gas_to_electric_ratio": round(gas_therms * 29.3 / max(total_kwh, 1), 2),  # therms to kWh equivalent
        })
        
    # Aggregate county-level statistics for overview
    county_stats = df.groupby(["year", "county"]).agg(
        total_elec_kwh=("total_electricity_kwh", "sum"),
        total_gas_therms=("total_natural_gas_therms", "sum"),
        muni_count=("municipality", "nunique")
    ).reset_index()
    
    latest_county = county_stats[county_stats["year"] == latest_year].sort_values("total_elec_kwh", ascending=False).to_dict(orient="records")
    
    return {
        "year": int(latest_year),
        "rankings": rankings,
        "county_summary": latest_county
    }

