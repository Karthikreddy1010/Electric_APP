"""
GET /eia861m — monthly state-level electricity sales, revenue, customers, and prices.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from api.cache import cached
from api.state import app_state
from api.schemas import EIA861MSummary, EIA861MRecord, EIA861MStateTrends, EIA861MRankingItem
from database.connection import get_sync_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["EIA-861M"])


def _get_eia861m_df() -> pd.DataFrame:
    """Retrieve EIA-861M DataFrame from app_state or database."""
    df = app_state.get("eia861m_df")
    if df is None or df.empty:
        try:
            engine = get_sync_engine()
            df = pd.read_sql("SELECT * FROM eia861m_monthly", con=engine)
            if not df.empty:
                app_state["eia861m_df"] = df
                logger.info(f"Loaded eia861m_df from database: {len(df)} rows")
            else:
                logger.warning("eia861m_monthly table is empty")
        except Exception as e:
            logger.error(f"Error reading eia861m_monthly: {e}")
            df = pd.DataFrame()
    return df


@router.get("/eia861m/summary", response_model=EIA861MSummary)
@cached(ttl=300)
async def get_eia861m_summary():
    """Get the latest national monthly aggregate summary (TOTAL sector)."""
    df = _get_eia861m_df()
    if df.empty:
        raise HTTPException(500, "EIA-861M data not loaded")

    # Filter to total sector
    totals = df[df["sector"] == "total"].copy()
    if totals.empty:
        raise HTTPException(404, "No 'total' sector data found in EIA-861M")

    # Find the latest year/month period
    latest_period = totals["period"].max()
    latest_data = totals[totals["period"] == latest_period]

    year = int(latest_data["year"].iloc[0])
    month = int(latest_data["month"].iloc[0])

    # Aggregate national totals for that month
    monthly_sales = float(latest_data["sales_mwh"].sum())
    monthly_revenue = float(latest_data["revenue_k_dollars"].sum())
    customer_count = int(latest_data["customers"].sum())
    avg_price = float(latest_data["price_cents_kwh"].mean())

    return EIA861MSummary(
        year=year,
        month=month,
        period=latest_period,
        monthly_sales_mwh=monthly_sales,
        monthly_revenue_k=monthly_revenue,
        customer_count=customer_count,
        avg_price_cents_kwh=round(avg_price, 4),
    )


@router.get("/eia861m/states", response_model=list[str])
@cached(ttl=600)
async def get_eia861m_states():
    """Get a list of all states with monthly data available."""
    df = _get_eia861m_df()
    if df.empty:
        return []
    return sorted(df["state"].dropna().unique().tolist())


@router.get("/eia861m/state/{state}", response_model=EIA861MStateTrends)
@cached(ttl=300)
async def get_state_monthly_trends(
    state: str,
    sector: str = Query("total", description="residential | commercial | industrial | total"),
):
    """Get monthly trends for a specific state and sector."""
    df = _get_eia861m_df()
    if df.empty:
        raise HTTPException(500, "EIA-861M data not loaded")

    state = state.strip().upper()
    state_df = df[(df["state"] == state) & (df["sector"] == sector.lower())].copy()
    if state_df.empty:
        raise HTTPException(404, f"No monthly data found for state {state} and sector {sector}")

    state_df = state_df.sort_values("period")

    return EIA861MStateTrends(
        state=state,
        periods=state_df["period"].tolist(),
        sales=state_df["sales_mwh"].fillna(0.0).tolist(),
        revenue=state_df["revenue_k_dollars"].fillna(0.0).tolist(),
        prices=state_df["price_cents_kwh"].fillna(0.0).tolist(),
        customers=state_df["customers"].fillna(0).astype(int).tolist(),
    )


@router.get("/eia861m/trends", response_model=EIA861MStateTrends)
@cached(ttl=300)
async def get_national_monthly_trends(
    sector: str = Query("total", description="residential | commercial | industrial | total"),
):
    """Get national aggregated monthly trends."""
    df = _get_eia861m_df()
    if df.empty:
        raise HTTPException(500, "EIA-861M data not loaded")

    sector_df = df[df["sector"] == sector.lower()].copy()
    if sector_df.empty:
        raise HTTPException(404, f"No monthly data found for sector {sector}")

    # Aggregate by period
    grouped = sector_df.groupby("period").agg({
        "sales_mwh": "sum",
        "revenue_k_dollars": "sum",
        "price_cents_kwh": "mean",
        "customers": "sum",
    }).reset_index()

    grouped = grouped.sort_values("period")

    return EIA861MStateTrends(
        state="US",
        periods=grouped["period"].tolist(),
        sales=grouped["sales_mwh"].fillna(0.0).tolist(),
        revenue=grouped["revenue_k_dollars"].fillna(0.0).tolist(),
        prices=grouped["price_cents_kwh"].fillna(0.0).tolist(),
        customers=grouped["customers"].fillna(0).astype(int).tolist(),
    )


@router.get("/eia861m/rankings", response_model=list[EIA861MRankingItem])
@cached(ttl=300)
async def get_eia861m_rankings(
    period: Optional[str] = Query(None, description="Format YYYY-MM. Defaults to latest month."),
    sector: str = Query("residential", description="residential | commercial | industrial | total"),
):
    """Get state rankings by price for a specific month and sector."""
    df = _get_eia861m_df()
    if df.empty:
        raise HTTPException(500, "EIA-861M data not loaded")

    period = period or df["period"].max()
    period_df = df[(df["period"] == period) & (df["sector"] == sector.lower())].copy()
    if period_df.empty:
        raise HTTPException(404, f"No monthly data found for period {period} and sector {sector}")

    # Sort by price descending
    period_df = period_df.sort_values("price_cents_kwh", ascending=False).reset_index(drop=True)

    rankings = []
    for i, row in period_df.iterrows():
        rankings.append(EIA861MRankingItem(
            state=row["state"],
            price_cents_kwh=float(row["price_cents_kwh"]) if pd.notna(row["price_cents_kwh"]) else 0.0,
            sales_mwh=float(row["sales_mwh"]) if pd.notna(row["sales_mwh"]) else 0.0,
            customers=int(row["customers"]) if pd.notna(row["customers"]) else 0,
            rank=i + 1,
        ))

    return rankings
