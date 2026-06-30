"""
OpenEI Utility Service Territories Loader — CSV ingestion + optional API sync.

CSV Sources:
  data/raw/OpenEI_IOU_Utility_ZIP_Mapping_2024.csv
  data/raw/OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv

Both CSVs have identical columns:
  zip, eiaid, utility_name, state, service_type, ownership, comm_rate, ind_rate, res_rate

Produces three normalized DataFrames for database seeding:
  1. utility_master — unique utilities (eia_utility_id, utility_name, state, ownership_type)
  2. utility_zip_lookup — ZIP→utility mappings
  3. utility_rates — average rates per utility
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def load_openei_from_csv(
    iou_path: Optional[Path] = None,
    noniou_path: Optional[Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and normalize OpenEI IOU + NonIOU CSV files.

    Returns:
        (masters_df, zip_lookup_df, rates_df) — three DataFrames ready for DB insertion.
    """
    iou_path = iou_path or RAW_DIR / "OpenEI_IOU_Utility_ZIP_Mapping_2024.csv"
    noniou_path = noniou_path or RAW_DIR / "OpenEI_NonIOU_Utility_ZIP_Mapping_2024.csv"

    frames = []
    for path in [iou_path, noniou_path]:
        if path.exists():
            df = pd.read_csv(path, dtype={"zip": str})
            logger.info(f"Loaded {len(df)} rows from {path.name}")
            frames.append(df)
        else:
            logger.warning(f"OpenEI CSV not found: {path}")

    if not frames:
        logger.error("No OpenEI CSV files found")
        empty = pd.DataFrame()
        return empty, empty, empty

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Combined OpenEI data: {len(combined)} total rows")

    # Standardize column names
    combined = combined.rename(columns={
        "zip": "zip_code",
        "eiaid": "eia_utility_id",
        "ownership": "ownership_type",
        "res_rate": "residential_rate",
        "comm_rate": "commercial_rate",
        "ind_rate": "industrial_rate",
    })

    # Clean data
    combined["zip_code"] = combined["zip_code"].astype(str).str.zfill(5)
    combined["eia_utility_id"] = pd.to_numeric(combined["eia_utility_id"], errors="coerce")
    combined = combined.dropna(subset=["eia_utility_id"])
    combined["eia_utility_id"] = combined["eia_utility_id"].astype(int)
    combined["state"] = combined["state"].astype(str).str.strip().str.upper()

    # 1. Build utility_master — unique (eia_utility_id, state)
    masters = (
        combined
        .groupby(["eia_utility_id", "state"])
        .agg({
            "utility_name": "first",
            "ownership_type": "first",
        })
        .reset_index()
    )
    logger.info(f"Utility master: {len(masters)} unique utility-state pairs")

    # 2. Build utility_zip_lookup — unique (zip_code, eia_utility_id)
    zip_lookup = (
        combined[["zip_code", "eia_utility_id", "utility_name", "state", "service_type"]]
        .drop_duplicates(subset=["zip_code", "eia_utility_id"])
        .reset_index(drop=True)
    )
    logger.info(f"ZIP lookup: {len(zip_lookup)} unique ZIP-utility mappings")

    # 3. Build utility_rates — average rates per (eia_utility_id, state)
    rate_cols = ["residential_rate", "commercial_rate", "industrial_rate"]
    rates = (
        combined
        .groupby(["eia_utility_id", "state"])[rate_cols]
        .mean()
        .reset_index()
    )
    # Replace 0.0 rates with None (0.0 means no service for that sector)
    for col in rate_cols:
        rates.loc[rates[col] == 0.0, col] = None
    logger.info(f"Utility rates: {len(rates)} records")

    return masters, zip_lookup, rates


def sync_openei_tariffs(
    eia_utility_ids: Optional[list[int]] = None,
    api_key: str = "DEMO_KEY",
    limit: int = 50,
) -> pd.DataFrame:
    """
    Optional: Fetch tariff metadata from OpenEI URDB API.

    This is an optional monthly sync — the CSV master data is the primary source.
    Only fetches tariffs for the specified utility IDs (or top NJ utilities by default).

    Returns DataFrame ready for utility_tariffs table insertion.
    """
    base_url = "https://api.openei.org/utility_rates"

    if eia_utility_ids is None:
        # Default: major NJ utilities
        eia_utility_ids = [15477, 8901, 347, 12390]  # PSE&G, JCP&L, ACE, RECO

    all_records = []

    for eia_id in eia_utility_ids:
        params = {
            "api_key": api_key,
            "version": "latest",
            "detail": "full",
            "eia": eia_id,
            "limit": limit,
        }

        try:
            logger.info(f"OpenEI API: fetching tariffs for utility {eia_id}")
            resp = requests.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                record = {
                    "eia_utility_id": eia_id,
                    "label": item.get("label"),
                    "name": item.get("name"),
                    "uri": item.get("uri"),
                    "sector": item.get("sector"),
                    "service_type": item.get("servicetype"),
                    "source": item.get("source"),
                    "source_parent": item.get("sourceparent"),
                    "fixed_charge": _safe_float(item.get("fixedchargefirstmeter")),
                    "fixed_charge_units": item.get("fixedchargeunits"),
                    "min_charge": _safe_float(item.get("mincharge")),
                    "min_charge_units": item.get("minchargeunits"),
                    "energy_rate_structure": json.dumps(item.get("energyratestructure")) if item.get("energyratestructure") else None,
                    "energy_comments": item.get("energycomments"),
                    "demand_rate_structure": json.dumps(item.get("demandratestructure")) if item.get("demandratestructure") else None,
                    "demand_comments": item.get("demandcomments"),
                    "start_date": _parse_epoch_date(item.get("startdate")),
                    "end_date": _parse_epoch_date(item.get("enddate")),
                    "approved": item.get("approved"),
                    "is_default": item.get("is_default"),
                }
                all_records.append(record)

            logger.info(f"OpenEI API: fetched {len(items)} tariffs for utility {eia_id}")

        except Exception as e:
            logger.error(f"OpenEI API error for utility {eia_id}: {e}")
            continue

    df = pd.DataFrame(all_records)
    if not df.empty:
        logger.info(f"OpenEI tariff sync: {len(df)} total tariff records")
    return df


def _safe_float(val) -> Optional[float]:
    """Convert to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_epoch_date(val) -> Optional[str]:
    """Convert epoch timestamp (seconds) to date string, or return None."""
    if val is None:
        return None
    try:
        ts = int(val)
        return pd.Timestamp(ts, unit="s").date()
    except (ValueError, TypeError, OverflowError):
        return None
