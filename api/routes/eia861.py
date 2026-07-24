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


@router.get("/utility/{utility_id}/metrics")
@cached(ttl=600)
async def get_utility_metrics(utility_id: int, state: str | None = None):
    """Get peak demand, capacity, and calculated transmission loss percentage for a utility."""
    df = _get_eia861_master_df()
    if df.empty:
        raise HTTPException(500, "EIA-861 master data not loaded")
        
    util_data = df[df["utility_id"] == utility_id]
    if state:
        util_data = util_data[util_data["state"].str.upper() == state.upper()]
        
    if util_data.empty:
        raise HTTPException(404, f"Utility ID {utility_id} not found")
        
    # Get the latest year record
    latest = util_data.sort_values("year").iloc[-1]
    
    # Transmission losses proxy calculation
    peak = float(latest.get("peak_demand", 0) or 0)
    load = float(latest.get("total_load", 0) or 0)
    losses_pct = 5.4  # standard 5.4% average
    if peak > 0 and load > 0:
        losses_pct = round(abs(load - peak) / load * 100, 2)
        if losses_pct > 15.0 or losses_pct < 2.0:
            losses_pct = 5.4
            
    # Fetch ownership type from utility_master
    ownership = "Investor Owned"
    try:
        from database.connection import get_sync_engine
        import pandas as pd
        engine = get_sync_engine()
        q = f"SELECT ownership_type FROM utility_master WHERE eia_utility_id = {utility_id} LIMIT 1"
        res_df = pd.read_sql(q, con=engine)
        if not res_df.empty:
            ownership = res_df.iloc[0]["ownership_type"] or "Investor Owned"
    except Exception:
        pass
        
    # RTO & NERC mapper based on state
    st_upper = (state or latest["state"]).upper()
    rto = "PJM Interconnection"
    nerc = "RFC (ReliabilityFirst)"
    
    if st_upper in ["CA"]:
        rto = "CAISO"
        nerc = "WECC"
    elif st_upper in ["TX"]:
        rto = "ERCOT"
        nerc = "TRE"
    elif st_upper in ["NY"]:
        rto = "NYISO"
        nerc = "NPCC"
    elif st_upper in ["MA", "ME", "NH", "VT", "RI", "CT"]:
        rto = "ISO-NE"
        nerc = "NPCC"
    elif st_upper in ["IL", "IN", "MI", "OH", "KY", "WV", "PA", "DE", "MD", "NJ"]:
        rto = "PJM Interconnection"
        nerc = "RFC (ReliabilityFirst)"
    elif st_upper in ["FL"]:
        rto = "None (Bilateral)"
        nerc = "FRCC"
    elif st_upper in ["WA", "OR", "CO", "AZ", "NM", "UT", "NV", "ID", "WY", "MT"]:
        rto = "None (Bilateral)"
        nerc = "WECC"
    else:
        rto = "MISO"
        nerc = "MRO"
        
    total_cust = int(latest.get("total_customers", 0) or 0)
    sales = float(latest.get("total_sales_mwh", 0) or 0.0)
    avg_cons = round(sales * 1000 / total_cust, 2) if total_cust > 0 else 0.0
            
    return {
        "utility_id": utility_id,
        "utility_name": latest["utility_name"],
        "year": int(latest["year"]),
        "peak_demand_mw": peak,
        "total_load_mwh": load,
        "transmission_losses_pct": losses_pct,
        "demand_response_active": bool(latest.get("demand_response_flag", 0)),
        "dynamic_pricing_active": bool(latest.get("dynamic_pricing_flag", 0)),
        "net_metering_customers": int(latest.get("nm_customers", 0) or 0),
        "net_metering_energy_mwh": float(latest.get("nm_energy_mwh", 0) or 0.0),
        "ownership_type": ownership,
        "rto_iso": rto,
        "nerc_region": nerc,
        "service_territory": f"{st_upper} Service Area",
        "total_customers": total_cust,
        "total_sales_mwh": sales,
        "total_revenue_usd": float(latest.get("total_revenue", 0) or 0.0),
        "avg_price_cents_kwh": round(float(latest.get("avg_price", 0) or 0) / 10, 2),
        "avg_annual_consumption_kwh": avg_cons,
    }


# ── NEW: Operational Benchmarking & Incentive Endpoints ───────────────────

@router.get("/operational-benchmark")
async def get_operational_benchmark(
    state: str = Query("NJ", description="State abbreviation"),
    year: int = Query(None, description="Filter to specific year"),
):
    """Get operational benchmark metrics for utilities in a state."""
    from api.services.eia861_analytics_service import eia861_analytics_service
    data = eia861_analytics_service.get_operational_benchmark(state=state, year=year)
    return {"count": len(data), "data": data}


@router.get("/incentives")
async def get_incentive_programs(
    state: str = Query("NJ"),
    utility_id: int = Query(None, description="Filter to specific utility"),
):
    """Get available incentive programs (Net Metering, DR, TOU) for a state/utility."""
    from api.services.eia861_analytics_service import eia861_analytics_service
    return eia861_analytics_service.get_available_incentives(
        utility_id=utility_id, state=state
    )


@router.get("/tou-savings")
async def estimate_tou_savings(
    usage_kwh: float = Query(750, ge=0),
    peak_pct: float = Query(0.40, ge=0, le=1),
    shift_pct: float = Query(0.15, ge=0, le=1),
    peak_rate: float = Query(0.22, ge=0),
    offpeak_rate: float = Query(0.09, ge=0),
):
    """Estimate savings from switching to a Time-of-Use rate plan."""
    from api.services.eia861_analytics_service import eia861_analytics_service
    return eia861_analytics_service.estimate_tou_savings(
        monthly_usage_kwh=usage_kwh,
        peak_pct=peak_pct,
        shift_pct=shift_pct,
        peak_rate=peak_rate,
        offpeak_rate=offpeak_rate,
    )
