"""
EIA-923 Lightweight Aggregation & Ingestion ETL Pipeline

Automated ingestion for approved EIA-923 datasets in data/raw/eia923/:
- Phase 1: Page 5 Fuel Receipts & Costs (Aggregated by Year, Month, State, Utility ID, Fuel Group)
- Phase 1: Page 1 Generation & Fuel Data (Aggregated by Year, Month, State, Utility ID, Fuel Code)
- Phase 2: Page 1 Energy Storage (Aggregated by Year, State, Technology)

ARCHITECTURAL PRINCIPLE:
NEVER store raw plant-level EIA-923 records. Expose aggregated metrics only.
"""
import os
import glob
import re
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from database.connection import get_sync_session, get_sync_engine
from database.models import Base, EIA923FuelCostTrend, EIA923StateFuelMix, EIA923StorageSummary

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("etl_eia923")

# Fuel Code Category Mappings & Emission Factors (g CO2 / kWh equivalent)
FUEL_EMISSION_FACTORS = {
    'NG': 415.0,    # Natural Gas
    'BIT': 900.0,   # Bituminous Coal
    'SUB': 980.0,   # Sub-bituminous Coal
    'LIG': 1050.0,  # Lignite Coal
    'DFO': 750.0,   # Distillate Fuel Oil
    'RFO': 800.0,   # Residual Fuel Oil
    'NUC': 0.0,     # Nuclear
    'SUN': 0.0,     # Solar
    'WND': 0.0,     # Wind
    'WAT': 0.0,     # Hydro
    'BAT': 0.0,     # Battery Storage
}

CLEAN_FUELS = {'NUC', 'SUN', 'WND', 'WAT', 'BAT', 'GEO'}


def extract_year_from_filename(filepath: str) -> Optional[int]:
    """Extract 4-digit year from filename (e.g. 2024)."""
    match = re.search(r'(20\d{2})', os.path.basename(filepath))
    return int(match.group(1)) if match else None


def find_header_row(df_raw: pd.DataFrame, key_terms: List[str]) -> int:
    """Dynamically scan top 12 rows to locate table header row."""
    for r in range(min(12, len(df_raw))):
        row_vals = [str(x).strip() for x in df_raw.iloc[r].values]
        if any(term in str(x) for term in key_terms for x in row_vals):
            return r
    return 4  # Default fallback header row


def process_page_5_receipts(filepath: str, file_year: int) -> List[Dict]:
    """Process Page 5 Fuel Receipts & Costs sheet and return aggregated summary records."""
    try:
        xl = pd.ExcelFile(filepath)
        if 'Page 5 Fuel Receipts and Costs' not in xl.sheet_names:
            return []

        df_raw = xl.parse('Page 5 Fuel Receipts and Costs', header=None, nrows=12)
        hdr_idx = find_header_row(df_raw, ['YEAR', 'Plant Id', 'Plant State', 'Purchase Type', 'FUEL_COST'])
        
        df = xl.parse('Page 5 Fuel Receipts and Costs', header=hdr_idx)
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]

        # Column Mapping Resilience
        col_map = {}
        for c in df.columns:
            c_upper = c.upper()
            if 'YEAR' in c_upper and 'year' not in col_map: col_map['year'] = c
            elif 'MONTH' in c_upper and 'month' not in col_map: col_map['month'] = c
            elif ('PLANT STATE' in c_upper or 'STATE' in c_upper) and 'state' not in col_map: col_map['state'] = c
            elif 'OPERATOR ID' in c_upper and 'utility_id' not in col_map: col_map['utility_id'] = c
            elif ('ENERGY_SOURCE' in c_upper or 'ENERGY SOURCE' in c_upper) and 'fuel_code' not in col_map: col_map['fuel_code'] = c
            elif ('FUEL_GROUP' in c_upper or 'FUEL GROUP' in c_upper) and 'fuel_group' not in col_map: col_map['fuel_group'] = c
            elif 'QUANTITY' in c_upper and 'quantity' not in col_map: col_map['quantity'] = c
            elif ('AVERAGE HEAT CONTENT' in c_upper or 'HEAT CONTENT' in c_upper) and 'heat_content' not in col_map: col_map['heat_content'] = c
            elif ('FUEL_COST' in c_upper or 'FUEL COST' in c_upper) and 'fuel_cost' not in col_map: col_map['fuel_cost'] = c

        if 'state' not in col_map or 'fuel_cost' not in col_map:
            return []

        # Filter & Clean
        df = df.dropna(subset=[col_map['state'], col_map['fuel_cost']]).copy()
        
        df['year'] = pd.to_numeric(df[col_map['year']], errors='coerce').fillna(file_year).astype(int) if 'year' in col_map else file_year
        df['month'] = pd.to_numeric(df[col_map['month']], errors='coerce').fillna(1).astype(int) if 'month' in col_map else 1
        df['state'] = df[col_map['state']].astype(str).str.strip().str.upper()
        df['utility_id'] = pd.to_numeric(df[col_map['utility_id']], errors='coerce').fillna(0).astype(int) if 'utility_id' in col_map else 0
        df['fuel_group'] = df[col_map['fuel_group']].astype(str).str.strip() if 'fuel_group' in col_map else 'Natural Gas'
        
        df['quantity'] = pd.to_numeric(df[col_map['quantity']], errors='coerce').fillna(1.0) if 'quantity' in col_map else 1.0
        df['heat_content'] = pd.to_numeric(df[col_map['heat_content']], errors='coerce').fillna(1.0) if 'heat_content' in col_map else 1.0
        df['raw_cost'] = pd.to_numeric(df[col_map['fuel_cost']], errors='coerce').fillna(0.0)

        # Filter valid states and positive costs
        df = df[(df['state'].str.len() == 2) & (df['raw_cost'] > 0)].copy()
        if df.empty:
            return []

        # Determine cents vs dollars $/MMBtu
        df['cost_dollars_mmbtu'] = np.where(df['raw_cost'] > 50.0, df['raw_cost'] / 100.0, df['raw_cost'])
        df['cost_cents_mmbtu'] = df['cost_dollars_mmbtu'] * 100.0
        df['mmbtu_delivered'] = df['quantity'] * df['heat_content']

        # MANDATORY AGGREGATION: Group by (year, month, state, utility_id, fuel_group)
        grouped = df.groupby(['year', 'month', 'state', 'utility_id', 'fuel_group']).agg(
            total_mmbtu=('mmbtu_delivered', 'sum'),
            total_qty=('quantity', 'sum'),
            weighted_cost_dollars=('cost_dollars_mmbtu', lambda x: np.average(x, weights=df.loc[x.index, 'mmbtu_delivered']) if df.loc[x.index, 'mmbtu_delivered'].sum() > 0 else x.mean()),
            weighted_heat=('heat_content', 'mean')
        ).reset_index()

        records = []
        for _, row in grouped.iterrows():
            records.append({
                'year': int(row['year']),
                'month': int(row['month']),
                'state': str(row['state']),
                'utility_id': int(row['utility_id']),
                'fuel_group': str(row['fuel_group']),
                'avg_cost_dollars_mmbtu': round(float(row['weighted_cost_dollars']), 4),
                'avg_cost_cents_mmbtu': round(float(row['weighted_cost_dollars'] * 100.0), 2),
                'total_quantity_delivered': round(float(row['total_qty']), 2),
                'avg_heat_content': round(float(row['weighted_heat']), 4),
                'mom_change_pct': 0.0
            })
        return records
    except Exception as e:
        logger.warning(f"Error parsing Page 5 in {filepath}: {e}")
        return []


def process_page_1_generation(filepath: str, file_year: int) -> List[Dict]:
    """Process Page 1 Generation & Fuel Data sheet and return aggregated state/utility summaries."""
    try:
        xl = pd.ExcelFile(filepath)
        if 'Page 1 Generation and Fuel Data' not in xl.sheet_names:
            return []

        df_raw = xl.parse('Page 1 Generation and Fuel Data', header=None, nrows=12)
        hdr_idx = find_header_row(df_raw, ['Plant Id', 'Operator Id', 'Plant State', 'Netgen January'])
        
        df = xl.parse('Page 1 Generation and Fuel Data', header=hdr_idx)
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]

        state_col = next((c for c in df.columns if 'STATE' in c.upper()), None)
        util_col = next((c for c in df.columns if 'OPERATOR ID' in c.upper()), None)
        fuel_col = next((c for c in df.columns if 'REPORTED FUEL TYPE CODE' in c.upper() or 'MER FUEL TYPE CODE' in c.upper() or 'AER FUEL TYPE CODE' in c.upper()), None)

        if not state_col or not fuel_col:
            return []

        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        
        df['state'] = df[state_col].astype(str).str.strip().str.upper()
        df['utility_id'] = pd.to_numeric(df[util_col], errors='coerce').fillna(0).astype(int) if util_col else 0
        df['fuel_code'] = df[fuel_col].astype(str).str.strip().str.upper()
        df = df[df['state'].str.len() == 2].copy()

        records = []
        for m_idx, m_name in enumerate(month_names, 1):
            netgen_col = next((c for c in df.columns if f'NETGEN {m_name.upper()}' in c.upper() or f'NETGEN {m_name.capitalize()}' in c), None)
            mmbtu_col = next((c for c in df.columns if f'ELEC_MMBTU {m_name.upper()}' in c.upper() or f'ELEC_MMBTU {m_name.capitalize()}' in c or f'TOT_MMBTU {m_name.upper()}' in c.upper()), None)
            
            if netgen_col:
                df_m = df[['state', 'utility_id', 'fuel_code']].copy()
                df_m['netgen'] = pd.to_numeric(df[netgen_col], errors='coerce').fillna(0.0)
                df_m['mmbtu'] = pd.to_numeric(df[mmbtu_col], errors='coerce').fillna(0.0) if mmbtu_col else 0.0

                grouped = df_m.groupby(['state', 'utility_id', 'fuel_code']).agg(
                    total_netgen=('netgen', 'sum'),
                    total_mmbtu=('mmbtu', 'sum')
                ).reset_index()

                for _, row in grouped.iterrows():
                    netgen_val = max(0.0, float(row['total_netgen']))
                    fuel_code = str(row['fuel_code'])
                    is_clean = fuel_code in CLEAN_FUELS
                    
                    records.append({
                        'year': file_year,
                        'month': m_idx,
                        'state': str(row['state']),
                        'utility_id': int(row['utility_id']),
                        'fuel_code': fuel_code,
                        'fuel_group': 'Renewable' if is_clean else 'Fossil',
                        'net_generation_mwh': round(netgen_val, 2),
                        'total_mmbtu': round(float(row['total_mmbtu']), 2),
                        'clean_share_pct': 100.0 if is_clean else 0.0,
                        'fossil_share_pct': 0.0 if is_clean else 100.0,
                        'carbon_intensity_g_kwh': FUEL_EMISSION_FACTORS.get(fuel_code, 450.0)
                    })

        return records
    except Exception as e:
        logger.warning(f"Error parsing Page 1 Generation in {filepath}: {e}")
        return []


def process_page_1_storage(filepath: str, file_year: int) -> List[Dict]:
    """Process Page 1 Energy Storage sheet and return aggregated annual state storage summaries."""
    try:
        xl = pd.ExcelFile(filepath)
        if 'Page 1 Energy Storage' not in xl.sheet_names:
            return []

        df_raw = xl.parse('Page 1 Energy Storage', header=None, nrows=12)
        hdr_idx = find_header_row(df_raw, ['Plant Id', 'Operator Id', 'Plant State', 'Grossgen January'])

        df = xl.parse('Page 1 Energy Storage', header=hdr_idx)
        df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]

        state_col = next((c for c in df.columns if 'STATE' in c.upper()), None)
        gross_col = next((c for c in df.columns if 'GROSS GENERATION' in c.upper() or 'GROSSGEN ANNUAL' in c.upper()), None)
        charge_col = next((c for c in df.columns if 'TOTAL FUEL CONSUMPTION' in c.upper() or 'ELECTRIC FUEL CONSUMPTION' in c.upper()), None)

        if not state_col:
            return []

        df['state'] = df[state_col].astype(str).str.strip().str.upper()
        df['discharge_mwh'] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0.0) if gross_col else 0.0
        df['charge_mwh'] = pd.to_numeric(df[charge_col], errors='coerce').fillna(0.0) if charge_col else 0.0
        df = df[df['state'].str.len() == 2].copy()

        grouped = df.groupby('state').agg(
            total_discharge=('discharge_mwh', 'sum'),
            total_charge=('charge_mwh', 'sum')
        ).reset_index()

        records = []
        for _, row in grouped.iterrows():
            discharge = float(row['total_discharge'])
            charge = float(row['total_charge'])
            efficiency = round((discharge / charge * 100.0), 2) if charge > 0 else 81.4
            
            records.append({
                'year': file_year,
                'state': str(row['state']),
                'technology': 'Batteries',
                'total_discharge_mwh': round(discharge, 2),
                'total_charge_mwh': round(charge, 2),
                'roundtrip_efficiency_pct': efficiency
            })

        return records
    except Exception as e:
        logger.warning(f"Error parsing Page 1 Storage in {filepath}: {e}")
        return []


def run_eia923_etl():
    """Main ETL Execution Loop."""
    logger.info("Starting EIA-923 Lightweight Aggregation ETL Pipeline...")
    
    data_dir = os.path.join(os.getcwd(), 'data', 'raw', 'eia923')
    if not os.path.exists(data_dir):
        logger.error(f"EIA-923 raw data directory not found: {data_dir}")
        return

    files = sorted(glob.glob(os.path.join(data_dir, '*.xlsx')) + glob.glob(os.path.join(data_dir, '*.xls')))
    logger.info(f"Discovered {len(files)} total Excel files in data/raw/eia923/")

    all_fuel_cost_records = []
    all_gen_records = []
    all_storage_records = []

    processed_files = 0
    skipped_files = 0

    for f in files:
        file_year = extract_year_from_filename(f)
        if not file_year:
            logger.info(f"Skipping file without 4-digit year: {os.path.basename(f)}")
            skipped_files += 1
            continue

        # Only process Schedules 2_3_4_5 workbooks
        if 'Schedules_2_3_4_5' not in f and 'SCHEDULES 2_3_4_5' not in f:
            continue

        try:
            logger.info(f"Processing file ({file_year}): {os.path.basename(f)}")
            
            # Page 5 Receipts & Costs
            p5_recs = process_page_5_receipts(f, file_year)
            all_fuel_cost_records.extend(p5_recs)

            # Page 1 Generation
            p1_recs = process_page_1_generation(f, file_year)
            all_gen_records.extend(p1_recs)

            # Page 1 Energy Storage
            storage_recs = process_page_1_storage(f, file_year)
            all_storage_records.extend(storage_recs)

            processed_files += 1

        except Exception as e:
            logger.error(f"Error processing {os.path.basename(f)}: {e}")
            skipped_files += 1

    logger.info(f"ETL Extraction complete. Processed {processed_files} files, skipped {skipped_files} files.")
    logger.info(f"Aggregated Records Generated: Fuel Cost={len(all_fuel_cost_records)}, Generation={len(all_gen_records)}, Storage={len(all_storage_records)}")

    # Database Persistence
    engine = get_sync_engine()
    
    # Drop tables to ensure updated schema with utility_id columns
    try:
        EIA923FuelCostTrend.__table__.drop(engine, checkfirst=True)
        EIA923StateFuelMix.__table__.drop(engine, checkfirst=True)
        EIA923StorageSummary.__table__.drop(engine, checkfirst=True)
    except Exception as e_drop:
        logger.warning(f"Note during table drop: {e_drop}")

    Base.metadata.create_all(engine)

    with get_sync_session() as session:
        # Clear existing tables for clean upsert
        session.query(EIA923FuelCostTrend).delete()
        session.query(EIA923StateFuelMix).delete()
        session.query(EIA923StorageSummary).delete()
        session.commit()

        # Batch insert Fuel Costs
        if all_fuel_cost_records:
            logger.info(f"Bulk inserting {len(all_fuel_cost_records)} aggregated Fuel Cost records...")
            session.bulk_insert_mappings(EIA923FuelCostTrend, all_fuel_cost_records)

        # Batch insert Generation
        if all_gen_records:
            logger.info(f"Bulk inserting {len(all_gen_records)} aggregated Generation records...")
            session.bulk_insert_mappings(EIA923StateFuelMix, all_gen_records)

        # Batch insert Storage
        if all_storage_records:
            logger.info(f"Bulk inserting {len(all_storage_records)} aggregated Storage records...")
            session.bulk_insert_mappings(EIA923StorageSummary, all_storage_records)

        session.commit()

    logger.info("EIA-923 ETL Aggregation & Database Persistence Completed Successfully!")


if __name__ == '__main__':
    run_eia923_etl()
