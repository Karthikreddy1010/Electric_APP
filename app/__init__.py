"""
Flask application factory.
All data loading and model training happen here — ONCE at startup.
Request handlers only read from app.extensions['svc'].
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# ── Ensure project root is on sys.path ───────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify

from app.config import get_config
from app.services.data_service import DataService

logger = logging.getLogger(__name__)


def create_app(env: str = "default") -> Flask:
    """
    Application factory.

    Parameters
    ----------
    env : "development" | "production" | "default"
    """
    config = get_config(env)

    app = Flask(
        __name__,
        static_folder=str(PROJECT_ROOT / "frontend"),
        static_url_path="/static",
    )
    app.config.from_object(config)

    # ── CORS ─────────────────────────────────────────────────────────────────
    try:
        from flask_cors import CORS
        CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)
    except ImportError:
        @app.after_request
        def _add_cors(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    # ── Initialize data & models (runs once at startup) ─────────────────────
    svc = DataService()
    try:
        svc.initialize(config.DATA_RAW_DIR)
    except Exception as exc:
        logger.error(f"DataService initialization failed: {exc}")
        # App still starts; endpoints will return 503 for data-dependent routes.

    app.extensions["svc"] = svc

    # ── Register blueprints ──────────────────────────────────────────────────
    from app.routes.health    import health_bp
    from app.routes.billing   import billing_bp
    from app.routes.forecast  import forecast_bp
    from app.routes.impact    import impact_bp
    from app.routes.plans     import plans_bp
    from app.routes.benchmark import benchmark_bp
    from app.routes.geo       import geo_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(impact_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(benchmark_bp)
    app.register_blueprint(geo_bp)

    # ── Frontend catch-all ───────────────────────────────────────────────────
    frontend_dir = PROJECT_ROOT / "frontend"
    if frontend_dir.exists():
        from flask import send_from_directory

        @app.route("/app")
        @app.route("/app/")
        @app.route("/app/<path:filename>")
        def serve_frontend(filename="index.html"):
            return send_from_directory(str(frontend_dir), filename)

    # ── Centralised error handlers ───────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(err):
        return jsonify({"error": "Bad Request", "detail": str(err)}), 400

    @app.errorhandler(404)
    def not_found(err):
        return jsonify({"error": "Not Found", "detail": str(err)}), 404

    @app.errorhandler(422)
    def unprocessable(err):
        return jsonify({"error": "Validation Error", "detail": str(err)}), 422

    @app.errorhandler(500)
    def internal(err):
        logger.exception("Unhandled 500")
        return jsonify({"error": "Internal Server Error", "detail": str(err)}), 500

    logger.info(f"Flask app created (env={env}, debug={config.DEBUG})")
    return app
