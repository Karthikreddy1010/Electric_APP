import logging
from typing import Optional
from sqlalchemy import text
from database.connection import get_sync_engine

logger = logging.getLogger(__name__)


def get_county_utilities(state: str, county: str) -> list[dict]:
    """Get all utilities operating in a specific county and state."""
    engine = get_sync_engine()
    state = state.strip().upper()
    county = county.strip()

    query = text("""
        SELECT DISTINCT
            t.utility_id,
            m.utility_name,
            m.ownership_type,
            r.residential_rate,
            r.commercial_rate,
            r.industrial_rate
        FROM utility_service_territories t
        JOIN utility_master m ON t.utility_id = m.eia_utility_id AND t.state = m.state
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        WHERE t.state = :state AND t.county = :county
        ORDER BY m.utility_name
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"state": state, "county": county})
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result]
    except Exception as e:
        logger.error(f"Error querying county utilities ({state}, {county}): {e}")
        return []


def get_state_utilities(state: str) -> list[dict]:
    """Get all utilities operating in a state with their unique county count coverage."""
    engine = get_sync_engine()
    state = state.strip().upper()

    query = text("""
        SELECT 
            m.eia_utility_id as utility_id,
            m.utility_name,
            m.ownership_type,
            r.residential_rate,
            r.commercial_rate,
            r.industrial_rate,
            COUNT(DISTINCT t.county) as county_count
        FROM utility_master m
        LEFT JOIN utility_service_territories t ON m.eia_utility_id = t.utility_id AND m.state = t.state
        LEFT JOIN utility_rates r ON m.eia_utility_id = r.eia_utility_id AND m.state = r.state
        WHERE m.state = :state
        GROUP BY m.eia_utility_id, m.utility_name, m.ownership_type, r.residential_rate, r.commercial_rate, r.industrial_rate
        ORDER BY county_count DESC, m.utility_name
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"state": state})
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result]
    except Exception as e:
        logger.error(f"Error querying state utilities ({state}): {e}")
        return []


def get_utility_service_area(utility_id: int) -> list[dict]:
    """Get all counties and states served by a utility."""
    engine = get_sync_engine()

    query = text("""
        SELECT DISTINCT state, county
        FROM utility_service_territories
        WHERE utility_id = :utility_id
        ORDER BY state, county
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"utility_id": utility_id})
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result]
    except Exception as e:
        logger.error(f"Error querying utility service area ({utility_id}): {e}")
        return []


def get_service_statistics(state: Optional[str] = None) -> dict:
    """Get aggregated service territory and load statistics across all utilities in a state or nationally."""
    engine = get_sync_engine()
    
    # Query latest year in EIA-861 master
    year_query = text("SELECT MAX(year) FROM eia861_master")
    try:
        with engine.connect() as conn:
            latest_year = conn.execute(year_query).scalar() or 2024
    except Exception:
        latest_year = 2024

    params = {"year": latest_year}
    where_clause = "WHERE m.year = :year"
    if state:
        where_clause += " AND m.state = :state"
        params["state"] = state.strip().upper()

    stats_query = text(f"""
        SELECT 
            COUNT(DISTINCT m.utility_id) as total_utilities,
            SUM(m.total_customers) as total_customers,
            SUM(m.total_sales_mwh) as total_sales_mwh,
            SUM(m.peak_demand) as total_peak_demand_mw,
            SUM(CASE WHEN m.demand_response_flag = 1 THEN 1 ELSE 0 END) as utilities_demand_response,
            SUM(CASE WHEN m.dynamic_pricing_flag = 1 THEN 1 ELSE 0 END) as utilities_dynamic_pricing,
            SUM(m.nm_customers) as total_net_metering_customers
        FROM eia861_master m
        {where_clause}
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(stats_query, params)
            keys = result.keys()
            row = result.fetchone()
            stats = dict(zip(keys, row)) if row else {}
            
            # Format and clean NaN values
            return {
                "year": latest_year,
                "state": state or "US",
                "total_utilities": int(stats.get("total_utilities") or 0),
                "total_customers": int(stats.get("total_customers") or 0),
                "total_sales_mwh": round(float(stats.get("total_sales_mwh") or 0.0), 2),
                "total_peak_demand_mw": round(float(stats.get("total_peak_demand_mw") or 0.0), 2),
                "utilities_demand_response": int(stats.get("utilities_demand_response") or 0),
                "utilities_dynamic_pricing": int(stats.get("utilities_dynamic_pricing") or 0),
                "total_net_metering_customers": int(stats.get("total_net_metering_customers") or 0),
            }
    except Exception as e:
        logger.error(f"Error querying service territory statistics: {e}")
        return {
            "year": latest_year,
            "state": state or "US",
            "error": str(e)
        }
