import logging
import json
from typing import Optional, Any
from sqlalchemy import text
from database.connection import get_sync_engine

logger = logging.getLogger(__name__)


def _safe_date(val) -> Optional[str]:
    """Safely convert date/datetime/string to ISO string, or return None."""
    if val is None:
        return None
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


def _parse_rate_structure(rate_struct_str: Optional[str]) -> Optional[list]:
    """Parse JSON rate structure string to list of periods/tiers."""
    if not rate_struct_str:
        return None
    try:
        return json.loads(rate_struct_str)
    except Exception as e:
        logger.warning(f"Failed to parse energy rate structure: {e}")
        return None


def extract_effective_energy_rate(tariff: dict) -> float:
    """Extract standard energy rate (base rate + adjustment) from tariff JSON structure."""
    rate_struct = _parse_rate_structure(tariff.get("energy_rate_structure"))
    if not rate_struct or not isinstance(rate_struct, list):
        return 0.12  # fallback baseline rate: 12 cents/kWh

    try:
        # OpenEI energyratestructure typically contains lists of periods containing tier dicts
        # Grab first period, first tier to resolve a baseline variable rate
        period = rate_struct[0]
        if isinstance(period, list) and len(period) > 0:
            tier = period[0]
            rate = float(tier.get("rate", 0.0))
            adj = float(tier.get("adj", 0.0))
            return round(rate + adj, 5)
    except Exception as e:
        logger.debug(f"Failed to extract rate from structure: {e}")
        
    return 0.12


def get_tariff_by_zip(zipcode: str, sector: str = "Residential") -> list[dict]:
    """Find tariffs for all utilities operating in a given ZIP code."""
    zip_code = str(zipcode).strip().zfill(5)
    engine = get_sync_engine()

    query = text("""
        SELECT t.*, m.utility_name
        FROM utility_zip_lookup z
        JOIN utility_master m ON z.eia_utility_id = m.eia_utility_id AND z.state = m.state
        JOIN utility_tariffs t ON m.eia_utility_id = t.eia_utility_id
        WHERE z.zip_code = :zip_code AND t.sector = :sector
        ORDER BY t.is_default DESC, t.name
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"zip_code": zip_code, "sector": sector.capitalize()})
            keys = result.keys()
            rows = [dict(zip(keys, row)) for row in result]
            
            # Format rows
            for r in rows:
                r["energy_rate"] = extract_effective_energy_rate(r)
                r["ingested_at"] = _safe_date(r.get("ingested_at"))
                r["start_date"] = _safe_date(r.get("start_date"))
                r["end_date"] = _safe_date(r.get("end_date"))
            return rows
    except Exception as e:
        logger.error(f"Error querying tariffs by ZIP {zip_code}: {e}")
        return []


def get_tariff_by_utility(eia_utility_id: int, sector: str = "Residential") -> list[dict]:
    """Find all tariffs for a specific utility ID."""
    engine = get_sync_engine()

    query = text("""
        SELECT t.*
        FROM utility_tariffs t
        WHERE t.eia_utility_id = :eia_utility_id AND t.sector = :sector
        ORDER BY t.is_default DESC, t.name
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"eia_utility_id": eia_utility_id, "sector": sector.capitalize()})
            keys = result.keys()
            rows = [dict(zip(keys, row)) for row in result]
            for r in rows:
                r["energy_rate"] = extract_effective_energy_rate(r)
                r["ingested_at"] = _safe_date(r.get("ingested_at"))
                r["start_date"] = _safe_date(r.get("start_date"))
                r["end_date"] = _safe_date(r.get("end_date"))
            return rows
    except Exception as e:
        logger.error(f"Error querying tariffs for utility {eia_utility_id}: {e}")
        return []


def get_default_residential_tariff(eia_utility_id: Optional[int] = None) -> Optional[dict]:
    """Get the default residential tariff for a utility. Defaults to PSE&G (15477) if none specified."""
    utility_id = eia_utility_id or 15477
    tariffs = get_tariff_by_utility(utility_id, sector="Residential")
    
    if not tariffs:
        return None
        
    # Search for is_default = True
    for t in tariffs:
        if t.get("is_default"):
            return t
            
    # Fallback to first available residential tariff
    return tariffs[0]


def get_tariff_breakdown(tariff_id: int) -> Optional[dict]:
    """Get detailed rate component breakdown for a specific tariff ID."""
    engine = get_sync_engine()

    query = text("""
        SELECT t.*
        FROM utility_tariffs t
        WHERE t.id = :tariff_id
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"tariff_id": tariff_id})
            keys = result.keys()
            row = result.fetchone()
            if not row:
                return None
                
            r = dict(zip(keys, row))
            r["energy_rate"] = extract_effective_energy_rate(r)
            r["parsed_energy_structure"] = _parse_rate_structure(r.get("energy_rate_structure"))
            r["parsed_demand_structure"] = _parse_rate_structure(r.get("demand_rate_structure"))
            
            r["ingested_at"] = _safe_date(r.get("ingested_at"))
            r["start_date"] = _safe_date(r.get("start_date"))
            r["end_date"] = _safe_date(r.get("end_date"))
                
            return r
    except Exception as e:
        logger.error(f"Error fetching tariff breakdown for {tariff_id}: {e}")
        return None


def compare_tariffs(tariff_ids: list[int]) -> list[dict]:
    """Compare multiple tariffs side-by-side."""
    results = []
    for tid in tariff_ids:
        breakdown = get_tariff_breakdown(tid)
        if breakdown:
            results.append({
                "id": breakdown["id"],
                "name": breakdown["name"],
                "eia_utility_id": breakdown["eia_utility_id"],
                "sector": breakdown["sector"],
                "service_type": breakdown["service_type"],
                "fixed_charge": breakdown.get("fixed_charge") or 0.0,
                "min_charge": breakdown.get("min_charge"),
                "energy_rate": breakdown["energy_rate"],
                "is_default": breakdown.get("is_default", False),
                "approved": breakdown.get("approved", False),
            })
    return results
