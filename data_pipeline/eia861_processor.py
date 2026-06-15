"""
EIA-861 Data Processor — Clean, Normalize, and Merge raw EIA-861 sub-datasets.

Transforms 7 messy multi-row-header CSVs into clean, snake_case output files:
  1. sales_clean.csv              — benchmark price/consumption
  2. net_metering_clean.csv       — utility-level NM adoption
  3. demand_response_clean.csv    — binary state-level flag
  4. dynamic_pricing_clean.csv    — binary state-level flag
  5. net_metering_state_clean.csv — state-level NM adoption
  6. operational_clean.csv        — peak demand / load
  7. service_territory_clean.csv  — geo mapping
  8. eia861_master_clean.csv      — final merged dataset

Usage:
    python -m data_pipeline.eia861_processor
    python -m data_pipeline.eia861_processor --force
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "eia861_master_data"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "eia861"


def _safe_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to numeric, coercing '.' and other placeholders to NaN."""
    return pd.to_numeric(series.replace({".": np.nan, "": np.nan, " ": np.nan}), errors="coerce")


# ═════════════════════════════════════════════════════════════════════════════
#  7.6 Sales_Ult_Cust_master (CORE DATASET)
# ═════════════════════════════════════════════════════════════════════════════

def process_sales(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Sales_Ult_Cust_master.csv → sales_clean.csv

    Multi-row header: row 0 = sector group labels, row 1 = real column names.
    We skip row 0 and use row 1 as the actual header.
    """
    path = path or RAW_DIR / "Sales_Ult_Cust_master.csv"
    logger.info(f"Processing Sales: {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    # Row 0 is the sector-group label row (RESIDENTIAL, COMMERCIAL, TOTAL, etc.)
    # Row 1 is the actual header row with real column names
    # Data starts at row 2+
    header_row = raw.iloc[1]  # This is the real header with column names
    group_row = raw.iloc[0]   # Sector-group labels
    data = raw.iloc[2:].reset_index(drop=True)

    # Build column name mapping from header_row
    # The columns we need from row 1 are: Data Year, Utility Number, Utility Name, State
    # And the TOTAL section: Thousand Dollars, Megawatthours, Count
    col_names = header_row.values.tolist()

    # Find positions of key columns
    year_col = None
    utility_num_col = None
    utility_name_col = None
    state_col = None

    for i, val in enumerate(col_names):
        v = str(val).strip()
        if v == "Data Year":
            year_col = raw.columns[i]
        elif v == "Utility Number":
            utility_num_col = raw.columns[i]
        elif v == "Utility Name":
            utility_name_col = raw.columns[i]
        elif v == "State":
            state_col = raw.columns[i]

    # Find TOTAL section columns (Revenue, Sales, Customers)
    # In the original raw columns, "TOTAL" is one of the named columns
    # The subsequent unnamed columns after it hold: Revenue (Thousand Dollars), Sales (Megawatthours), Customers (Count)
    total_idx = None
    for i, c in enumerate(raw.columns):
        if c == "TOTAL":
            total_idx = i
            break

    if total_idx is None:
        raise ValueError("Could not find TOTAL section in Sales data")

    # TOTAL section has 3 sub-columns: Revenue, Sales, Customers
    total_rev_col = raw.columns[total_idx]      # TOTAL
    total_sales_col = raw.columns[total_idx + 1]  # Unnamed after TOTAL
    total_cust_col = raw.columns[total_idx + 2]   # Unnamed after that

    df = pd.DataFrame({
        "year": _safe_numeric(data[year_col]),
        "utility_id": _safe_numeric(data[utility_num_col]),
        "utility_name": data[utility_name_col],
        "state": data[state_col],
        "total_revenue_k": _safe_numeric(data[total_rev_col]),
        "total_sales_mwh": _safe_numeric(data[total_sales_col]),
        "total_customers": _safe_numeric(data[total_cust_col]),
    })

    # Drop rows where year is NaN (sub-header remnants)
    df = df.dropna(subset=["year", "utility_id", "state"]).copy()
    df["year"] = df["year"].astype(int)
    df["utility_id"] = df["utility_id"].astype(int)

    # Convert revenue from thousands to dollars
    df["total_revenue"] = df["total_revenue_k"] * 1000
    df.drop(columns=["total_revenue_k"], inplace=True)

    # Aggregate by (year, utility_id, state) to avoid duplicates from multiple service types
    df = df.groupby(["year", "utility_id", "state"], as_index=False).agg({
        "utility_name": "first",
        "total_revenue": "sum",
        "total_sales_mwh": "sum",
        "total_customers": "sum",
    })

    # Compute avg_price ($/MWh → can also express as $/kWh by dividing by 1000)
    df["avg_price"] = np.where(
        df["total_sales_mwh"] > 0,
        df["total_revenue"] / df["total_sales_mwh"],
        np.nan
    )

    # Reorder
    df = df[["year", "utility_id", "utility_name", "state",
             "total_revenue", "total_sales_mwh", "total_customers", "avg_price"]]

    logger.info(f"  Sales: {len(df)} rows, {df['year'].nunique()} years, {df['state'].nunique()} states")
    return df


# ═════════════════════════════════════════════════════════════════════════════
#  7.4 Net Metering — Utility Level
# ═════════════════════════════════════════════════════════════════════════════

def process_net_metering_utility(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Net_Metering_net_metering_states_master.csv → net_metering_clean.csv

    Multi-row header with technology groups (Photovoltaic, Wind, Other, Total).
    We only want the Total/All_Technologies columns for Customers and Energy Sold Back.
    """
    path = path or RAW_DIR / "Net_Metering_net_metering_states_master.csv"
    logger.info(f"Processing Net Metering (Utility): {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    # Row 0 = metric group labels (Capacity MW, Customers, Energy Sold Back MWh, ...)
    # Row 1 = sub-labels (Year, Utility Number, State, Residential, Commercial, ..., Total)
    header_row = raw.iloc[1]
    group_row = raw.iloc[0]
    data = raw.iloc[2:].reset_index(drop=True)
    col_names = header_row.values.tolist()

    # Find identity columns from header_row
    year_col = utility_num_col = state_col = None
    for i, val in enumerate(col_names):
        v = str(val).strip()
        if v == "Data Year" or v == "Year":
            year_col = raw.columns[i]
        elif v == "Utility Number":
            utility_num_col = raw.columns[i]
        elif v == "State":
            state_col = raw.columns[i]

    # Find the Total/All_Technologies section
    # Look for 'Total' or 'All_Technologies' in the raw column names
    total_start = None
    for col_name in ["All_Technologies", "Total"]:
        if col_name in raw.columns:
            total_start = list(raw.columns).index(col_name)
            break

    if total_start is None:
        logger.warning("Could not find Total/All_Technologies section in Net Metering utility data")
        # Return empty
        return pd.DataFrame(columns=["year", "utility_id", "state", "nm_customers", "nm_energy_mwh"])

    # In the Total section, find "Customers" → Total sub-column and "Energy Sold Back" → Total sub-column
    # The metric groups repeat: Capacity MW, Customers, Energy Sold Back MWh
    # Each has 5 sub-cols: Residential, Commercial, Industrial, Transportation, Total
    # So from total_start: Capacity(5) + Customers(5) + Energy Sold Back(5) = 15 cols

    # Row 0 at total_start region tells us what metric group each col belongs to
    # Let's find the Customers→Total and Energy Sold Back→Total
    nm_customers_col = None
    nm_energy_col = None

    # From the raw header row (row 0), the Total section repeats the metric patterns
    # Scan through the Total section looking for "Total" in row 1 (the sub-label row)
    # which corresponds to the aggregate across sectors
    total_section_cols = list(raw.columns[total_start:])

    # In the header_row (row 0 of data), find the indices where we have
    # "Installations"→Total and "Energy Sold Back MWh"→Total
    metric_in_section = None
    for idx_offset, col_key in enumerate(total_section_cols):
        metric_label = str(raw.iloc[0].iloc[total_start + idx_offset]).strip()
        sector_label = str(header_row.iloc[total_start + idx_offset]).strip()

        if "nan" in metric_label.lower():
            # Carry forward the last seen metric
            pass
        else:
            metric_in_section = metric_label

        if sector_label == "Total" or sector_label == "Total ":
            if metric_in_section and ("Installations" in str(metric_in_section) or "Customers" in str(metric_in_section)):
                nm_customers_col = raw.columns[total_start + idx_offset]
            elif metric_in_section and "Energy Sold Back" in str(metric_in_section):
                nm_energy_col = raw.columns[total_start + idx_offset]

    # Fallback: if we didn't find them precisely, use positional approach
    # Total section: Capacity(5) + Installations(5) + Energy Sold Back(5)
    if nm_customers_col is None and len(total_section_cols) >= 10:
        nm_customers_col = total_section_cols[9]  # Installations→Total (pos 5+4=9)
        logger.info("  Using positional fallback for nm_customers_col")
    if nm_energy_col is None and len(total_section_cols) >= 15:
        nm_energy_col = total_section_cols[14]     # Energy Sold Back→Total (pos 10+4=14)
        logger.info("  Using positional fallback for nm_energy_col")

    df = pd.DataFrame({
        "year": _safe_numeric(data[year_col]) if year_col else np.nan,
        "utility_id": _safe_numeric(data[utility_num_col]) if utility_num_col else np.nan,
        "state": data[state_col] if state_col else np.nan,
        "nm_customers": _safe_numeric(data[nm_customers_col]) if nm_customers_col else np.nan,
        "nm_energy_mwh": _safe_numeric(data[nm_energy_col]) if nm_energy_col else np.nan,
    })

    df = df.dropna(subset=["year", "utility_id", "state"]).copy()
    df["year"] = df["year"].astype(int)
    df["utility_id"] = df["utility_id"].astype(int)

    # Aggregate across any duplicate utility/year rows (shouldn't be many)
    df = df.groupby(["year", "utility_id", "state"], as_index=False).agg({
        "nm_customers": "sum",
        "nm_energy_mwh": "sum",
    })

    logger.info(f"  Net Metering Utility: {len(df)} rows")
    return df


# ═════════════════════════════════════════════════════════════════════════════
#  7.1 Demand Response (States)
# ═════════════════════════════════════════════════════════════════════════════

def process_demand_response(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Demand_Response_demand_response_states_master.csv → demand_response_clean.csv

    Binary flag: demand_response_flag = 1 if any utility in state/year has enrolled customers.
    """
    path = path or RAW_DIR / "Demand_Response_demand_response_states_master.csv"
    logger.info(f"Processing Demand Response: {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    # Row 0 = metric group labels, Row 1 = real column headers
    header_row = raw.iloc[1]
    group_row = raw.iloc[0]
    data = raw.iloc[2:].reset_index(drop=True)
    col_names = header_row.values.tolist()

    # Find identity columns
    year_col = state_col = total_enrolled_col = None
    for i, val in enumerate(col_names):
        v = str(val).strip()
        if v == "Data Year":
            year_col = raw.columns[i]
        elif v == "State":
            state_col = raw.columns[i]
        elif v == "Total":
            # First "Total" in the header row is Number of Customers Enrolled→Total
            if total_enrolled_col is None:
                total_enrolled_col = raw.columns[i]

    df = pd.DataFrame({
        "year": _safe_numeric(data[year_col]),
        "state": data[state_col],
        "enrolled_total": _safe_numeric(data[total_enrolled_col]) if total_enrolled_col else 0,
    })

    df = df.dropna(subset=["year", "state"]).copy()
    df["year"] = df["year"].astype(int)
    df["enrolled_total"] = df["enrolled_total"].fillna(0)

    # Binary flag: 1 if any utility in state/year has customers > 0
    df["demand_response_flag"] = (df["enrolled_total"] > 0).astype(int)

    result = df.groupby(["year", "state"], as_index=False)["demand_response_flag"].max()

    logger.info(f"  Demand Response: {len(result)} rows, {result['demand_response_flag'].sum()} active")
    return result


# ═════════════════════════════════════════════════════════════════════════════
#  7.2 Dynamic Pricing (States)
# ═════════════════════════════════════════════════════════════════════════════

def process_dynamic_pricing(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Dynamic_Pricing_dynamic_pricing_states_master.csv → dynamic_pricing_clean.csv

    Binary flag: dynamic_pricing_flag = 1 if any utility in state/year has enrolled customers.
    """
    path = path or RAW_DIR / "Dynamic_Pricing_dynamic_pricing_states_master.csv"
    logger.info(f"Processing Dynamic Pricing: {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    # Row 0 = metric group labels, Row 1 = real column names
    header_row = raw.iloc[1]
    group_row = raw.iloc[0]
    data = raw.iloc[2:].reset_index(drop=True)
    col_names = header_row.values.tolist()

    # Find identity columns
    year_col = state_col = total_enrolled_col = None
    for i, val in enumerate(col_names):
        v = str(val).strip()
        if v == "Data Year":
            year_col = raw.columns[i]
        elif v == "State":
            state_col = raw.columns[i]
        elif v == "Total":
            # First "Total" = Customers Enrolled→Total
            if total_enrolled_col is None:
                total_enrolled_col = raw.columns[i]

    df = pd.DataFrame({
        "year": _safe_numeric(data[year_col]),
        "state": data[state_col],
        "enrolled_total": _safe_numeric(data[total_enrolled_col]) if total_enrolled_col else 0,
    })

    df = df.dropna(subset=["year", "state"]).copy()
    df["year"] = df["year"].astype(int)
    df["enrolled_total"] = df["enrolled_total"].fillna(0)

    df["dynamic_pricing_flag"] = (df["enrolled_total"] > 0).astype(int)

    result = df.groupby(["year", "state"], as_index=False)["dynamic_pricing_flag"].max()

    logger.info(f"  Dynamic Pricing: {len(result)} rows, {result['dynamic_pricing_flag'].sum()} active")
    return result


# ═════════════════════════════════════════════════════════════════════════════
#  7.3 Net Metering — State Level
# ═════════════════════════════════════════════════════════════════════════════

def process_net_metering_state(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Net_Metering_states_state_level_master.csv → net_metering_state_clean.csv

    State-level net metering adoption signal: total customers across all technologies.
    Same multi-row header structure as the utility-level file.
    """
    path = path or RAW_DIR / "Net_Metering_states_state_level_master.csv"
    logger.info(f"Processing Net Metering (State): {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    # Row 0 = metric group, Row 1 = sub-labels
    header_row = raw.iloc[1]
    group_row = raw.iloc[0]
    data = raw.iloc[2:].reset_index(drop=True)
    col_names = header_row.values.tolist()

    # Find identity columns
    year_col = state_col = None
    for i, val in enumerate(col_names):
        v = str(val).strip()
        if v == "Year" or v == "Data Year":
            year_col = raw.columns[i]
        elif v == "State":
            state_col = raw.columns[i]

    # Find All_Technologies or Total section → Installations → Total
    total_start = None
    for col_name in ["All_Technologies", "Total"]:
        if col_name in raw.columns:
            total_start = list(raw.columns).index(col_name)
            break

    nm_customers_col = None
    if total_start is not None:
        total_section_cols = list(raw.columns[total_start:])
        metric_in_section = None
        for idx_offset, col_key in enumerate(total_section_cols):
            metric_label = str(raw.iloc[0].iloc[total_start + idx_offset]).strip()
            sector_label = str(header_row.iloc[total_start + idx_offset]).strip()

            if "nan" in metric_label.lower():
                pass
            else:
                metric_in_section = metric_label

            if sector_label == "Total" or sector_label == "Total ":
                if metric_in_section and ("Installations" in str(metric_in_section) or "Customers" in str(metric_in_section)):
                    nm_customers_col = raw.columns[total_start + idx_offset]
                    break

        if nm_customers_col is None and len(total_section_cols) >= 10:
            nm_customers_col = total_section_cols[9]

    df = pd.DataFrame({
        "year": _safe_numeric(data[year_col]) if year_col else np.nan,
        "state": data[state_col] if state_col else np.nan,
        "nm_state_customers": _safe_numeric(data[nm_customers_col]) if nm_customers_col else np.nan,
    })

    df = df.dropna(subset=["year", "state"]).copy()
    df["year"] = df["year"].astype(int)
    df["nm_state_customers"] = df["nm_state_customers"].fillna(0)

    # Aggregate by state/year (should already be one row per state per year)
    result = df.groupby(["year", "state"], as_index=False)["nm_state_customers"].sum()

    logger.info(f"  Net Metering State: {len(result)} rows")
    return result


# ═════════════════════════════════════════════════════════════════════════════
#  7.5 Operational Data
# ═════════════════════════════════════════════════════════════════════════════

def process_operational(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Operational_Data_master.csv → operational_clean.csv

    Extract peak demand (MW) and total load (retail sales MWh) per utility.
    """
    path = path or RAW_DIR / "Operational_Data_master.csv"
    logger.info(f"Processing Operational Data: {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    # Row 0 = section labels (Demand, Energy Sources, Disposition, Revenue)
    # Row 1 = real column names
    header_row = raw.iloc[1]
    group_row = raw.iloc[0]
    data = raw.iloc[2:].reset_index(drop=True)
    col_names = header_row.values.tolist()

    # Find identity columns
    year_col = utility_num_col = state_col = None
    peak_demand_col = total_load_col = None

    for i, val in enumerate(col_names):
        v = str(val).strip()
        if v == "Data Year":
            year_col = raw.columns[i]
        elif v == "Utility Number":
            utility_num_col = raw.columns[i]
        elif v == "State":
            state_col = raw.columns[i]
        elif v == "Summer Peak Demand":
            peak_demand_col = raw.columns[i]
        elif v == "Retail Sales":
            total_load_col = raw.columns[i]

    df = pd.DataFrame({
        "year": _safe_numeric(data[year_col]),
        "utility_id": _safe_numeric(data[utility_num_col]),
        "state": data[state_col],
        "peak_demand": _safe_numeric(data[peak_demand_col]) if peak_demand_col else np.nan,
        "total_load": _safe_numeric(data[total_load_col]) if total_load_col else np.nan,
    })

    df = df.dropna(subset=["year", "utility_id", "state"]).copy()
    df["year"] = df["year"].astype(int)
    df["utility_id"] = df["utility_id"].astype(int)

    # Aggregate by (year, utility_id, state) to avoid duplicates
    df = df.groupby(["year", "utility_id", "state"], as_index=False).agg({
        "peak_demand": "max",
        "total_load": "sum"
    })

    logger.info(f"  Operational: {len(df)} rows")
    return df


# ═════════════════════════════════════════════════════════════════════════════
#  7.7 Service Territory
# ═════════════════════════════════════════════════════════════════════════════

def process_service_territory(path: Path | None = None) -> pd.DataFrame:
    """
    Clean Service_Territory_counties_states_master.csv → service_territory_clean.csv

    Already has clean headers. Just rename and deduplicate.
    """
    path = path or RAW_DIR / "Service_Territory_counties_states_master.csv"
    logger.info(f"Processing Service Territory: {path.name}")

    raw = pd.read_csv(path, low_memory=False)

    df = pd.DataFrame({
        "utility_id": _safe_numeric(raw["Utility_Number"]),
        "state": raw["State"],
        "county": raw["County"],
    })

    df = df.dropna(subset=["utility_id", "state"]).copy()
    df["utility_id"] = df["utility_id"].astype(int)

    # Deduplicate
    df = df.drop_duplicates(subset=["utility_id", "state", "county"]).reset_index(drop=True)

    logger.info(f"  Service Territory: {len(df)} rows, {df['state'].nunique()} states")
    return df


# ═════════════════════════════════════════════════════════════════════════════
#  MASTER ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════

def process_all(force: bool = False) -> pd.DataFrame:
    """
    Run all 7 sub-processors, save individual CSVs, and produce the final merge.

    Final merge:
        sales_clean
        LEFT JOIN net_metering_clean USING (year, utility_id)
        LEFT JOIN operational_clean USING (year, utility_id)
        LEFT JOIN demand_response_clean USING (year, state)
        LEFT JOIN dynamic_pricing_clean USING (year, state)
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    master_path = OUT_DIR / "eia861_master_clean.csv"
    if master_path.exists() and not force:
        logger.info(f"EIA-861 master already exists at {master_path} — skipping (use --force)")
        return pd.read_csv(master_path)

    logger.info("=" * 70)
    logger.info("EIA-861 FULL PROCESSING PIPELINE")
    logger.info("=" * 70)

    # 1. Process each sub-dataset
    sales_df = process_sales()
    sales_df.to_csv(OUT_DIR / "sales_clean.csv", index=False)

    nm_utility_df = process_net_metering_utility()
    nm_utility_df.to_csv(OUT_DIR / "net_metering_clean.csv", index=False)

    dr_df = process_demand_response()
    dr_df.to_csv(OUT_DIR / "demand_response_clean.csv", index=False)

    dp_df = process_dynamic_pricing()
    dp_df.to_csv(OUT_DIR / "dynamic_pricing_clean.csv", index=False)

    nm_state_df = process_net_metering_state()
    nm_state_df.to_csv(OUT_DIR / "net_metering_state_clean.csv", index=False)

    ops_df = process_operational()
    ops_df.to_csv(OUT_DIR / "operational_clean.csv", index=False)

    svc_df = process_service_territory()
    svc_df.to_csv(OUT_DIR / "service_territory_clean.csv", index=False)

    # 2. Merge
    logger.info("Merging datasets...")

    final = sales_df.copy()

    # LEFT JOIN net_metering_clean on (year, utility_id, state)
    final = final.merge(
        nm_utility_df[["year", "utility_id", "state", "nm_customers", "nm_energy_mwh"]],
        on=["year", "utility_id", "state"],
        how="left",
    )

    # LEFT JOIN operational_clean on (year, utility_id, state)
    final = final.merge(
        ops_df[["year", "utility_id", "state", "peak_demand", "total_load"]],
        on=["year", "utility_id", "state"],
        how="left",
    )

    # LEFT JOIN demand_response_clean on (year, state)
    final = final.merge(
        dr_df[["year", "state", "demand_response_flag"]],
        on=["year", "state"],
        how="left",
    )

    # LEFT JOIN dynamic_pricing_clean on (year, state)
    final = final.merge(
        dp_df[["year", "state", "dynamic_pricing_flag"]],
        on=["year", "state"],
        how="left",
    )

    # Fill NaN flags with 0
    final["demand_response_flag"] = final["demand_response_flag"].fillna(0).astype(int)
    final["dynamic_pricing_flag"] = final["dynamic_pricing_flag"].fillna(0).astype(int)
    final["nm_customers"] = final["nm_customers"].fillna(0)
    final["nm_energy_mwh"] = final["nm_energy_mwh"].fillna(0)

    # Save
    final.to_csv(master_path, index=False)

    logger.info("=" * 70)
    logger.info(f"EIA-861 MASTER: {final.shape[0]} rows × {final.shape[1]} cols")
    logger.info(f"Years: {sorted(final['year'].unique().tolist())}")
    logger.info(f"States: {final['state'].nunique()}")
    logger.info(f"Saved to: {master_path}")
    logger.info("=" * 70)

    return final


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )

    parser = argparse.ArgumentParser(description="Process EIA-861 master datasets")
    parser.add_argument("--force", action="store_true", help="Re-process even if output exists")
    args = parser.parse_args()

    result = process_all(force=args.force)
    print(f"\nDone! Final dataset: {result.shape[0]} rows × {result.shape[1]} columns")
    print(f"Columns: {list(result.columns)}")
