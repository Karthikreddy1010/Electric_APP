"""
Validators — Data quality validation checks for the pipeline.
"""
import logging
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)


def check_missing_values(df: pd.DataFrame, name: str, threshold: float = 0.1) -> dict:
    """Check for missing values exceeding the threshold."""
    if df.empty:
        return {}

    missing_pct = df.isna().mean()
    high_missing = missing_pct[missing_pct > threshold]
    
    if not high_missing.empty:
        logger.warning(f"[{name}] Columns exceeding {threshold*100}% missing values:")
        for col, pct in high_missing.items():
            logger.warning(f"  - {col}: {pct*100:.1f}%")
            
    return missing_pct.to_dict()


def check_duplicates(df: pd.DataFrame, name: str, subset: list = None) -> int:
    """Check for duplicate rows."""
    if df.empty:
        return 0

    dupes = df.duplicated(subset=subset).sum()
    if dupes > 0:
        logger.warning(f"[{name}] Found {dupes} duplicate rows" + 
                       (f" (subset: {subset})" if subset else ""))
    return int(dupes)


def check_year_coverage(datasets: dict) -> dict:
    """Ensure consistency of year ranges across key datasets."""
    coverage = {}
    for name, df in datasets.items():
        if df is not None and not df.empty and "year" in df.columns:
            min_year_val = df["year"].min()
            max_year_val = df["year"].max()
            if pd.isna(min_year_val) or pd.isna(max_year_val):
                logger.warning(f"[{name}] Year column contains all NaNs or is missing valid years.")
                continue
                
            min_year = int(min_year_val)
            max_year = int(max_year_val)
            coverage[name] = (min_year, max_year)
            logger.info(f"[{name}] Coverage: {min_year} - {max_year}")
    
    return coverage


def validate_merge(df_before: pd.DataFrame, df_after: pd.DataFrame, name: str, tolerance: float = 0.05) -> None:
    """Ensure merges don't drop or explode rows unexpectedly."""
    rows_before = len(df_before)
    rows_after = len(df_after)
    
    if rows_before == 0:
        return

    diff_pct = abs(rows_after - rows_before) / rows_before
    
    if diff_pct > tolerance:
        logger.warning(f"[{name}] Merge resulted in large row count change: "
                       f"{rows_before} -> {rows_after} ({diff_pct*100:.1f}% change)")


def run_all_validations(datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Run all validation checks on the processed datasets."""
    logger.info("=" * 70)
    logger.info("STAGE 4: Validating Datasets")
    logger.info("=" * 70)
    
    report = {}
    
    # Check coverage
    report["coverage"] = check_year_coverage(datasets)
    
    # Check missing & dupes
    for name, df in datasets.items():
        if df is not None and not df.empty:
            missing = check_missing_values(df, name)
            dupes = check_duplicates(df, name)
            report[name] = {"missing": missing, "duplicates": dupes}
            
    logger.info("Validation complete.")
    return report
