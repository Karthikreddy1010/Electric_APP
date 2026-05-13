"""POST /benchmark — state electricity rate comparison."""
from fastapi import APIRouter, HTTPException

from api.state import app_state
from api.schemas import BenchmarkRequest, BenchmarkResponse, StateData

router = APIRouter(tags=["benchmark"])


@router.post("/benchmark", response_model=BenchmarkResponse)
async def state_benchmark(req: BenchmarkRequest):
    """Compare electricity rates across US states."""
    bench_df = app_state["benchmark_df"]
    if bench_df is None:
        raise HTTPException(500, "Benchmark data not loaded")

    year_data = bench_df[bench_df["year"] == req.year].copy()
    if year_data.empty:
        raise HTTPException(404, f"No data for year {req.year}")

    year_data = year_data.sort_values("avg_rate")
    year_data["rank"] = range(1, len(year_data) + 1)

    focus = year_data[year_data["state"] == req.compare_state]
    if focus.empty:
        raise HTTPException(404, f"State {req.compare_state} not found")

    focus_row = focus.iloc[0]

    states = [
        StateData(
            state=row["state"],
            avg_rate=round(row["avg_rate"], 4),
            avg_bill=round(row["avg_bill"], 2),
            rank=int(row["rank"]),
        )
        for _, row in year_data.iterrows()
    ]

    return BenchmarkResponse(
        year=req.year,
        focus_state=StateData(
            state=focus_row["state"],
            avg_rate=round(focus_row["avg_rate"], 4),
            avg_bill=round(focus_row["avg_bill"], 2),
            rank=int(focus_row["rank"]),
        ),
        national_avg=round(year_data["avg_rate"].mean(), 4),
        states=states,
    )
