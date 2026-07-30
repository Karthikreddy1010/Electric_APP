"""
Global Data Validation & Quality Control Engine
Performs automatic quality checks: missing values, schema drift, invalid codes, negative values, data freshness.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

VALID_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY", "US"
}

VALID_SECTORS = {"ALL", "COM", "IND", "OTH", "RES", "TRA"}


class ValidationReport:
    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.total_rows = 0
        self.missing_values: Dict[str, int] = {}
        self.invalid_state_codes: List[str] = []
        self.invalid_sectors: List[str] = []
        self.negative_value_counts: Dict[str, int] = {}
        self.duplicate_count = 0
        self.schema_valid = True
        self.data_freshness_period = ""
        self.is_passed = True
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "total_rows": self.total_rows,
            "missing_values": self.missing_values,
            "invalid_state_codes_count": len(self.invalid_state_codes),
            "invalid_sectors_count": len(self.invalid_sectors),
            "negative_value_counts": self.negative_value_counts,
            "duplicate_count": self.duplicate_count,
            "schema_valid": self.schema_valid,
            "data_freshness_period": self.data_freshness_period,
            "is_passed": self.is_passed,
            "warnings": self.warnings,
        }


def validate_eia_retail_dataframe(df: pd.DataFrame) -> ValidationReport:
    """Performs rigorous quality audit on EIA Retail DataFrame."""
    report = ValidationReport("EIA Retail")
    report.total_rows = len(df)

    if df.empty:
        report.is_passed = False
        report.warnings.append("DataFrame is empty!")
        return report

    # 1. Required Schema Check
    required_cols = ["period", "stateid", "sectorid", "retail_price", "retail_sales", "retail_revenue", "retail_customers"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        report.schema_valid = False
        report.is_passed = False
        report.warnings.append(f"Missing required columns: {missing_cols}")

    # 2. Missing Values Count
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            report.missing_values[col] = null_count
            if null_count > len(df) * 0.1:  # Warning if > 10% nulls
                report.warnings.append(f"Column '{col}' has high null count: {null_count}")

    # 3. Invalid State Codes Check
    if "stateid" in df.columns:
        states = set(df["stateid"].dropna().unique())
        invalid_states = states - VALID_US_STATES
        if invalid_states:
            report.invalid_state_codes = list(invalid_states)
            report.warnings.append(f"Found invalid state codes: {invalid_states}")

    # 4. Invalid Sectors Check
    if "sectorid" in df.columns:
        sectors = set(df["sectorid"].dropna().unique())
        invalid_sec = sectors - VALID_SECTORS
        if invalid_sec:
            report.invalid_sectors = list(invalid_sec)
            report.warnings.append(f"Found invalid sector ids: {invalid_sec}")

    # 5. Negative Values Check
    num_cols = ["retail_price", "retail_sales", "retail_revenue", "retail_customers"]
    for col in num_cols:
        if col in df.columns:
            neg_count = int((df[col] < 0).sum())
            if neg_count > 0:
                report.negative_value_counts[col] = neg_count
                report.warnings.append(f"Column '{col}' contains {neg_count} negative values")

    # 6. Duplicate Primary Key Check
    if {"period", "stateid", "sectorid"}.issubset(df.columns):
        dups = int(df.duplicated(subset=["period", "stateid", "sectorid"]).sum())
        report.duplicate_count = dups
        if dups > 0:
            report.is_passed = False
            report.warnings.append(f"Found {dups} duplicate PK rows (period, stateid, sectorid)")

    # 7. Data Freshness Check
    if "period" in df.columns and not df["period"].empty:
        report.data_freshness_period = str(df["period"].max())

    logger.info(f"EIA Retail validation finished: Passed={report.is_passed}, Warnings={len(report.warnings)}")
    return report
