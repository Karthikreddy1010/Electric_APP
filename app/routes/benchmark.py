"""
Benchmark endpoint:
  POST /benchmark — compare electricity rates across US states.
"""
import logging

from flask import Blueprint, jsonify, request, current_app

benchmark_bp = Blueprint("benchmark", __name__)
logger = logging.getLogger(__name__)


@benchmark_bp.route("/benchmark", methods=["POST"])
def state_benchmark():
    """Compare electricity rates across US states."""
    bench_df = current_app.config.get("BENCHMARK_DF")
    if bench_df is None:
        return jsonify({"error": "Benchmark data not loaded"}), 500

    body = request.get_json(silent=True) or {}

    # ── Manual validation ────────────────────────────────────────
    year = body.get("year", 2025)
    compare_state = body.get("compare_state", "NJ")

    if not isinstance(year, int) or not (2019 <= year <= 2026):
        return jsonify({"error": "year must be between 2019 and 2026"}), 422
    if not isinstance(compare_state, str) or len(compare_state) != 2:
        return jsonify({"error": "compare_state must be a 2-letter state abbreviation"}), 422

    year_data = bench_df[bench_df["year"] == year].copy()
    if year_data.empty:
        return jsonify({"error": f"No data for year {year}"}), 404

    year_data = year_data.sort_values("avg_rate")
    year_data["rank"] = range(1, len(year_data) + 1)

    focus = year_data[year_data["state"] == compare_state]
    if focus.empty:
        return jsonify({"error": f"State {compare_state} not found"}), 404

    focus_row = focus.iloc[0]

    states = [
        {
            "state": row["state"],
            "avg_rate": round(row["avg_rate"], 4),
            "avg_bill": round(row["avg_bill"], 2),
            "rank": int(row["rank"]),
        }
        for _, row in year_data.iterrows()
    ]

    return jsonify({
        "year": year,
        "focus_state": {
            "state": focus_row["state"],
            "avg_rate": round(focus_row["avg_rate"], 4),
            "avg_bill": round(focus_row["avg_bill"], 2),
            "rank": int(focus_row["rank"]),
        },
        "national_avg": round(year_data["avg_rate"].mean(), 4),
        "states": states,
    })
