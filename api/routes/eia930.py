"""
GET /grid — EIA-930 Hourly Balancing Authority Grid Operations & Generation Mix.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api.cache import cached
from api.state import app_state
from api.schemas import (
    GridStatusResponse, HourlyDemandPoint, FuelMixPoint, 
    SubregionDemandPoint, InterchangePoint
)
from database.connection import get_sync_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["EIA-930 Grid"])


def _get_engine():
    return get_sync_engine()


def _ensure_eia930_seeded():
    """Ensure EIA-930 data is populated in database; otherwise run initial seed."""
    engine = _get_engine()
    try:
        count = pd.read_sql("SELECT COUNT(*) as cnt FROM eia930_hourly", con=engine).iloc[0]["cnt"]
        if count == 0:
            logger.info("EIA-930 database tables are empty. Running initial sync on-demand...")
            from database.seed import seed_eia930_initial
            seed_eia930_initial(force=True)
    except Exception as e:
        logger.error(f"Failed to check/seed EIA-930 data: {e}")


@router.get("/grid/current", response_model=GridStatusResponse)
@cached(ttl=300)
async def get_current_grid_status(
    ba: str = Query("PJM", description="Balancing Authority Code, e.g. PJM"),
):
    """Get current grid demand, forecast, net generation, fuel mix, subregion, and interchanges."""
    ba_code = ba.strip().upper()
    _ensure_eia930_seeded()

    engine = _get_engine()

    # 1. Fetch latest demand, forecast, generation totals
    query_totals = text("""
        SELECT period, type_code, value_mwh
        FROM eia930_hourly
        WHERE ba_code = :ba AND period = (
            SELECT MAX(period) FROM eia930_hourly WHERE ba_code = :ba
        )
    """)
    try:
        df_totals = pd.read_sql(query_totals, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying grid totals: {e}")
        raise HTTPException(500, "Database query error")

    if df_totals.empty:
        raise HTTPException(404, f"No grid status data found for BA {ba_code}")

    latest_period = df_totals["period"].max()
    if latest_period:
        if isinstance(latest_period, str):
            try:
                import dateutil.parser
                latest_period = dateutil.parser.parse(latest_period)
            except Exception:
                pass
        latest_period_str = latest_period.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(latest_period, "strftime") else str(latest_period)
    else:
        latest_period_str = ""

    demand = 0.0
    forecast = None
    generation = None

    for _, row in df_totals.iterrows():
        tc = row["type_code"]
        val = float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
        if tc == "D":
            demand = val
        elif tc == "DF":
            forecast = val
        elif tc == "NG":
            generation = val

    # 2. Fetch fuel mix
    query_fuel = text("""
        SELECT fuel_type, fuel_type_name, value_mwh
        FROM eia930_generation
        WHERE ba_code = :ba AND period = (
            SELECT MAX(period) FROM eia930_generation WHERE ba_code = :ba
        )
    """)
    try:
        df_fuel = pd.read_sql(query_fuel, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying fuel mix: {e}")
        df_fuel = pd.DataFrame()

    fuel_mix = []
    if not df_fuel.empty:
        total_gen = df_fuel["value_mwh"].sum()
        for _, row in df_fuel.iterrows():
            val = float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
            pct = (val / total_gen * 100) if total_gen > 0 else 0.0
            fuel_mix.append(FuelMixPoint(
                fuel_type=str(row["fuel_type"]),
                fuel_type_name=str(row["fuel_type_name"]),
                value_mwh=val,
                percentage=round(pct, 2)
            ))
    # Sort fuel mix by generation descending
    fuel_mix = sorted(fuel_mix, key=lambda x: x.value_mwh, reverse=True)

    # 3. Fetch subregions
    query_sub = text("""
        SELECT subba_code, subba_name, value_mwh
        FROM eia930_subregion
        WHERE parent_ba = :ba AND period = (
            SELECT MAX(period) FROM eia930_subregion WHERE parent_ba = :ba
        )
    """)
    try:
        df_sub = pd.read_sql(query_sub, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying subregion demand: {e}")
        df_sub = pd.DataFrame()

    subregions = []
    for _, row in df_sub.iterrows():
        subregions.append(SubregionDemandPoint(
            subba_code=str(row["subba_code"]),
            subba_name=str(row["subba_name"]),
            value_mwh=float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
        ))
    subregions = sorted(subregions, key=lambda x: x.value_mwh, reverse=True)

    # 4. Fetch interchange
    query_ic = text("""
        SELECT to_ba as neighbor, to_ba_name as neighbor_name, value_mwh
        FROM eia930_interchange
        WHERE from_ba = :ba AND period = (
            SELECT MAX(period) FROM eia930_interchange WHERE from_ba = :ba
        )
    """)
    try:
        df_ic = pd.read_sql(query_ic, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying interchanges: {e}")
        df_ic = pd.DataFrame()

    interchange = []
    for _, row in df_ic.iterrows():
        interchange.append(InterchangePoint(
            neighbor=str(row["neighbor"]),
            neighbor_name=str(row["neighbor_name"]),
            net_interchange_mwh=float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
        ))

    return GridStatusResponse(
        ba_code=ba_code,
        ba_name=ba_code, # Default to code if no long name
        latest_period=latest_period_str,
        current_demand_mwh=demand,
        current_forecast_mwh=forecast,
        current_generation_mwh=generation,
        fuel_mix=fuel_mix,
        subregions=subregions,
        interchange=interchange
    )


@router.get("/grid/demand", response_model=list[HourlyDemandPoint])
@cached(ttl=300)
async def get_hourly_demand_series(
    ba: str = Query("PJM", description="Balancing Authority Code"),
    hours: int = Query(24, ge=4, le=168, description="Number of past hours to return"),
):
    """Get time-series hourly grid demand and forecasts for a BA."""
    ba_code = ba.strip().upper()
    _ensure_eia930_seeded()

    engine = _get_engine()
    # Query to fetch latest N hours of data
    query = text("""
        SELECT period, type_code, value_mwh
        FROM eia930_hourly
        WHERE ba_code = :ba AND period >= (
            SELECT MAX(period) - INTERVAL ':hours HOUR' FROM eia930_hourly WHERE ba_code = :ba
        )
        ORDER BY period DESC, type_code
    """)

    try:
        # PostgreSQL doesn't always support direct interval strings in parameter binding, so format it safely
        raw_query = f"""
            SELECT period, type_code, value_mwh
            FROM eia930_hourly
            WHERE ba_code = :ba AND period >= (
                SELECT MAX(period) - INTERVAL '{int(hours)} hours' FROM eia930_hourly WHERE ba_code = :ba
            )
            ORDER BY period DESC, type_code
        """
        df = pd.read_sql(text(raw_query), con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying hourly demand: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        raise HTTPException(404, f"No grid demand history found for BA {ba_code}")

    # Pivot DataFrame so each period has a row with D, DF, NG columns
    pivoted = df.pivot(index="period", columns="type_code", values="value_mwh").reset_index()
    pivoted = pivoted.sort_values("period", ascending=True)

    results = []
    for _, row in pivoted.iterrows():
        p_val = row["period"]
        if p_val:
            if isinstance(p_val, str):
                try:
                    import dateutil.parser
                    p_val = dateutil.parser.parse(p_val)
                except Exception:
                    pass
            p_str = p_val.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(p_val, "strftime") else str(p_val)
        else:
            p_str = ""
        results.append(HourlyDemandPoint(
            period=p_str,
            demand=float(row["D"]) if "D" in row and pd.notna(row["D"]) else 0.0,
            forecast=float(row["DF"]) if "DF" in row and pd.notna(row["DF"]) else None,
            generation=float(row["NG"]) if "NG" in row and pd.notna(row["NG"]) else None,
        ))

    return results


@router.get("/grid/generation-mix", response_model=list[FuelMixPoint])
@cached(ttl=300)
async def get_generation_mix(
    ba: str = Query("PJM", description="Balancing Authority Code"),
):
    """Get the latest fuel mix for a BA (useful for pie charts)."""
    ba_code = ba.strip().upper()
    _ensure_eia930_seeded()

    engine = _get_engine()
    query = text("""
        SELECT fuel_type, fuel_type_name, value_mwh
        FROM eia930_generation
        WHERE ba_code = :ba AND period = (
            SELECT MAX(period) FROM eia930_generation WHERE ba_code = :ba
        )
    """)
    try:
        df = pd.read_sql(query, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying generation mix: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        raise HTTPException(404, f"No generation mix data found for BA {ba_code}")

    total_gen = df["value_mwh"].sum()
    results = []
    for _, row in df.iterrows():
        val = float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
        pct = (val / total_gen * 100) if total_gen > 0 else 0.0
        results.append(FuelMixPoint(
            fuel_type=str(row["fuel_type"]),
            fuel_type_name=str(row["fuel_type_name"]),
            value_mwh=val,
            percentage=round(pct, 2)
        ))

    # Sort descending by generation value
    results = sorted(results, key=lambda x: x.value_mwh, reverse=True)
    return results


@router.get("/grid/subregions", response_model=list[SubregionDemandPoint])
@cached(ttl=300)
async def get_subregions_demand(
    ba: str = Query("PJM", description="Balancing Authority Code"),
):
    """Get latest demand by subregions for a BA."""
    ba_code = ba.strip().upper()
    _ensure_eia930_seeded()

    engine = _get_engine()
    query = text("""
        SELECT subba_code, subba_name, value_mwh
        FROM eia930_subregion
        WHERE parent_ba = :ba AND period = (
            SELECT MAX(period) FROM eia930_subregion WHERE parent_ba = :ba
        )
    """)
    try:
        df = pd.read_sql(query, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying subregions: {e}")
        raise HTTPException(500, "Database query error")

    results = []
    for _, row in df.iterrows():
        results.append(SubregionDemandPoint(
            subba_code=str(row["subba_code"]),
            subba_name=str(row["subba_name"]),
            value_mwh=float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
        ))

    results = sorted(results, key=lambda x: x.value_mwh, reverse=True)
    return results


@router.get("/grid/interchange", response_model=list[InterchangePoint])
@cached(ttl=300)
async def get_interchange_neighbors(
    ba: str = Query("PJM", description="Balancing Authority Code"),
):
    """Get latest interchange flow with neighboring balancing authorities."""
    ba_code = ba.strip().upper()
    _ensure_eia930_seeded()

    engine = _get_engine()
    query = text("""
        SELECT to_ba as neighbor, to_ba_name as neighbor_name, value_mwh
        FROM eia930_interchange
        WHERE from_ba = :ba AND period = (
            SELECT MAX(period) FROM eia930_interchange WHERE from_ba = :ba
        )
    """)
    try:
        df = pd.read_sql(query, con=engine, params={"ba": ba_code})
    except Exception as e:
        logger.error(f"Error querying interchanges: {e}")
        raise HTTPException(500, "Database query error")

    results = []
    for _, row in df.iterrows():
        results.append(InterchangePoint(
            neighbor=str(row["neighbor"]),
            neighbor_name=str(row["neighbor_name"]),
            net_interchange_mwh=float(row["value_mwh"]) if pd.notna(row["value_mwh"]) else 0.0
        ))

    return results


@router.get("/grid/lmp")
@cached(ttl=300)
async def get_day_ahead_lmp(
    zone: str = Query("PSEG", description="Balancing Zone, e.g. PSEG, JCPL, AECO, RECO"),
    days: int = Query(30, ge=1, le=90)
):
    """Retrieve daily aggregated day-ahead LMP node prices for a zone."""
    engine = _get_engine()
    
    query = text("""
        SELECT 
            strftime('%Y-%m-%d', timestamp) as date,
            AVG(price_per_mwh) as avg_lmp,
            MAX(price_per_mwh) as max_lmp,
            MIN(price_per_mwh) as min_lmp
        FROM raw_energy_data
        WHERE region_id = :zone
        GROUP BY date
        ORDER BY date DESC
        LIMIT :days
    """)
    
    try:
        df = pd.read_sql(query, con=engine, params={"zone": zone.upper().strip(), "days": days})
        if df.empty:
            return {"zone": zone, "data": []}
            
        df = df.iloc[::-1].reset_index(drop=True)
        
        records = []
        for _, row in df.iterrows():
            records.append({
                "date": row["date"],
                "avg_lmp": float(row["avg_lmp"]) / 10.0 if row["avg_lmp"] is not None else 0.0,
                "max_lmp": float(row["max_lmp"]) / 10.0 if row["max_lmp"] is not None else 0.0,
                "min_lmp": float(row["min_lmp"]) / 10.0 if row["min_lmp"] is not None else 0.0,
            })
            
        return {"zone": zone, "data": records}
    except Exception as e:
        logger.error(f"Error querying raw energy LMP data: {e}")
        raise HTTPException(500, f"Database error: {e}")


# ── Wholesale PJM LMP Nodal Extensions ────────────────────────────────────────

from data_pipeline.pjm_lmp_fetcher import sync_pjm_lmps


def _ensure_pjm_lmp_seeded():
    """Ensure PJM nodal LMP tables are populated; otherwise run seed on-demand."""
    engine = _get_engine()
    try:
        count = pd.read_sql("SELECT COUNT(*) as cnt FROM pjm_lmp_nodes", con=engine).iloc[0]["cnt"]
        if count == 0:
            logger.info("PJM LMP nodes table is empty. Running seeding on-demand...")
            sync_pjm_lmps(limit_nodes=25, limit_days=14)
    except Exception as e:
        logger.error(f"Failed to check/seed PJM LMP nodes: {e}")


@router.get("/grid/nodes")
@cached(ttl=60)
async def get_grid_nodes():
    """
    Get all grid pricing nodes in PJM with coordinates and latest LMP prices.
    Used to render the interactive regional nodal congestion map.
    """
    _ensure_pjm_lmp_seeded()
    engine = _get_engine()

    query = text("""
        SELECT 
            n.node_id, 
            n.name, 
            n.zone, 
            n.latitude, 
            n.longitude,
            h.timestamp,
            h.total_lmp,
            h.energy_comp,
            h.congestion_comp,
            h.loss_comp
        FROM pjm_lmp_nodes n
        LEFT JOIN pjm_lmp_hourly h ON n.node_id = h.node_id AND h.timestamp = (
            SELECT MAX(timestamp) FROM pjm_lmp_hourly WHERE node_id = n.node_id
        )
    """)

    try:
        df = pd.read_sql(query, con=engine)
        if df.empty:
            return []

        # Convert datetimes to ISO string
        records = []
        for _, row in df.iterrows():
            ts = row.get("timestamp")
            ts_str = ts.isoformat() if (ts is not None and hasattr(ts, "isoformat")) else None
            
            records.append({
                "node_id": str(row["node_id"]),
                "name": str(row["name"]),
                "zone": str(row["zone"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "latest_update": ts_str,
                "total_lmp": float(row["total_lmp"]) if pd.notna(row.get("total_lmp")) else 45.5,
                "energy_comp": float(row["energy_comp"]) if pd.notna(row.get("energy_comp")) else 42.0,
                "congestion_comp": float(row["congestion_comp"]) if pd.notna(row.get("congestion_comp")) else 2.5,
                "loss_comp": float(row["loss_comp"]) if pd.notna(row.get("loss_comp")) else 1.0,
            })
        return records
    except Exception as e:
        logger.error(f"Error querying grid nodes: {e}")
        raise HTTPException(500, f"Database query error: {e}")


@router.get("/grid/nodes/{node_id}/history")
@cached(ttl=60)
async def get_node_lmp_history(node_id: str):
    """
    Get hourly historical LMP price components for a node.
    Used for local time-series visualizations.
    """
    engine = _get_engine()
    query = text("""
        SELECT timestamp, total_lmp, energy_comp, congestion_comp, loss_comp
        FROM pjm_lmp_hourly
        WHERE node_id = :node_id
        ORDER BY timestamp ASC
        LIMIT 336 -- last 14 days of hourly data
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"node_id": node_id})
        if df.empty:
            raise HTTPException(404, f"No history found for node {node_id}")

        records = []
        for _, row in df.iterrows():
            ts = row["timestamp"]
            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            records.append({
                "timestamp": ts_str,
                "total_lmp": float(row["total_lmp"]),
                "energy_comp": float(row["energy_comp"]),
                "congestion_comp": float(row["congestion_comp"]),
                "loss_comp": float(row["loss_comp"]),
            })
        return records
    except Exception as e:
        logger.error(f"Error querying node history: {e}")
        raise HTTPException(500, f"Database query error: {e}")

