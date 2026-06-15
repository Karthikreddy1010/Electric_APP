from fastapi import APIRouter, HTTPException
from api.state import app_state
from api.cache import cached
import pandas as pd

router = APIRouter(prefix="/bgs", tags=["bgs"])


@router.get("/rates")
@cached(ttl=600)
async def get_bgs_rates():
    """Expose historical BGS RSCP rates pivoted by utility for plotting."""
    df = app_state.get("bgs_auction_df")
    if df is None or df.empty:
        raise HTTPException(500, "BGS Auction data not loaded")

    # Filter for Residential/Small Commercial default pricing
    rscp = df[df["auction_product_type"].str.contains("RSCP|default|FP|Baseline|Transition", case=False, na=False)].copy()

    def clean_edc(name):
        n = str(name).upper()
        if "PSEG" in n or "PSE&G" in n:
            return "PSE&G"
        if "JCP" in n:
            return "JCP&L"
        if "ACE" in n or "ATLANTIC" in n:
            return "ACE"
        if "RECO" in n or "ROCKLAND" in n:
            return "RECO"
        return name

    rscp["edc_clean"] = rscp["edc"].apply(clean_edc)

    # Pivot to get years as rows and EDC names as columns
    pivoted = rscp.pivot_table(
        index="year",
        columns="edc_clean",
        values="final_price_kwh",
        aggfunc="mean"
    ).reset_index()

    pivoted = pivoted.sort_values("year").replace({float('nan'): None})
    records = pivoted.to_dict(orient="records")
    
    return {
        "count": len(records),
        "data": records
    }
