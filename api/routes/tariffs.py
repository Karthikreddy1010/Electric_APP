from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from api.cache import cached
import api.services.tariff_service as ts

router = APIRouter(prefix="/tariffs", tags=["OpenEI Tariffs"])


@router.get("")
@cached(ttl=300)
async def get_tariffs(
    utility_id: Optional[int] = Query(None, description="Filter by utility EIA ID"),
    zip_code: Optional[str] = Query(None, description="Filter by ZIP code"),
    sector: str = Query("Residential", description="Residential, Commercial, or Industrial")
):
    """List tariffs filtered by utility or ZIP code."""
    if zip_code:
        return ts.get_tariff_by_zip(zip_code, sector=sector)
    elif utility_id:
        return ts.get_tariff_by_utility(utility_id, sector=sector)
    else:
        # Return default NJ residential tariffs if no filter
        return ts.get_tariff_by_utility(15477, sector=sector)


@router.get("/default")
@cached(ttl=600)
async def get_default_tariff(
    utility_id: Optional[int] = Query(None, description="EIA utility ID. Defaults to 15477 (PSE&G).")
):
    """Retrieve the default residential tariff for a utility."""
    tariff = ts.get_default_residential_tariff(utility_id)
    if not tariff:
        raise HTTPException(404, f"No default residential tariff found for utility {utility_id or 15477}")
    return tariff


@router.get("/comparison")
@cached(ttl=300)
async def get_tariffs_comparison(
    ids: str = Query(..., description="Comma-separated tariff IDs to compare, e.g. 1,2,3")
):
    """Compare multiple tariffs side-by-side."""
    try:
        tariff_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(400, "Tariff IDs must be a comma-separated list of integers.")
        
    if not tariff_ids:
        raise HTTPException(400, "At least one tariff ID must be specified.")
        
    return ts.compare_tariffs(tariff_ids)


@router.get("/zip/{zipcode}")
@cached(ttl=300)
async def get_tariffs_by_zip(
    zipcode: str,
    sector: str = Query("Residential", description="Sector: Residential, Commercial, or Industrial")
):
    """Get all tariffs available in a ZIP code."""
    res = ts.get_tariff_by_zip(zipcode, sector=sector)
    if not res:
        raise HTTPException(404, f"No tariffs found in ZIP {zipcode} for sector {sector}")
    return res


@router.get("/{utility}")
@cached(ttl=300)
async def get_tariffs_by_utility(
    utility: int,
    sector: str = Query("Residential", description="Sector: Residential, Commercial, or Industrial")
):
    """Get all tariffs for a utility ID."""
    res = ts.get_tariff_by_utility(utility, sector=sector)
    if not res:
        raise HTTPException(404, f"No tariffs found for utility {utility} and sector {sector}")
    return res
