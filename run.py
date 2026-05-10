"""
Run script: generates data, trains models, and starts the API server.
Usage: python run.py
"""
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("electric-ai")

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

    # Step 2: Start FastAPI server
    logger.info("=" * 60)
    logger.info("STEP 2: Starting API server...")
    logger.info("=" * 60)
    logger.info("  API docs: http://localhost:8000/docs")
    logger.info("  Frontend: open frontend/index.html in browser")
    logger.info("=" * 60)

    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
