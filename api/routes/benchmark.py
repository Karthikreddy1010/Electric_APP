"""GET /benchmark — state electricity rate comparison using real EIA data."""
import logging
from fastapi import APIRouter, HTTPException, Query
from api.state import app_state
from api.cache import cached
from api.schemas import BenchmarkRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["benchmark"])


@router.post("/benchmark")
async def state_benchmark_post(req: BenchmarkRequest):
    return await state_benchmark(year=req.year, compare_state=req.compare_state)


@router.get("/benchmark")
@cached(ttl=600)
async def state_benchmark(
    year: int = Query(2025, ge=2005, le=2026),
    compare_state: str = Query("NJ"),
):
    """Compare residential electricity rates across all US states."""
    bench_df = app_state.get("benchmark_df")
    if bench_df is None:
        raise HTTPException(500, "Benchmark data not loaded")

    year_data = bench_df[bench_df["year"] == year].copy()
    if year_data.empty:
        available = sorted(bench_df["year"].unique().tolist())
        raise HTTPException(404, f"No data for year {year}. Available: {available}")

    # Sort by price descending (rank 1 = most expensive)
    year_data = year_data.sort_values("avg_rate", ascending=False).reset_index(drop=True)
    year_data["rank"] = range(1, len(year_data) + 1)

    # National average
    national_avg = round(float(year_data["avg_rate"].mean()), 4)

    # Focus state
    focus = year_data[year_data["state"] == compare_state]
    if focus.empty:
        raise HTTPException(404, f"State '{compare_state}' not found in {year} data")

    focus_row = focus.iloc[0]
    vs_national = round((focus_row["avg_rate"] - national_avg) / national_avg * 100, 1)

    # States list
    states = []
    for _, row in year_data.iterrows():
        states.append({
            "state": row["state"],
            "state_name": row.get("state_name", row["state"]),
            "avg_rate": round(float(row["avg_rate"]), 4),
            "avg_bill": round(float(row["avg_bill"]), 2),
            "avg_usage_kwh": int(row.get("avg_usage_kwh", 0)),
            "rank": int(row["rank"]),
            "region": row.get("region", "Unknown"),
            "percentile": round(float(row.get("percentile", 0)), 1),
            "vs_national_pct": round(float(row.get("vs_national_pct", 0)), 1),
        })

    # Top 10 most expensive
    top_10 = states[:10]

    # Bottom 10 cheapest
    cheapest_10 = states[-10:][::-1]

    # Regional averages
    region_avgs = (
        year_data.groupby("region")["avg_rate"]
        .mean()
        .sort_values(ascending=False)
        .round(4)
        .to_dict()
    )

    # Available years
    available_years = sorted(bench_df["year"].unique().tolist())

    # Generate insights
    try:
        from data_pipeline.benchmark_builder import generate_insights
        insights = generate_insights(bench_df, compare_state, year)
    except Exception as e:
        logger.warning(f"Insights generation failed: {e}")
        insights = []

    # Scatter data (price vs bill)
    scatter = [
        {"state": s["state"], "avg_rate": s["avg_rate"], "avg_bill": s["avg_bill"], "region": s["region"]}
        for s in states
    ]

    return {
        "year": year,
        "focus_state": {
            "state": focus_row["state"],
            "state_name": focus_row.get("state_name", focus_row["state"]),
            "avg_rate": round(float(focus_row["avg_rate"]), 4),
            "avg_bill": round(float(focus_row["avg_bill"]), 2),
            "rank": int(focus_row["rank"]),
            "vs_national_pct": vs_national,
            "region": focus_row.get("region", "Unknown"),
            "avg_usage_kwh": int(focus_row.get("avg_usage_kwh", 0)),
        },
        "national_avg": national_avg,
        "states": states,
        "top_10_expensive": top_10,
        "cheapest_10": cheapest_10,
        "region_averages": region_avgs,
        "available_years": available_years,
        "insights": insights,
        "scatter_data": scatter,
        "total_states": len(states),
    }


@router.get("/benchmark/zip-level")
async def benchmark_zip_level(state: str = Query("NJ")):
    state = state.strip().upper()
    from database.connection import get_sync_engine
    from sqlalchemy import text
    import pandas as pd
    import numpy as np

    engine = get_sync_engine()
    query = text("""
        SELECT 
            z.zip_code, 
            r.residential_rate
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
        WHERE z.state = :state
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"state": state})
    except Exception as e:
        logger.error(f"Database query error in benchmark_zip_level: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        return {"state": state, "avg_rate": 0, "zips": []}

    df['zip_code'] = df['zip_code'].astype(str).str.strip().str.zfill(5)
    grouped = df.groupby('zip_code')['residential_rate'].mean().dropna().reset_index()

    if grouped.empty:
        return {"state": state, "avg_rate": 0, "zips": []}

    avg_rate = float(grouped['residential_rate'].mean())

    zips_list = []
    for _, row in grouped.sort_values('residential_rate', ascending=False).iterrows():
        rate = float(row['residential_rate'])
        vs_avg_pct = round((rate - avg_rate) / avg_rate * 100, 1) if avg_rate > 0 else 0.0
        zips_list.append({
            "zip_code": row['zip_code'],
            "rate": round(rate, 4),
            "vs_state_avg_pct": vs_avg_pct
        })

    above_avg = sum(1 for z in zips_list if z["vs_state_avg_pct"] > 0)
    below_avg = len(zips_list) - above_avg

    return {
        "state": state,
        "avg_rate": round(avg_rate, 4),
        "above_average_count": above_avg,
        "below_average_count": below_avg,
        "zips": zips_list
    }


@router.get("/benchmark/utility-comparison")
async def benchmark_utility_comparison(state: str = Query("NJ")):
    state = state.strip().upper()
    from database.connection import get_sync_engine
    from sqlalchemy import text
    import pandas as pd

    engine = get_sync_engine()
    query = text("""
        SELECT 
            z.utility_name,
            r.residential_rate,
            r.commercial_rate,
            r.industrial_rate
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
        WHERE z.state = :state AND z.utility_name IS NOT NULL
    """)

    try:
        df = pd.read_sql(query, con=engine, params={"state": state})
    except Exception as e:
        logger.error(f"Database query error in benchmark_utility_comparison: {e}")
        raise HTTPException(500, "Database query error")

    if df.empty:
        return []

    # Calculate average rates per utility
    grouped = df.groupby('utility_name').agg({
        'residential_rate': 'mean',
        'commercial_rate': 'mean',
        'industrial_rate': 'mean'
    }).dropna(subset=['residential_rate']).reset_index()

    utils_list = []
    for _, row in grouped.sort_values('residential_rate', ascending=False).iterrows():
        utils_list.append({
            "utility_name": row['utility_name'],
            "residential_rate": round(float(row['residential_rate']), 4),
            "commercial_rate": round(float(row['commercial_rate']), 4) if pd.notna(row['commercial_rate']) else None,
            "industrial_rate": round(float(row['industrial_rate']), 4) if pd.notna(row['industrial_rate']) else None,
        })

    return utils_list

