"""
run_flask.py — Entry point for the ElectricAI Flask application.

Usage:
    python run_flask.py                       # development (port 5000)
    python run_flask.py --port 8080           # custom port
    FLASK_ENV=production python run_flask.py  # production mode
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Ensure the project root is on the path before any local imports
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="ElectricAI Flask server")
    parser.add_argument("--host",  default="0.0.0.0",  help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port",  type=int, default=5000, help="Bind port (default: 5000)")
    parser.add_argument("--env",   default=os.getenv("FLASK_ENV", "development"),
                        choices=["development", "production", "default"],
                        help="Config environment")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    from app import create_app
    flask_app = create_app(env=args.env)

    logger.info(f"Starting ElectricAI on http://{args.host}:{args.port}  [env={args.env}]")
    flask_app.run(
        host=args.host,
        port=args.port,
        debug=(args.env == "development"),
        use_reloader=False,  # avoid double model training
    )
