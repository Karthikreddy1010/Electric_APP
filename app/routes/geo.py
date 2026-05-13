"""
Geo analytics endpoints:
  GET /geo-lookup       — ZIP → county + estimated bill
  GET /geo-all-counties — all 21 NJ counties with bill estimates
"""
import logging

from flask import Blueprint, jsonify, request, current_app

geo_bp = Blueprint("geo", __name__)
logger = logging.getLogger(__name__)


@geo_bp.route("/geo-lookup", methods=["GET"])
def geo_lookup():
    """Map ZIP code to NJ county and estimate local bill."""
    from shared.geo_analytics import zip_to_county, estimate_county_bill

    zip_code = request.args.get("zip_code", "").strip()
    if not zip_code or len(zip_code) != 5:
        return jsonify({"error": "zip_code must be a 5-digit string"}), 422

    county = zip_to_county(zip_code)
    if county is None:
        return jsonify({"error": f"ZIP {zip_code} not found in NJ"}), 404

    billing = current_app.config.get("BILLING_DF")
    base_bill = float(billing.iloc[-1]["total_bill"]) if billing is not None else 150.0
    estimate = estimate_county_bill(base_bill, county)
    return jsonify(estimate)


@geo_bp.route("/geo-all-counties", methods=["GET"])
def geo_all_counties():
    """Get bill estimates for all 21 NJ counties."""
    from shared.geo_analytics import get_all_county_estimates

    billing = current_app.config.get("BILLING_DF")
    base_bill = float(billing.iloc[-1]["total_bill"]) if billing is not None else 150.0
    df = get_all_county_estimates(base_bill)
    return jsonify(df.to_dict(orient="records"))
