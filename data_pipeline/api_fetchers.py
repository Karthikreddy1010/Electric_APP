"""
API Fetchers — incremental data retrieval from BLS and EIA APIs.

Supports local caching: only fetches years not already present in
the local CSV cache. Controlled by the `force` parameter.
"""
import json
import logging
from typing import Optional

import pandas as pd
import requests

from data_pipeline.config import (
    RAW_DIR,
    CPI_SERIES_ID,
    CPI_START_YEAR,
    CPI_END_YEAR,
    get_bls_api_key,
    get_eia_api_key,
)

logger = logging.getLogger(__name__)

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


# ── BLS CPI Fetcher ─────────────────────────────────────────────────────────

def _load_cached_cpi() -> Optional[pd.DataFrame]:
    """Load existing CPI monthly cache if present."""
    path = RAW_DIR / "cpi_monthly.csv"
    if path.exists():
        df = pd.read_csv(path)
        return df
    return None


def _determine_missing_years(
    cached: Optional[pd.DataFrame],
    start_year: int,
    end_year: int,
) -> list[int]:
    """Return list of years not yet present in cached data."""
    target_years = list(range(start_year, end_year + 1))
    if cached is None or cached.empty:
        return target_years

    cached_years = set(cached["year"].unique())
    missing = [y for y in target_years if y not in cached_years]
    return missing


def _fetch_bls_series(
    series_id: str,
    start_year: int,
    end_year: int,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Call the BLS API for a single year range.
    BLS v2 API limits to 20 years per request.
    """
    payload = {
        "seriesid": [series_id],
        "startyear": str(start_year),
        "endyear": str(end_year),
        "catalog": False,
        "calculations": False,
        "annualaverage": False,
    }
    if api_key:
        payload["registrationkey"] = api_key

    headers = {"Content-Type": "application/json"}

    logger.info(f"BLS API request: {series_id} [{start_year}–{end_year}]")
    try:
        resp = requests.post(
            BLS_API_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        logger.error(f"BLS API request failed: {e}")
        raise

    if result.get("status") != "REQUEST_SUCCEEDED":
        msg = result.get("message", ["Unknown error"])
        logger.error(f"BLS API error: {msg}")
        raise RuntimeError(f"BLS API returned status: {result.get('status')}")

    series_data = result.get("Results", {}).get("series", [])
    if not series_data:
        logger.warning("BLS API returned no series data.")
        return pd.DataFrame()

    records = []
    for item in series_data[0].get("data", []):
        period = item.get("period", "")
        # Only monthly data (M01–M12), skip annual averages (M13)
        if not period.startswith("M") or period == "M13":
            continue
        records.append({
            "year": int(item["year"]),
            "month": int(period[1:]),
            "cpi": float(item["value"]),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values(["year", "month"]).reset_index(drop=True)
    logger.info(f"BLS API returned {len(df)} monthly records.")
    return df


def fetch_bls_cpi(force: bool = False) -> pd.DataFrame:
    """
    Fetch BLS CPI-U monthly data with incremental caching.

    Args:
        force: If True, re-fetch all years even if cached.

    Returns:
        Complete CPI monthly DataFrame covering CPI_START_YEAR–CPI_END_YEAR.
    """
    logger.info("=" * 70)
    logger.info("STAGE 2: Fetching BLS CPI data")
    logger.info("=" * 70)

    cached = _load_cached_cpi()
    api_key = get_bls_api_key()

    if force:
        missing_years = list(range(CPI_START_YEAR, CPI_END_YEAR + 1))
        logger.info(f"Force mode: fetching all years {CPI_START_YEAR}–{CPI_END_YEAR}")
    else:
        missing_years = _determine_missing_years(cached, CPI_START_YEAR, CPI_END_YEAR)

    if not missing_years:
        logger.info("CPI data is up-to-date. No API call needed.")
        return cached

    logger.info(f"Missing years to fetch: {missing_years}")

    # BLS API allows max 20 years per request
    # Split into chunks if needed
    new_frames = []
    chunk_size = 20
    for i in range(0, len(missing_years), chunk_size):
        chunk = missing_years[i : i + chunk_size]
        start, end = min(chunk), max(chunk)
        try:
            df_chunk = _fetch_bls_series(CPI_SERIES_ID, start, end, api_key)
            if not df_chunk.empty:
                new_frames.append(df_chunk)
        except Exception as e:
            logger.error(f"Failed to fetch CPI for {start}–{end}: {e}")
            logger.info("Falling back to cached data if available.")

    if new_frames:
        new_data = pd.concat(new_frames, ignore_index=True)

        # Merge with cached, deduplicate
        if cached is not None and not cached.empty and not force:
            combined = pd.concat([cached, new_data], ignore_index=True)
        else:
            combined = new_data

        combined = (
            combined.drop_duplicates(subset=["year", "month"])
            .sort_values(["year", "month"])
            .reset_index(drop=True)
        )

        # Save updated cache
        cache_path = RAW_DIR / "cpi_monthly.csv"
        combined.to_csv(cache_path, index=False)
        logger.info(f"Saved CPI monthly cache: {len(combined)} rows → {cache_path}")

        # Also compute and save yearly averages
        _save_cpi_yearly(combined)

        return combined

    # If fetch failed but we have cache, return cache
    if cached is not None and not cached.empty:
        logger.warning("API fetch returned no data; using cached CPI data.")
        return cached

    logger.error("No CPI data available (neither cached nor from API).")
    return pd.DataFrame(columns=["year", "month", "cpi"])


def _save_cpi_yearly(monthly_df: pd.DataFrame) -> None:
    """Compute yearly CPI averages and save to cache."""
    from data_pipeline.config import CPI_BASE_YEAR

    yearly = (
        monthly_df.groupby("year")["cpi"]
        .mean()
        .reset_index()
        .rename(columns={"cpi": "cpi_annual_avg"})
    )

    # Compute deflator relative to base year
    base_cpi = yearly.loc[
        yearly["year"] == CPI_BASE_YEAR, "cpi_annual_avg"
    ]
    if not base_cpi.empty:
        base_val = base_cpi.values[0]
        yearly["deflator"] = base_val / yearly["cpi_annual_avg"]
    else:
        yearly["deflator"] = None

    # Compute YoY inflation %
    yearly["inflation_pct"] = yearly["cpi_annual_avg"].pct_change() * 100

    path = RAW_DIR / "cpi_yearly.csv"
    yearly.to_csv(path, index=False)
    logger.info(f"Saved CPI yearly cache: {len(yearly)} rows → {path}")


# ── EIA API Fetcher (Optional Extension) ────────────────────────────────────

def fetch_eia_prices(
    state: str = "NJ",
    start_year: int = 2019,
    force: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Fetch electricity prices from EIA API v2 (optional extension).

    Uses the existing EIAIngestor class for the actual API call.
    Adds incremental caching on top.

    Args:
        state: State abbreviation.
        start_year: Earliest year to fetch.
        force: If True, bypass cache check.

    Returns:
        DataFrame of EIA electricity price data, or None on failure.
    """
    api_key = get_eia_api_key()
    if not api_key:
        logger.warning("EIA_API_KEY not set. Skipping EIA price fetch.")
        return None

    cache_path = RAW_DIR / f"eia_prices_{state.lower()}_cache.csv"

    if not force and cache_path.exists():
        cached = pd.read_csv(cache_path, parse_dates=["date"])
        max_date = cached["date"].max()
        logger.info(f"EIA price cache exists through {max_date}. Skipping fetch.")
        return cached

    try:
        from data_pipeline.ingestors import EIAIngestor

        ingestor = EIAIngestor(api_key)
        df = ingestor.get_state_electricity_prices(state=state, start_year=start_year)

        if df is not None and not df.empty:
            df.to_csv(cache_path, index=False)
            logger.info(
                f"Fetched & cached EIA prices for {state}: "
                f"{len(df)} rows → {cache_path}"
            )
        return df

    except Exception as e:
        logger.error(f"EIA price fetch failed for {state}: {e}")
        if cache_path.exists():
            logger.info("Falling back to cached EIA data.")
            return pd.read_csv(cache_path, parse_dates=["date"])
        return None
