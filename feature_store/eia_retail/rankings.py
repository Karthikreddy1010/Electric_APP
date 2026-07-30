"""
EIA Retail Rankings Engine
Computes state, regional, national, rolling, and percentile rankings across all metrics and sectors.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from feature_store.base.cache import memoize_feature

logger = logging.getLogger(__name__)

REGION_MAP = {
    "CT": "Northeast", "ME": "Northeast", "MA": "Northeast", "NH": "Northeast",
    "RI": "Northeast", "VT": "Northeast", "NJ": "Northeast", "NY": "Northeast",
    "PA": "Northeast",
    "IL": "Midwest", "IN": "Midwest", "MI": "Midwest", "OH": "Midwest",
    "WI": "Midwest", "IA": "Midwest", "KS": "Midwest", "MN": "Midwest",
    "MO": "Midwest", "NE": "Midwest", "ND": "Midwest", "SD": "Midwest",
    "DE": "South", "DC": "South", "FL": "South", "GA": "South",
    "MD": "South", "NC": "South", "SC": "South", "VA": "South",
    "WV": "South", "AL": "South", "KY": "South", "MS": "South",
    "TN": "South", "AR": "South", "LA": "South", "OK": "South", "TX": "South",
    "AZ": "West", "CO": "West", "ID": "West", "MT": "West",
    "NV": "West", "NM": "West", "UT": "West", "WY": "West",
    "AK": "West", "CA": "West", "HI": "West", "OR": "West", "WA": "West",
}


def add_rankings_and_percentiles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes national rank, regional rank, and percentile rank for each (period, sectorid).
    Rank 1 = Highest price (most expensive).
    """
    df = df.copy()

    # Assign region column
    df["region"] = df["stateid"].map(REGION_MAP).fillna("Other")

    # Exclude US total row from state rankings
    is_state = df["stateid"] != "US"

    # National & Regional Rank per period and sectorid
    df["national_rank"] = np.nan
    df["regional_rank"] = np.nan
    df["percentile_rank"] = np.nan

    # Group by period and sectorid to rank states
    state_rows = df[is_state].copy()
    
    # Compute rank (1 = highest retail_price)
    state_rows["national_rank"] = state_rows.groupby(["period", "sectorid"])["retail_price"].rank(
        ascending=False, method="min"
    )

    # Compute percentile rank (0 to 100)
    state_rows["percentile_rank"] = state_rows.groupby(["period", "sectorid"])["retail_price"].rank(
        pct=True
    ) * 100.0

    # Regional Rank
    state_rows["regional_rank"] = state_rows.groupby(["period", "sectorid", "region"])["retail_price"].rank(
        ascending=False, method="min"
    )

    # Update back to main dataframe
    df.update(state_rows[["national_rank", "percentile_rank", "regional_rank"]])

    df["national_rank"] = df["national_rank"].fillna(0).astype(int)
    df["regional_rank"] = df["regional_rank"].fillna(0).astype(int)
    df["percentile_rank"] = df["percentile_rank"].fillna(0.0).round(1)

    return df


@memoize_feature(ttl=3600)
def get_top_and_bottom_states(df: pd.DataFrame, period: str, sectorid: str = "RES", top_n: int = 10):
    """
    Retrieves top N most expensive and bottom N cheapest states for a given period and sector.
    """
    period_df = df[(df["period"] == period) & (df["sectorid"] == sectorid) & (df["stateid"] != "US")].copy()
    if period_df.empty:
        latest = df["period"].max()
        period_df = df[(df["period"] == latest) & (df["sectorid"] == sectorid) & (df["stateid"] != "US")].copy()

    period_df = period_df.sort_values("retail_price", ascending=False)
    
    most_expensive = period_df.head(top_n)[["stateid", "stateDescription", "retail_price", "national_rank", "price_yoy_growth"]].to_dict("records")
    cheapest = period_df.tail(top_n)[::-1][["stateid", "stateDescription", "retail_price", "national_rank", "price_yoy_growth"]].to_dict("records")

    return {"most_expensive": most_expensive, "cheapest": cheapest}
