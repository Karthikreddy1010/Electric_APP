"""
EIA PJM Daily Demand Data Fetcher
─────────────────────────────────
Fetches PJM sub-BA daily demand data (AE, JC, PS, RECO) from the EIA API.
Supports both full download and incremental append modes.

Usage:
    # As a module (called by scheduler):
    from data_pipeline.eia_demand_fetcher import fetch_and_update_daily_demand
    fetch_and_update_daily_demand()

    # Standalone:
    python -m data_pipeline.eia_demand_fetcher
"""

import os
import csv
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

import requests
import pandas as pd

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

API_KEY = os.environ.get("EIA_API_KEY", "MPXiO8mjvmZc9fgNWkeZhhKP9SYaBbQDxodAswcg")

BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-region-sub-ba-data/data/"

SUBBAS = ["AE", "JC", "PS", "RECO"]   # PJM sub-balancing authorities

FULL_START_DATE = "2019-01-01"          # earliest date for full downloads
PAGE_SIZE       = 5000                  # max records per API request
REQUEST_DELAY   = 0.5                   # seconds between pages

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "eia_pjm_daily_demand.csv"


# ── API helpers ───────────────────────────────────────────────────────────────

def _build_params(start_date: str, end_date: str, offset: int) -> list:
    """
    Build request params as a list of tuples so repeated keys
    (facets[subba][]) are handled correctly by the requests library.
    """
    params = [
        ("api_key",            API_KEY),
        ("frequency",          "daily"),
        ("data[0]",            "value"),
        ("facets[parent][]",   "PJM"),
        ("start",              start_date),
        ("end",                end_date),
        ("sort[0][column]",    "period"),
        ("sort[0][direction]", "asc"),
        ("length",             PAGE_SIZE),
        ("offset",             offset),
    ]
    for subba in SUBBAS:
        params.append(("facets[subba][]", subba))
    return params


def _fetch_page(session: requests.Session, start_date: str, end_date: str, offset: int) -> dict:
    """GET one page of results from the EIA API."""
    resp = session.get(BASE_URL, params=_build_params(start_date, end_date, offset), timeout=30)

    if resp.status_code == 403:
        raise RuntimeError(
            "403 Forbidden — EIA API key may be invalid or missing. "
            "Register at: https://www.eia.gov/opendata/"
        )
    if resp.status_code == 429:
        raise RuntimeError(
            "429 Too Many Requests — EIA rate limit hit. "
            "Wait a few minutes and try again."
        )

    resp.raise_for_status()
    return resp.json()


def _download_records(start_date: str, end_date: str) -> list[dict]:
    """Page through every result page and return a flat list of records."""
    all_records = []
    offset = 0

    with requests.Session() as session:
        # Page 1 — also discovers the total record count
        logger.info(f"EIA fetch page 1 (offset=0, {start_date} → {end_date})...")
        payload = _fetch_page(session, start_date, end_date, offset)
        body    = payload.get("response", {})
        total   = int(body.get("total", 0))
        records = body.get("data", [])

        if total == 0:
            logger.info("EIA API returned 0 records for the given date range.")
            return []

        all_records.extend(records)
        pages_needed = -(-total // PAGE_SIZE)  # ceiling division
        logger.info(f"  {len(records):,} records fetched | total: {total:,} | pages: {pages_needed}")

        # Remaining pages
        offset += PAGE_SIZE
        page = 2
        while offset < total:
            time.sleep(REQUEST_DELAY)
            logger.info(f"EIA fetch page {page} (offset={offset})...")
            payload = _fetch_page(session, start_date, end_date, offset)
            records = payload.get("response", {}).get("data", [])
            if not records:
                break
            all_records.extend(records)
            logger.info(f"  {len(records):,} records fetched | total so far: {len(all_records):,}")
            offset += PAGE_SIZE
            page += 1

    logger.info(f"EIA download complete — {len(all_records):,} records total")
    return all_records


# ── Core public API ───────────────────────────────────────────────────────────

def fetch_and_update_daily_demand(output_path: str | Path | None = None) -> Path:
    """
    Fetch the latest PJM daily demand data from EIA and update the local CSV.

    - If the CSV exists: reads the last date, fetches only newer data, and appends.
    - If the CSV doesn't exist: downloads the full history from 2019-01-01.

    Returns the path to the updated CSV file.
    """
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Determine start date based on existing data
    if output_path.exists() and output_path.stat().st_size > 0:
        try:
            existing_df = pd.read_csv(output_path)
            last_date = pd.to_datetime(existing_df["period"]).max()
            # Start from the day after the last date we have
            start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"Incremental mode: existing data through {last_date.date()}, "
                        f"fetching from {start_date}")

            if start_date > today_str:
                logger.info("Data is already up to date — nothing to fetch.")
                return output_path
        except Exception as e:
            logger.warning(f"Could not read existing CSV ({e}), doing full download")
            start_date = FULL_START_DATE
            existing_df = None
    else:
        logger.info("No existing CSV found — performing full download")
        start_date = FULL_START_DATE
        existing_df = None

    # Fetch new records from EIA
    new_records = _download_records(start_date, today_str)

    if not new_records:
        logger.info("No new records returned by EIA API.")
        return output_path

    new_df = pd.DataFrame(new_records)

    # Merge with existing data if incremental
    if existing_df is not None:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        # Drop any duplicates (same period + subba)
        combined_df = combined_df.drop_duplicates(subset=["period", "subba"], keep="last")
    else:
        combined_df = new_df

    # Sort chronologically
    combined_df = combined_df.sort_values(["period", "subba"]).reset_index(drop=True)

    # Save
    combined_df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(combined_df):,} total records to {output_path}")
    logger.info(f"  Date range: {combined_df['period'].min()} → {combined_df['period'].max()}")
    logger.info(f"  New records appended: {len(new_records):,}")

    return output_path


# ── Standalone execution ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    masked = ("*" * (len(API_KEY) - 4) + API_KEY[-4:]) if len(API_KEY) > 8 else "(not set)"
    print("=" * 60)
    print("  EIA PJM Sub-BA Daily Demand Fetcher")
    print(f"  Sub-BAs : {', '.join(SUBBAS)}")
    print(f"  API key : {masked}")
    print(f"  Output  : {DEFAULT_OUTPUT}")
    print("=" * 60)

    result_path = fetch_and_update_daily_demand()
    print(f"\n  Done → {result_path}")
