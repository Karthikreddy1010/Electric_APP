"""
Pipeline Runner — Main orchestrator for the Data Ingestion Pipeline.

Combines loaders, fetchers, transformers, validators, and merger
into a single executable script.
"""
import logging
import argparse
from pathlib import Path

from data_pipeline.config import setup_logging, PROCESSED_DIR, OUTPUT_FILES
from data_pipeline.loaders import load_all_local
from data_pipeline.api_fetchers import fetch_bls_cpi
from data_pipeline.transformers import (
    preprocess_bgs_auction,
    preprocess_municipal_energy,
    preprocess_community_energy,
    preprocess_nj_retail_prices,
    preprocess_eia_residential_prices,
    preprocess_weather,
    preprocess_cpi
)
from data_pipeline.validators import run_all_validations
from data_pipeline.merger import build_master_dataset

logger = logging.getLogger(__name__)


def run_pipeline(force: bool = False) -> dict:
    """
    Run the full ingestion -> transform -> merge pipeline.
    
    Args:
        force: If True, re-process and re-fetch even if outputs exist.
        
    Returns:
        Dict mapping logical names to processed DataFrames.
    """
    setup_logging()
    logger.info("Starting Data Pipeline")
    
    # 1. Load Local Data
    datasets = load_all_local()
    
    # 2. Fetch API Data
    cpi_df = fetch_bls_cpi(force=force)
    datasets["cpi_monthly"] = cpi_df
    
    # 3. Preprocess / Transform
    logger.info("=" * 70)
    logger.info("STAGE 3: Preprocessing Datasets")
    logger.info("=" * 70)
    
    processed = {}
    
    if "bgs_auction" in datasets:
        processed["bgs_auction"] = preprocess_bgs_auction(datasets["bgs_auction"])
        
    if "municipal_energy" in datasets:
        processed["municipal_energy"] = preprocess_municipal_energy(datasets["municipal_energy"])
        
    if "community_energy" in datasets:
        processed["community_energy"] = preprocess_community_energy(datasets["community_energy"])
        
    if "nj_retail_prices" in datasets:
        processed["nj_retail_prices"] = preprocess_nj_retail_prices(datasets["nj_retail_prices"])
        
    if "eia_residential_prices" in datasets:
        processed["eia_residential_prices"] = preprocess_eia_residential_prices(datasets["eia_residential_prices"])
        
    if "weather" in datasets:
        processed["weather_monthly"] = preprocess_weather(datasets["weather"])
        
    if "cpi_monthly" in datasets:
        processed["cpi_monthly"] = preprocess_cpi(datasets["cpi_monthly"])

    # 4. Validate
    run_all_validations(processed)
    
    # 5. Merge (Master Dataset)
    master_df = build_master_dataset(processed)
    processed["master"] = master_df
    
    # 6. Save Outputs
    logger.info("=" * 70)
    logger.info("STAGE 6: Saving Outputs")
    logger.info("=" * 70)
    
    output_paths = {}
    
    for key, filename in OUTPUT_FILES.items():
        if key in processed and processed[key] is not None and not processed[key].empty:
            out_path = PROCESSED_DIR / filename
            
            if out_path.exists() and not force:
                logger.info(f"Skipping save for {filename} (already exists). Use --force to overwrite.")
                output_paths[key] = str(out_path)
            else:
                processed[key].to_csv(out_path, index=False)
                logger.info(f"Saved {filename} to {PROCESSED_DIR}")
                output_paths[key] = str(out_path)
    
    logger.info("Pipeline completed successfully.")
    return output_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Electricity Cost Data Pipeline")
    parser.add_argument("--force", action="store_true", help="Force re-fetch and re-process all data")
    args = parser.parse_args()
    
    run_pipeline(force=args.force)
