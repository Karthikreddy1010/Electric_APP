from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.cache import cached
import api.services.service_territory_service as sts

router = APIRouter(prefix="/service-territory", tags=["EIA-861 Service Territory"])


@router.get("")
@cached(ttl=600)
async def get_service_territory(
    state: Optional[str] = Query(None, description="2-letter state code"),
    county: Optional[str] = Query(None, description="County name")
):
    """Query service territory mapping filtered by state and/or county."""
    if county and state:
        return sts.get_county_utilities(state, county)
    elif state:
        return sts.get_state_utilities(state)
    else:
        # Defaults to NJ state summary if no parameters
        return sts.get_state_utilities("NJ")


@router.get("/statistics")
@cached(ttl=300)
async def get_statistics(
    state: Optional[str] = Query(None, description="Optional 2-letter state code filter")
):
    """Aggregate customer counts, sales, demand response, and net metering coverage statistics."""
    return sts.get_service_statistics(state)


@router.get("/state/{state}")
@cached(ttl=600)
async def get_territory_by_state(state: str):
    """Get all utilities and their county coverage count for a state."""
    res = sts.get_state_utilities(state)
    if not res:
        raise HTTPException(404, f"No utilities or service territories found in state {state}")
    return res


@router.get("/county/{county}")
@cached(ttl=600)
async def get_territory_by_county(
    county: str,
    state: str = Query(..., description="2-letter state code context, e.g. NJ")
):
    """Get all utilities serving a specific county."""
    res = sts.get_county_utilities(state, county)
    if not res:
        raise HTTPException(404, f"No utilities found serving {county} County, {state}")
    return res


@router.get("/utility/{utility}")
@cached(ttl=600)
async def get_territory_by_utility(utility: int):
    """Get all counties and states served by a utility."""
    res = sts.get_utility_service_area(utility)
    if not res:
        raise HTTPException(404, f"No service territories found for utility ID {utility}")
    return res
