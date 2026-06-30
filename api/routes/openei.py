"""
GET /utility — OpenEI Utility Service Territories lookup, search, and rate comparison.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api.cache import cached
from api.state import app_state
from api.schemas import UtilityLookupResponse, UtilityDetailResponse, UtilityCompareResponse
from database.connection import get_sync_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["OpenEI Utility"])


def _get_engine():
    return get_sync_engine()


@router.get("/utility/lookup", response_model=list[UtilityLookupResponse])
@cached(ttl=3600)
async def lookup_utility_by_zip(
    zip: str = Query(..., description="5-digit ZIP code"),
):
    """Lookup utilities and average rates for a given ZIP code."""
    zip_code = zip.strip().zfill(5)
    engine = _get_engine()

    query = text("""
        SELECT 
            m.eia_utility_id,
            m.utility_name,
            m.state,
            m.ownership_type,
            z.zip_code,
            z.service_type,
            r.residential_rate,
            r.commercial_rate,
            r.industrial_rate
        FROM utility_zip_lookup z
        JOIN utility_master m ON z.eia_utility_id = m.eia_utility_id AND z.state = m.state
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        WHERE z.zip_code = :zip_code
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"zip_code": zip_code})
    except Exception as e:
        logger.error(f"Error querying utility by ZIP: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        raise HTTPException(404, f"No utilities found for ZIP code {zip_code}")

    results = []
    for _, row in df.iterrows():
        results.append(UtilityLookupResponse(
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]),
            state=str(row["state"]),
            ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
            zip_code=str(row["zip_code"]),
            service_type=str(row["service_type"]) if pd.notna(row.get("service_type")) else None,
            residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
            commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
            industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
        ))

    return results


@router.get("/utility/search", response_model=list[UtilityDetailResponse])
@cached(ttl=600)
async def search_utilities_by_name(
    name: str = Query(..., description="Part of the utility name"),
    state: Optional[str] = Query(None, description="Optional 2-letter state filter"),
):
    """Search for utilities by name and state."""
    engine = _get_engine()
    name_param = f"%{name.strip()}%"

    if state:
        state = state.strip().upper()
        query = text("""
            SELECT 
                m.eia_utility_id, m.utility_name, m.state, m.ownership_type,
                r.residential_rate, r.commercial_rate, r.industrial_rate,
                (SELECT COUNT(DISTINCT zip_code) FROM utility_zip_lookup WHERE eia_utility_id = m.eia_utility_id) as zip_count
            FROM utility_master m
            LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
            WHERE m.utility_name ILIKE :name AND m.state = :state
            ORDER BY m.utility_name
            LIMIT 50
        """)
        params = {"name": name_param, "state": state}
    else:
        query = text("""
            SELECT 
                m.eia_utility_id, m.utility_name, m.state, m.ownership_type,
                r.residential_rate, r.commercial_rate, r.industrial_rate,
                (SELECT COUNT(DISTINCT zip_code) FROM utility_zip_lookup WHERE eia_utility_id = m.eia_utility_id) as zip_count
            FROM utility_master m
            LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
            WHERE m.utility_name ILIKE :name
            ORDER BY m.utility_name
            LIMIT 50
        """)
        params = {"name": name_param}

    try:
        df = pd.read_sql(query, con=engine, params=params)
    except Exception as e:
        logger.error(f"Error searching utilities: {e}")
        raise HTTPException(500, "Database query error")

    results = []
    for _, row in df.iterrows():
        results.append(UtilityDetailResponse(
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]),
            state=str(row["state"]),
            ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
            residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
            commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
            industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
            zip_count=int(row["zip_count"]),
        ))

    return results


@router.get("/utility/{eia_id}", response_model=UtilityDetailResponse)
@cached(ttl=3600)
async def get_utility_details(
    eia_id: int,
    state: str = Query("NJ", description="State context"),
):
    """Get comprehensive details and rates for a utility in a state."""
    engine = _get_engine()
    state = state.strip().upper()

    query = text("""
        SELECT 
            m.eia_utility_id, m.utility_name, m.state, m.ownership_type,
            r.residential_rate, r.commercial_rate, r.industrial_rate,
            (SELECT COUNT(DISTINCT zip_code) FROM utility_zip_lookup WHERE eia_utility_id = m.eia_utility_id AND state = m.state) as zip_count
        FROM utility_master m
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        WHERE m.eia_utility_id = :eia_id AND m.state = :state
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"eia_id": eia_id, "state": state})
    except Exception as e:
        logger.error(f"Error fetching utility {eia_id}: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        raise HTTPException(404, f"Utility ID {eia_id} not found in state {state}")

    row = df.iloc[0]
    return UtilityDetailResponse(
        eia_utility_id=int(row["eia_utility_id"]),
        utility_name=str(row["utility_name"]),
        state=str(row["state"]),
        ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
        residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
        commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
        industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
        zip_count=int(row["zip_count"]),
    )


@router.get("/utility/compare", response_model=UtilityCompareResponse)
@cached(ttl=600)
async def compare_utility_rates(
    ids: str = Query(..., description="Comma-separated EIA Utility IDs, e.g. 15477,8901"),
    state: str = Query("NJ", description="State context"),
):
    """Compare rates between multiple utilities."""
    state = state.strip().upper()
    try:
        eia_ids = [int(i.strip()) for i in ids.split(",") if i.strip()]
    except ValueError:
        raise HTTPException(400, "Invalid utility IDs. Must be comma-separated integers.")

    if not eia_ids:
        raise HTTPException(400, "At least one utility ID must be provided.")

    engine = _get_engine()
    query = text("""
        SELECT 
            m.eia_utility_id, m.utility_name, m.state, m.ownership_type,
            r.residential_rate, r.commercial_rate, r.industrial_rate,
            (SELECT COUNT(DISTINCT zip_code) FROM utility_zip_lookup WHERE eia_utility_id = m.eia_utility_id AND state = m.state) as zip_count
        FROM utility_master m
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        WHERE m.eia_utility_id IN :ids AND m.state = :state
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"ids": tuple(eia_ids), "state": state})
    except Exception as e:
        logger.error(f"Error comparing utilities: {e}")
        raise HTTPException(500, "Database query error")

    utilities = []
    for _, row in df.iterrows():
        utilities.append(UtilityDetailResponse(
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]),
            state=str(row["state"]),
            ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
            residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
            commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
            industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
            zip_count=int(row["zip_count"]),
        ))

    # Calculate differences if comparing exactly 2 utilities
    res_diff = None
    comm_diff = None
    ind_diff = None
    if len(utilities) == 2:
        u1, u2 = utilities[0], utilities[1]
        if u1.residential_rate and u2.residential_rate:
            res_diff = ((u1.residential_rate - u2.residential_rate) / u2.residential_rate) * 100
        if u1.commercial_rate and u2.commercial_rate:
            comm_diff = ((u1.commercial_rate - u2.commercial_rate) / u2.commercial_rate) * 100
        if u1.industrial_rate and u2.industrial_rate:
            ind_diff = ((u1.industrial_rate - u2.industrial_rate) / u2.industrial_rate) * 100

    return UtilityCompareResponse(
        utilities=utilities,
        residential_diff_pct=res_diff,
        commercial_diff_pct=comm_diff,
        industrial_diff_pct=ind_diff,
    )


@router.get("/utility/coverage", response_model=list[UtilityDetailResponse])
@cached(ttl=3600)
async def get_utilities_coverage_by_state(
    state: str = Query("NJ", description="State filter"),
):
    """Get all utilities operating in a state ordered by number of service zip codes."""
    engine = _get_engine()
    state = state.strip().upper()

    query = text("""
        SELECT 
            m.eia_utility_id, m.utility_name, m.state, m.ownership_type,
            r.residential_rate, r.commercial_rate, r.industrial_rate,
            COUNT(DISTINCT z.zip_code) as zip_count
        FROM utility_master m
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        LEFT JOIN utility_zip_lookup z ON m.eia_utility_id = z.eia_utility_id AND m.state = z.state
        WHERE m.state = :state
        GROUP BY m.eia_utility_id, m.utility_name, m.state, m.ownership_type, r.residential_rate, r.commercial_rate, r.industrial_rate
        ORDER BY zip_count DESC
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"state": state})
    except Exception as e:
        logger.error(f"Error querying state utilities coverage: {e}")
        raise HTTPException(500, "Database query error")

    results = []
    for _, row in df.iterrows():
        results.append(UtilityDetailResponse(
            eia_utility_id=int(row["eia_utility_id"]),
            utility_name=str(row["utility_name"]),
            state=str(row["state"]),
            ownership_type=str(row["ownership_type"]) if pd.notna(row.get("ownership_type")) else None,
            residential_rate=float(row["residential_rate"]) if pd.notna(row.get("residential_rate")) else None,
            commercial_rate=float(row["commercial_rate"]) if pd.notna(row.get("commercial_rate")) else None,
            industrial_rate=float(row["industrial_rate"]) if pd.notna(row.get("industrial_rate")) else None,
            zip_count=int(row["zip_count"]),
        ))

    return results
