"""
Flask Application Factory
==========================
Creates and configures the Flask app with:
  - Blueprint registration for modular routes
  - CORS middleware
  - Centralized error handling
  - Data/model initialization on startup (no per-request training)
  - Static frontend serving
"""
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify

# Ensure project root is on sys.path for module imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory — returns a fully configured Flask instance."""

    app = Flask(
        __name__,
        static_folder=str(PROJECT_ROOT / "frontend"),
        static_url_path="/static",
    )

    # ── Configuration ────────────────────────────────────────────────
    app.config.from_object("app.config.FlaskConfig")

    # ── CORS (permissive for dev — tighten in production) ────────────
    try:
        from flask_cors import CORS
        CORS(app, resources={r"/*": {"origins": "*"}})
    except ImportError:
        # Manual CORS via after_request if flask-cors not installed
        @app.after_request
        def _add_cors(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    # ── Centralized Error Handlers ───────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad Request", "detail": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not Found", "detail": str(e)}), 404

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "Validation Error", "detail": str(e)}), 422

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Internal server error")
        return jsonify({"error": "Internal Server Error", "detail": str(e)}), 500

    # ── Register Blueprints ──────────────────────────────────────────
    from app.routes.health import health_bp
    from app.routes.billing import billing_bp
    from app.routes.forecast import forecast_bp
    from app.routes.impact import impact_bp
    from app.routes.plans import plans_bp
    from app.routes.benchmark import benchmark_bp
    from app.routes.geo import geo_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(impact_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(benchmark_bp)
    app.register_blueprint(geo_bp)

    # ── Frontend Route ───────────────────────────────────────────────
    from flask import send_from_directory

    frontend_dir = PROJECT_ROOT / "frontend"
    if frontend_dir.exists():
        @app.route("/app")
        @app.route("/app/<path:filename>")
        def serve_frontend(filename="index.html"):
            return send_from_directory(str(frontend_dir), filename)

    # ── Startup: Load Data + Train Models ────────────────────────────
    _initialize_app_state(app)

    logger.info("Flask application created successfully")
    return app


# ═════════════════════════════════════════════════════════════════════
#  STARTUP INITIALIZATION (runs once — never inside a request)
# ═════════════════════════════════════════════════════════════════════

def _initialize_app_state(app: Flask) -> None:
    """
    Load datasets, run the cleaning/feature pipeline, and train
    forecast + impact models.  Results are stored in ``app.config``
    so every request handler can access them without re-computation.
    """
    data_dir = PROJECT_ROOT / "data" / "raw"

    # ── Step 1: Generate synthetic data if missing ───────────────────
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        logger.info("No data found — generating synthetic datasets …")
        from data_pipeline.synthetic_data import generate_all
        generate_all(str(data_dir))

    # ── Step 2: Load Parquet files ───────────────────────────────────
    import pandas as pd

    try:
        app.config["BILLING_DF"] = pd.read_parquet(data_dir / "billing.parquet")
        app.config["WEATHER_DF"] = pd.read_parquet(data_dir / "weather.parquet")
        app.config["MARKET_DF"] = pd.read_parquet(data_dir / "pjm_market.parquet")
        app.config["BENCHMARK_DF"] = pd.read_parquet(data_dir / "state_benchmark.parquet")
        app.config["PLANS_DF"] = pd.read_parquet(data_dir / "retail_plans.parquet")
        logger.info("All datasets loaded successfully")
    except Exception as e:
        logger.error(f"Data loading failed: {e}")

    # ── Step 3: Clean + feature-engineer, train Impact model ─────────
    try:
        from data_pipeline.cleaners import run_cleaning_pipeline
        from data_pipeline.features import build_feature_matrix
        from models.impact_model import BillImpactModel

        billing, weather, market = run_cleaning_pipeline(
            app.config["BILLING_DF"],
            app.config["WEATHER_DF"],
            app.config["MARKET_DF"],
        )
        df, feature_cols, target = build_feature_matrix(billing, weather, market)
        app.config["FEATURE_MATRIX"] = df
        app.config["FEATURE_COLS"] = feature_cols

        model = BillImpactModel()
        model.train(df[feature_cols], df[target])
        app.config["IMPACT_MODEL"] = model
        logger.info("Impact model trained and ready")
    except Exception as e:
        logger.warning(f"Impact model training failed: {e}")
        app.config.setdefault("IMPACT_MODEL", None)

    # ── Step 4: Train Forecast ensemble ──────────────────────────────
    try:
        from models.forecast_model import ForecastEnsemble

        billing_df = app.config["BILLING_DF"]
        ensemble = ForecastEnsemble()
        ensemble.train_all(billing_df["total_bill"], billing_df["date"])
        app.config["FORECAST_MODEL"] = ensemble
        logger.info("Forecast ensemble trained and ready")
    except Exception as e:
        logger.warning(f"Forecast model training failed: {e}")
        app.config.setdefault("FORECAST_MODEL", None)
