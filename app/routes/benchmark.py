"""
POST /benchmark — compare electricity rates across US states.
"""
import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
benchmark_bp = Blueprint("benchmark", __name__)


@benchmark_bp.post("/benchmark")
def state_benchmark():
    """Compare electricity rates across US states."""
    svc = current_app.extensions["svc"]
    if svc.benchmark_df is None:
        return jsonify({"error": "Benchmark data not loaded"}), 503

    body = request.get_json(silent=True) or {}

    # ── Validate ─────────────────────────────────────────────────────────────
    try:
        year = int(body.get("year", 2025))
        if not (2019 <= year <= 2026):
            return jsonify({"error": "year must be between 2019 and 2026"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "year must be an integer"}), 400

    compare_state = body.get("compare_state", "NJ")
    if not isinstance(compare_state, str) or len(compare_state) != 2:
        return jsonify({"error": "compare_state must be a 2-letter abbreviation"}), 400

    year_data = svc.benchmark_df[svc.benchmark_df["year"] == year].copy()
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
            "state":    row["state"],
            "avg_rate": round(row["avg_rate"], 4),
            "avg_bill": round(row["avg_bill"], 2),
            "rank":     int(row["rank"]),
        }
        for _, row in year_data.iterrows()
    ]

    return jsonify({
        "year": year,
        "focus_state": {
            "state":    focus_row["state"],
            "avg_rate": round(focus_row["avg_rate"], 4),
            "avg_bill": round(focus_row["avg_bill"], 2),
            "rank":     int(focus_row["rank"]),
        },
        "national_avg": round(year_data["avg_rate"].mean(), 4),
        "states":       states,
    })
