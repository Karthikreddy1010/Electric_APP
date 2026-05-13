"""
run.py -- Entry point for the ElectricAI application.

Usage:
    python run.py                # development (port 8000)
    python run.py --port 9000    # custom port
"""
import sys
import logging
import argparse
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger("electric-ai")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="ElectricAI FastAPI server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable hot-reload")
    return parser.parse_args()


def main():
    args = parse_args()

    # Step 1: Ensure synthetic data exists
    data_dir = PROJECT_ROOT / "data" / "raw"
    if not data_dir.exists() or not list(data_dir.glob("*.parquet")):
        logger.info("=" * 60)
        logger.info("STEP 1: Generating synthetic data...")
        logger.info("=" * 60)
        from data_pipeline.synthetic_data import generate_all
        generate_all(str(data_dir))
    else:
        logger.info("Data already exists, skipping generation.")

    # Step 2: Start FastAPI server
    logger.info("=" * 60)
    logger.info(f"STEP 2: Starting FastAPI server on http://{args.host}:{args.port}")
    logger.info("=" * 60)
    logger.info(f"  API docs:  http://localhost:{args.port}/docs")
    logger.info(f"  Health:    http://localhost:{args.port}/health")
    logger.info(f"  Frontend:  http://localhost:{args.port}/app")
    logger.info("=" * 60)

    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
