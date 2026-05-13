"""
Global application state — shared between the lifespan handler and all routes.
Populated once at startup, read-only during request handling.
"""

app_state: dict = {
    "billing_df": None,
    "weather_df": None,
    "market_df": None,
    "benchmark_df": None,
    "plans_df": None,
    "impact_model": None,
    "forecast_model": None,
    "feature_matrix": None,
    "feature_cols": None,
    "geo_monthly_df": None,
}
