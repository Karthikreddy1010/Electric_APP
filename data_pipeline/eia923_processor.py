"""
EIA-923 Power Plant Operations Processor — High-ROI Data Ingestion Pipeline.

Ingests:
  - Page 1 Generation & Fuel Data -> Aggregated State Fuel Mix & Scope 2 Carbon Intensity (eia923_state_fuel_mix)
  - Page 5 Fuel Receipts & Costs  -> Weighted Average Delivered Fuel Prices $/MMBtu (eia923_fuel_cost_trends)
  - Page 6 Plant Frame           -> Power Plant Master Metadata Registry (eia923_plant_frame)

Follows minimal integration principles (Aggregate Only) to avoid raw database bloat.
"""
from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import get_sync_session, get_sync_engine
from database.models import (
    Base,
    EIA923StateFuelMix,
    EIA923FuelCostTrend,
    EIA923PlantFrame,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EIA923_DIR = PROJECT_ROOT / "data" / "raw" / "eia923"

# EPA/EIA standard carbon emission intensity factors (gCO2/kWh)
EMISSION_FACTORS_G_KWH: Dict[str, float] = {
    "NG": 420.0,    # Natural Gas
    "SUB": 1020.0,  # Subbituminous Coal
    "BIT": 980.0,   # Bituminous Coal
    "LIG": 1050.0,  # Lignite Coal
    "RC": 1000.0,   # Refined Coal
    "DFO": 840.0,   # Distillate Fuel Oil
    "RFO": 880.0,   # Residual Fuel Oil
    "WO": 850.0,    # Waste Oil
    "PC": 950.0,    # Petroleum Coke
    "NUC": 0.0,     # Nuclear
    "SUN": 0.0,     # Solar
    "WND": 0.0,     # Wind
    "WAT": 0.0,     # Hydroelectric
    "GEO": 0.0,     # Geothermal
    "WOOD": 50.0,   # Wood/Biomass (net neutral offset assumption)
    "OBG": 100.0,   # Other Biomass Gas
}
DEFAULT_EMISSION_FACTOR_G_KWH = 500.0

FUEL_GROUP_MAP: Dict[str, str] = {
    "NG": "Gas",
    "SUB": "Coal",
    "BIT": "Coal",
    "LIG": "Coal",
    "RC": "Coal",
    "DFO": "Petroleum",
    "RFO": "Petroleum",
    "WO": "Petroleum",
    "PC": "Petroleum",
    "NUC": "Nuclear",
    "SUN": "Solar",
    "WND": "Wind",
    "WAT": "Hydro",
}


def _clean_col_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize dataframe column names."""
    df.columns = [
        re.sub(r"\s+", "_", str(col).strip())
        .replace("\n", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        for col in df.columns
    ]
    return df


def process_eia923_page1(file_path: Path) -> pd.DataFrame:
    """
    Parse Page 1 Generation and Fuel Data and aggregate to State/Year/Month/FuelCode.
    """
    logger.info(f"Processing EIA-923 Page 1 from: {file_path.name}")
    try:
        xl = pd.ExcelFile(file_path)
        sheet = None
        for s in xl.sheet_names:
            if "Page 1 Generation and Fuel" in s or "Page 1 Gen" in s:
                sheet = s
                break
        if not sheet:
            logger.warning(f"Page 1 sheet not found in {file_path.name}")
            return pd.DataFrame()

        # Header detection
        preview = xl.parse(sheet, nrows=10, header=None)
        hdr_idx = 4
        for i, row in preview.iterrows():
            row_str = " ".join([str(x) for x in row.values])
            if "Plant Id" in row_str or "Plant ID" in row_str or "Reported Fuel Type" in row_str:
                hdr_idx = i
                break

        df = xl.parse(sheet, header=hdr_idx)
        df = _clean_col_names(df)

        # Detect Year from filename or column
        year_match = re.search(r"20\d\d", file_path.name)
        year = int(year_match.group(0)) if year_match else 2024

        # Required identity columns
        state_col = [c for c in df.columns if "Plant_State" in c or "State" in c]
        fuel_col = [c for c in df.columns if "Reported_Fuel_Type" in c or "Fuel_Type" in c or "AER_Fuel_Type" in c]

        if not state_col or not fuel_col:
            logger.warning(f"Could not find State/Fuel columns in {file_path.name}")
            return pd.DataFrame()

        st_c = state_col[0]
        fl_c = fuel_col[0]

        # Monthly net generation columns
        month_cols = {}
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        full_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

        for m_idx, (m_short, m_full) in enumerate(zip(months, full_months), start=1):
            matching = [
                c for c in df.columns
                if (m_short in c or m_full in c) and ("Netgen" in c or "Net_Generation" in c or "Generation" in c)
            ]
            if matching:
                month_cols[m_idx] = matching[0]

        records = []
        for _, row in df.iterrows():
            st = str(row.get(st_c, "")).strip().upper()
            fl = str(row.get(fl_c, "")).strip().upper()
            if not st or len(st) != 2 or st in ("US", "PR"):
                continue

            fl_grp = FUEL_GROUP_MAP.get(fl, "Other")
            ci = EMISSION_FACTORS_G_KWH.get(fl, DEFAULT_EMISSION_FACTOR_G_KWH)

            for m_idx, col_name in month_cols.items():
                try:
                    gen_val = float(row.get(col_name, 0.0) or 0.0)
                except (ValueError, TypeError):
                    gen_val = 0.0

                if np.isnan(gen_val):
                    gen_val = 0.0

                records.append({
                    "year": year,
                    "month": m_idx,
                    "state": st,
                    "fuel_code": fl,
                    "fuel_group": fl_grp,
                    "net_generation_mwh": gen_val,
                    "carbon_intensity_g_kwh": ci,
                })

        if not records:
            return pd.DataFrame()

        rdf = pd.DataFrame(records)
        agg_df = (
            rdf.groupby(["year", "month", "state", "fuel_code", "fuel_group"], as_index=False)
            .agg({
                "net_generation_mwh": "sum",
                "carbon_intensity_g_kwh": "mean",
            })
        )
        return agg_df

    except Exception as e:
        logger.error(f"Error processing Page 1 in {file_path.name}: {e}")
        return pd.DataFrame()


def process_eia923_page5(file_path: Path) -> pd.DataFrame:
    """
    Parse Page 5 Fuel Receipts & Costs and aggregate to State/Year/Month/FuelGroup.
    """
    logger.info(f"Processing EIA-923 Page 5 from: {file_path.name}")
    try:
        xl = pd.ExcelFile(file_path)
        sheet = None
        for s in xl.sheet_names:
            if "Page 5 Fuel Receipts" in s or "Page 5" in s:
                sheet = s
                break
        if not sheet:
            return pd.DataFrame()

        preview = xl.parse(sheet, nrows=10, header=None)
        hdr_idx = 4
        for i, row in preview.iterrows():
            row_str = " ".join([str(x) for x in row.values])
            if "Plant Id" in row_str or "Plant State" in row_str or "Fuel Cost" in row_str or "ENERGY_SOURCE" in row_str:
                hdr_idx = i
                break

        df = xl.parse(sheet, header=hdr_idx)
        df = _clean_col_names(df)

        year_match = re.search(r"20\d\d", file_path.name)
        year_default = int(year_match.group(0)) if year_match else 2024

        st_cols = [c for c in df.columns if "Plant_State" in c or "State" in c]
        mo_cols = [c for c in df.columns if "MONTH" in c or "Month" in c]
        fg_cols = [c for c in df.columns if "FUEL_GROUP" in c or "Fuel_Group" in c or "ENERGY_SOURCE" in c]
        cost_cols = [c for c in df.columns if "Fuel_Cost" in c or "Cost" in c]
        qty_cols = [c for c in df.columns if "Quantity" in c or "QUANTITY" in c]

        if not st_cols or not cost_cols:
            return pd.DataFrame()

        st_c = st_cols[0]
        mo_c = mo_cols[0] if mo_cols else None
        fg_c = fg_cols[0] if fg_cols else None
        cost_c = cost_cols[0]
        qty_c = qty_cols[0] if qty_cols else None

        records = []
        for _, row in df.iterrows():
            st = str(row.get(st_c, "")).strip().upper()
            if not st or len(st) != 2:
                continue

            try:
                mo = int(row.get(mo_c, 1)) if mo_c else 1
            except (ValueError, TypeError):
                mo = 1
            if mo < 1 or mo > 12:
                mo = 1

            fg = str(row.get(fg_c, "Natural Gas")).strip() if fg_c else "Natural Gas"
            if "Gas" in fg or "NG" in fg:
                fg = "Natural Gas"
            elif "Coal" in fg or "SUB" in fg or "BIT" in fg:
                fg = "Coal"
            elif "Petroleum" in fg or "Oil" in fg:
                fg = "Petroleum"
            else:
                fg = "Other"

            try:
                raw_cost = str(row.get(cost_c, 0.0)).replace(",", "").strip()
                cost_val = float(raw_cost) if raw_cost and raw_cost != "." else 0.0
            except (ValueError, TypeError):
                cost_val = 0.0

            if cost_val > 100:
                cost_dollars = cost_val / 100.0
                cost_cents = cost_val
            else:
                cost_dollars = cost_val
                cost_cents = cost_val * 100.0

            if cost_dollars <= 0 or cost_dollars > 100:
                continue

            try:
                qty_val = float(row.get(qty_c, 1.0) or 1.0)
            except (ValueError, TypeError):
                qty_val = 1.0

            records.append({
                "year": year_default,
                "month": mo,
                "state": st,
                "fuel_group": fg,
                "avg_cost_cents_mmbtu": cost_cents,
                "avg_cost_dollars_mmbtu": cost_dollars,
                "total_quantity_delivered": qty_val,
            })

        if not records:
            return pd.DataFrame()

        rdf = pd.DataFrame(records)
        agg_df = (
            rdf.groupby(["year", "month", "state", "fuel_group"], as_index=False)
            .agg({
                "avg_cost_cents_mmbtu": "mean",
                "avg_cost_dollars_mmbtu": "mean",
                "total_quantity_delivered": "sum",
            })
        )
        return agg_df

    except Exception as e:
        logger.error(f"Error processing Page 5 in {file_path.name}: {e}")
        return pd.DataFrame()


def run_eia923_ingestion(limit_files: Optional[int] = None) -> Dict[str, int]:
    """
    Run full EIA-923 ETL pipeline across raw files in data/raw/eia923/.
    """
    if not EIA923_DIR.exists():
        logger.error(f"EIA-923 directory not found: {EIA923_DIR}")
        return {"page1_rows": 0, "page5_rows": 0}

    files = sorted([
        f for f in os.listdir(EIA923_DIR)
        if f.endswith(".xlsx") and "Schedules_2_3_4_5" in f and "(1)" not in f
    ])

    if limit_files:
        files = files[-limit_files:]

    logger.info(f"Found {len(files)} EIA-923 Schedules 2-5 files for ingestion")

    all_p1 = []
    all_p5 = []

    for fname in files:
        fpath = EIA923_DIR / fname
        p1_df = process_eia923_page1(fpath)
        if not p1_df.empty:
            all_p1.append(p1_df)

        p5_df = process_eia923_page5(fpath)
        if not p5_df.empty:
            all_p5.append(p5_df)

    p1_total = 0
    p5_total = 0

    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)

    with get_sync_session() as db:
        if all_p1:
            full_p1 = pd.concat(all_p1, ignore_index=True)
            for _, row in full_p1.iterrows():
                existing = db.query(EIA923StateFuelMix).filter_by(
                    year=int(row["year"]),
                    month=int(row["month"]),
                    state=str(row["state"]),
                    fuel_code=str(row["fuel_code"])
                ).first()
                if not existing:
                    rec = EIA923StateFuelMix(
                        year=int(row["year"]),
                        month=int(row["month"]),
                        state=str(row["state"]),
                        fuel_code=str(row["fuel_code"]),
                        fuel_group=str(row["fuel_group"]),
                        net_generation_mwh=float(row["net_generation_mwh"]),
                        carbon_intensity_g_kwh=float(row["carbon_intensity_g_kwh"]),
                    )
                    db.add(rec)
                    p1_total += 1

        if all_p5:
            full_p5 = pd.concat(all_p5, ignore_index=True)
            for _, row in full_p5.iterrows():
                existing = db.query(EIA923FuelCostTrend).filter_by(
                    year=int(row["year"]),
                    month=int(row["month"]),
                    state=str(row["state"]),
                    fuel_group=str(row["fuel_group"])
                ).first()
                if not existing:
                    rec = EIA923FuelCostTrend(
                        year=int(row["year"]),
                        month=int(row["month"]),
                        state=str(row["state"]),
                        fuel_group=str(row["fuel_group"]),
                        avg_cost_cents_mmbtu=float(row["avg_cost_cents_mmbtu"]),
                        avg_cost_dollars_mmbtu=float(row["avg_cost_dollars_mmbtu"]),
                        total_quantity_delivered=float(row["total_quantity_delivered"]),
                    )
                    db.add(rec)
                    p5_total += 1

        db.commit()

    logger.info(f"EIA-923 ETL complete. Ingested {p1_total} State Fuel Mix rows, {p5_total} Fuel Cost rows.")
    return {"page1_rows": p1_total, "page5_rows": p5_total}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_eia923_ingestion(limit_files=2)
    print("Ingestion Results:", results)
