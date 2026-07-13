"""
Historical Tariff Engine ETL Pipeline

Pipeline to ingest raw utility tariff CSVs, validate, clean, normalize using mapping files,
and load into the centralized Historical Utility Tariff database.
"""
import pandas as pd
import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

def run_tariff_etl(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run the ETL pipeline for historical tariffs.
    Returns (tariff_versions_df, historical_tariffs_df)
    """
    logger.info("Starting Tariff ETL Pipeline...")
    
    # 1. Ingestion
    raw_path = RAW_DIR / "PSEG_Component_Distribution_Rates.csv"
    mapping_path = PROJECT_ROOT / "tariff_component_mapping.csv"
    
    if not raw_path.exists():
        logger.error(f"Raw tariff file missing: {raw_path}")
        return pd.DataFrame(), pd.DataFrame()
        
    if not mapping_path.exists():
        logger.error(f"Mapping file missing: {mapping_path}")
        return pd.DataFrame(), pd.DataFrame()
        
    raw_df = pd.read_csv(raw_path)
    mapping_df = pd.read_csv(mapping_path)
    
    # 2. Validation
    required_cols = ["Tariff_Version", "Year", "Rate_Schedule", "Component_Label", "Base_Rate"]
    for col in required_cols:
        if col not in raw_df.columns:
            raise ValueError(f"Missing required column in raw tariff data: {col}")
            
    # 3. Cleaning
    df = raw_df.copy()
    df["Base_Rate"] = pd.to_numeric(df["Base_Rate"], errors="coerce")
    if "With_SUT" in df.columns:
        df["With_SUT"] = pd.to_numeric(df["With_SUT"], errors="coerce")
    else:
        df["With_SUT"] = df["Base_Rate"]
        
    # Standardize empty SUT fields to base rate
    df["With_SUT"] = df["With_SUT"].fillna(df["Base_Rate"])
    
    df = df.drop_duplicates()
    
    # 4. Normalization (Join with Mapping)
    merged = df.merge(mapping_df, left_on="Component_Label", right_on="Original Label", how="left")
    
    # Filter out unrelated boilerplate
    cleaned = merged[merged["Normalized Label"] != "unrelated_boilerplate"].copy()
    
    # Drop where Normalized Label is NaN or unknown
    cleaned = cleaned.dropna(subset=["Normalized Label"])
    cleaned = cleaned[cleaned["Normalized Label"] != "unknown"]
    
    # Standardize effective dates
    # For PSE&G, we'll approximate effective_start as Jan 1 of the given year, and end as Dec 31
    cleaned["effective_start"] = pd.to_datetime(cleaned["Year"].astype(str) + "-01-01")
    cleaned["effective_end"] = pd.to_datetime(cleaned["Year"].astype(str) + "-12-31")
    
    # 5. Prepare Output Tables
    # Table 1: TariffVersions
    versions = []
    unique_versions = cleaned[["Tariff_Version", "Year", "effective_start", "effective_end"]].drop_duplicates()
    
    # We will generate a unique key for the version based on utility + version + year
    for _, row in unique_versions.iterrows():
        versions.append({
            "utility_name": "Public Service Electric & Gas",
            "utility_code": "PSEG",
            "state": "NJ",
            "service_territory": "New Jersey",
            "regulator": "BPU",
            "tariff_version": f"{row['Tariff_Version']} ({row['Year']})",
            "description": f"Historical Tariff for {row['Year']}",
            "effective_start": row["effective_start"],
            "effective_end": row["effective_end"],
            "status": "historical",
            # We'll use a temporary key to join back
            "_join_key": f"{row['Tariff_Version']}_{row['Year']}"
        })
        
    versions_df = pd.DataFrame(versions)
    
    # Assign a surrogate ID starting from 1 for the ETL (seed.py will re-assign real IDs)
    versions_df["temp_version_id"] = range(1, len(versions_df) + 1)
    
    # Table 2: HistoricalUtilityTariffs
    cleaned["_join_key"] = cleaned["Tariff_Version"] + "_" + cleaned["Year"].astype(str)
    
    # Join to get temp_version_id
    rates_df = cleaned.merge(versions_df[["_join_key", "temp_version_id"]], on="_join_key", how="left")
    
    # Format Historical Tariffs
    hist_tariffs = pd.DataFrame({
        "temp_version_id": rates_df["temp_version_id"],
        "component": rates_df["Normalized Label"],
        "component_category": rates_df["Category"],
        "rate": rates_df["With_SUT"],  # Using With_SUT as the primary rate for simulations
        "unit": rates_df["Unit"],
        "schedule": rates_df["Rate_Schedule"],
        "season": np.where(rates_df["Original Label"].str.contains("Summer", case=False, na=False), "summer", "annual")
    })
    
    # Drop duplicates for identical normalized components (e.g., if multiple raw components map to customer_charge)
    # If they do, we sum them
    hist_tariffs = hist_tariffs.groupby(
        ["temp_version_id", "component", "component_category", "unit", "schedule", "season"]
    ).agg({"rate": "sum"}).reset_index()
    
    logger.info(f"ETL Complete: Generated {len(versions_df)} versions and {len(hist_tariffs)} rates.")
    
    # Clean up temp columns
    versions_df = versions_df.drop(columns=["_join_key"])
    
    return versions_df, hist_tariffs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    v, r = run_tariff_etl()
    print("Versions:")
    print(v.head())
    print("\nRates:")
    print(r.head())
