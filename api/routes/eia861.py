from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.cache import cached
import pandas as pd

router = APIRouter(prefix="/eia861", tags=["eia861"])


import logging

logger = logging.getLogger(__name__)

def _get_eia861_master_df() -> pd.DataFrame:
    df = app_state.get("eia861_master_df")
    if df is None or df.empty:
        try:
            from database.connection import get_sync_engine
            engine = get_sync_engine()
            df = pd.read_sql("SELECT * FROM eia861_master", con=engine)
            if not df.empty:
                app_state["eia861_master_df"] = df
                logger.info(f"Loaded eia861_master_df from database: {len(df)} rows")
            else:
                logger.warning("eia861_master table is empty")
        except Exception as e:
            logger.error(f"Error reading eia861_master from database: {e}")
            df = pd.DataFrame()
    return df


@router.get("/utilities")
@cached(ttl=600)
async def get_utilities(state: str | None = None):
    """Get unique utilities, optionally filtered by state."""
    df = _get_eia861_master_df()
    if df.empty:
        raise HTTPException(500, "EIA-861 master data not loaded")

    sub_df = df
    if state:
        sub_df = df[df["state"].str.upper() == state.upper()]

    # Get unique (utility_id, utility_name, state)
    utils = sub_df[["utility_id", "utility_name", "state"]].drop_duplicates(subset=["utility_id", "state"]).sort_values("utility_name")
    
    # Replace NaN name/state with placeholders
    utils = utils.fillna("Unknown")
    
    records = utils.to_dict(orient="records")
    return {"count": len(records), "utilities": records}


@router.get("/utility/{utility_id}")
@cached(ttl=600)
async def get_utility_detail(utility_id: int, state: str | None = None):
    """Get historical data for a specific utility, optionally filtered by state."""
    df = _get_eia861_master_df()
    if df.empty:
        raise HTTPException(500, "EIA-861 master data not loaded")

    util_data = df[df["utility_id"] == utility_id]
    if state:
        util_data = util_data[util_data["state"].str.upper() == state.upper()]
        
    util_data = util_data.sort_values("year")
    if util_data.empty:
        raise HTTPException(404, f"Utility ID {utility_id} not found")

    # Clean NaN values for json serialization
    util_data = util_data.replace({float('nan'): None})
    records = util_data.to_dict(orient="records")
    
    return {
        "utility_id": utility_id,
        "utility_name": records[0]["utility_name"],
        "state": records[0]["state"],
        "history": records
    }


@router.get("/states")
@cached(ttl=600)
async def get_states():
    """Get list of unique states in EIA-861 data."""
    df = _get_eia861_master_df()
    if df.empty:
        raise HTTPException(500, "EIA-861 master data not loaded")
    
    states = sorted(df["state"].dropna().unique().tolist())
    return {"count": len(states), "states": states}
