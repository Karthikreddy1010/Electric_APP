"""
GET /geo-lookup       — ZIP to county + estimated bill
GET /geo-all-counties — all 21 NJ counties
"""
from fastapi import APIRouter, HTTPException, Query

from api.state import app_state
from shared.geo_analytics import zip_to_county, estimate_county_bill, get_all_county_estimates

router = APIRouter(tags=["geo"])


@router.get("/geo-lookup")
async def geo_lookup(zip_code: str = Query(..., min_length=5, max_length=5)):
    """Map ZIP code to NJ county and estimate local bill."""
    county = zip_to_county(zip_code)
    if county is None:
        raise HTTPException(404, f"ZIP {zip_code} not found in NJ")
    billing = app_state["billing_df"]
    base_bill = float(billing.iloc[-1]["total_bill"]) if billing is not None else 150.0
    return estimate_county_bill(base_bill, county)


@router.get("/geo-all-counties")
async def geo_all_counties():
    """Get bill estimates for all 21 NJ counties."""
    billing = app_state["billing_df"]
    base_bill = float(billing.iloc[-1]["total_bill"]) if billing is not None else 150.0
    df = get_all_county_estimates(base_bill)
    return df.to_dict(orient="records")
