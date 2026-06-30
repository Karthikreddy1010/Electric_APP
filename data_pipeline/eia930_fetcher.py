"""
EIA-930 Hourly Grid Operations Fetcher — API-only data pipeline.

Source: EIA API v2 electricity/rto/* endpoints
  1. region-data       → eia930_hourly     (demand, forecast, generation, interchange)
  2. fuel-type-data    → eia930_generation  (generation by energy source)
  3. region-sub-ba-data → eia930_subregion  (demand by subregion)
  4. interchange-data  → eia930_interchange (interchange between BAs)

All data is fetched from the API, cached locally in the database,
and served to the frontend from the database — never directly from the API.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "eia930_cache"

# Default balancing authorities to sync (PJM + NJ sub-BAs)
DEFAULT_BA_CODES = ["PJM"]
DEFAULT_SUB_BA_PARENT = "PJM"

EIA_BASE_URL = "https://api.eia.gov/v2/electricity/rto"


def _get_api_key() -> Optional[str]:
    """Get EIA API key from config."""
    try:
        from data_pipeline.config import get_eia_api_key
        return get_eia_api_key()
    except Exception:
        import os
        return os.environ.get("EIA_API_KEY")


def _fetch_eia_data(
    endpoint: str,
    params: dict,
    api_key: str,
    max_records: int = 5000,
) -> list[dict]:
    """
    Generic EIA API v2 data fetcher with pagination support.

    Returns list of raw API record dicts.
    """
    url = f"{EIA_BASE_URL}/{endpoint}/data"
    params["api_key"] = api_key
    params["length"] = max_records

    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json().get("response", {}).get("data", [])
        logger.info(f"EIA-930 {endpoint}: fetched {len(data)} records")
        return data
    except requests.RequestException as e:
        logger.error(f"EIA-930 API error ({endpoint}): {e}")
        return []


def fetch_eia930_region_data(
    ba_codes: Optional[list[str]] = None,
    hours_back: int = 48,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch hourly demand, demand forecast, net generation, and interchange
    from EIA-930 region-data endpoint.

    Returns DataFrame with columns:
        period, ba_code, ba_name, type_code, type_name, value_mwh
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        logger.warning("EIA_API_KEY not set. Skipping EIA-930 region data fetch.")
        return pd.DataFrame()

    ba_codes = ba_codes or DEFAULT_BA_CODES
    start = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H")

    params = {
        "data[0]": "value",
        "start": start,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
    }

    # Add BA facets
    for i, ba in enumerate(ba_codes):
        params[f"facets[respondent][{i}]"] = ba

    raw_data = _fetch_eia_data("region-data", params, api_key)

    records = []
    for r in raw_data:
        period_str = r.get("period", "")
        if not period_str:
            continue

        records.append({
            "period": _parse_eia_period(period_str),
            "ba_code": r.get("respondent", ""),
            "ba_name": r.get("respondent-name", ""),
            "type_code": r.get("type", ""),
            "type_name": r.get("type-name", ""),
            "value_mwh": _safe_float(r.get("value")),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.dropna(subset=["period"])
        df = df.drop_duplicates(subset=["period", "ba_code", "type_code"])
        logger.info(f"EIA-930 region-data: {len(df)} records for {ba_codes}")

    return df


def fetch_eia930_fuel_type(
    ba_codes: Optional[list[str]] = None,
    hours_back: int = 48,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch hourly generation by energy source from EIA-930 fuel-type-data endpoint.

    Returns DataFrame with columns:
        period, ba_code, ba_name, fuel_type, fuel_type_name, value_mwh
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        logger.warning("EIA_API_KEY not set. Skipping EIA-930 fuel type fetch.")
        return pd.DataFrame()

    ba_codes = ba_codes or DEFAULT_BA_CODES
    start = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H")

    params = {
        "data[0]": "value",
        "start": start,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
    }

    for i, ba in enumerate(ba_codes):
        params[f"facets[respondent][{i}]"] = ba

    raw_data = _fetch_eia_data("fuel-type-data", params, api_key)

    records = []
    for r in raw_data:
        period_str = r.get("period", "")
        if not period_str:
            continue

        records.append({
            "period": _parse_eia_period(period_str),
            "ba_code": r.get("respondent", ""),
            "ba_name": r.get("respondent-name", ""),
            "fuel_type": r.get("fueltype", ""),
            "fuel_type_name": r.get("type-name", ""),
            "value_mwh": _safe_float(r.get("value")),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.dropna(subset=["period"])
        df = df.drop_duplicates(subset=["period", "ba_code", "fuel_type"])
        logger.info(f"EIA-930 fuel-type: {len(df)} records for {ba_codes}")

    return df


def fetch_eia930_subregion(
    parent_ba: str = DEFAULT_SUB_BA_PARENT,
    hours_back: int = 48,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch hourly demand by sub-balancing authority from EIA-930 region-sub-ba-data.

    Returns DataFrame with columns:
        period, subba_code, subba_name, parent_ba, parent_ba_name, value_mwh
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        logger.warning("EIA_API_KEY not set. Skipping EIA-930 subregion fetch.")
        return pd.DataFrame()

    start = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H")

    params = {
        "data[0]": "value",
        "start": start,
        "facets[parent][]": parent_ba,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
    }

    raw_data = _fetch_eia_data("region-sub-ba-data", params, api_key)

    records = []
    for r in raw_data:
        period_str = r.get("period", "")
        if not period_str:
            continue

        records.append({
            "period": _parse_eia_period(period_str),
            "subba_code": r.get("subba", ""),
            "subba_name": r.get("subba-name", ""),
            "parent_ba": r.get("parent", ""),
            "parent_ba_name": r.get("parent-name", ""),
            "value_mwh": _safe_float(r.get("value")),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.dropna(subset=["period"])
        df = df.drop_duplicates(subset=["period", "subba_code"])
        logger.info(f"EIA-930 subregion: {len(df)} records (parent: {parent_ba})")

    return df


def fetch_eia930_interchange(
    ba_codes: Optional[list[str]] = None,
    hours_back: int = 48,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch hourly interchange between neighboring balancing authorities.

    Returns DataFrame with columns:
        period, from_ba, from_ba_name, to_ba, to_ba_name, value_mwh
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        logger.warning("EIA_API_KEY not set. Skipping EIA-930 interchange fetch.")
        return pd.DataFrame()

    ba_codes = ba_codes or DEFAULT_BA_CODES
    start = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H")

    params = {
        "data[0]": "value",
        "start": start,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
    }

    for i, ba in enumerate(ba_codes):
        params[f"facets[fromba][{i}]"] = ba

    raw_data = _fetch_eia_data("interchange-data", params, api_key)

    records = []
    for r in raw_data:
        period_str = r.get("period", "")
        if not period_str:
            continue

        records.append({
            "period": _parse_eia_period(period_str),
            "from_ba": r.get("fromba", ""),
            "from_ba_name": r.get("fromba-name", ""),
            "to_ba": r.get("toba", ""),
            "to_ba_name": r.get("toba-name", ""),
            "value_mwh": _safe_float(r.get("value")),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.dropna(subset=["period"])
        df = df.drop_duplicates(subset=["period", "from_ba", "to_ba"])
        logger.info(f"EIA-930 interchange: {len(df)} records for {ba_codes}")

    return df


def fetch_all_eia930(
    ba_codes: Optional[list[str]] = None,
    hours_back: int = 48,
    api_key: Optional[str] = None,
) -> dict[str, pd.DataFrame]:
    """
    Convenience function: fetch all 4 EIA-930 datasets at once.

    Returns dict with keys: 'hourly', 'generation', 'subregion', 'interchange'
    """
    ba_codes = ba_codes or DEFAULT_BA_CODES
    api_key = api_key or _get_api_key()

    return {
        "hourly": fetch_eia930_region_data(ba_codes, hours_back, api_key),
        "generation": fetch_eia930_fuel_type(ba_codes, hours_back, api_key),
        "subregion": fetch_eia930_subregion(ba_codes[0] if ba_codes else "PJM", hours_back, api_key),
        "interchange": fetch_eia930_interchange(ba_codes, hours_back, api_key),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_eia_period(period_str: str) -> Optional[datetime]:
    """Parse EIA-930 period string (e.g., '2026-06-30T03') to datetime."""
    try:
        return pd.to_datetime(period_str)
    except Exception:
        return None


def _safe_float(val) -> Optional[float]:
    """Convert to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
