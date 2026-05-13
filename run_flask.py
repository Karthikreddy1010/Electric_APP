"""
Flask entry point — generates data (if needed) and starts the Flask server.
Usage: python run_flask.py
"""
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("electric-ai-flask")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    # Step 1: Generate synthetic data if not present
    data_dir = PROJECT_ROOT / "data" / "raw"
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        logger.info("=" * 60)
        logger.info("STEP 1: Generating synthetic data...")
        logger.info("=" * 60)
        from data_pipeline.synthetic_data import generate_all
        generate_all(str(data_dir))
    else:
        logger.info("Data already exists, skipping generation.")

    # Step 2: Start Flask server
    logger.info("=" * 60)
    logger.info("STEP 2: Starting Flask API server...")
    logger.info("=" * 60)
    logger.info("  API base:  http://localhost:5000")
    logger.info("  Health:    http://localhost:5000/health")
    logger.info("  Frontend:  http://localhost:5000/app")
    logger.info("=" * 60)

    from app import create_app
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,  # avoid double model training
    )


if __name__ == "__main__":
    main()
