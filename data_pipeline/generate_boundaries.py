"""
Pre-generate ZCTA GeoJSON boundaries by state.
Loads the 820MB US shapefile exactly once, filters geometries per state,
simplifies the boundaries to preserve performance, maps database properties,
and caches the outputs to data/geojson_cache/zctas_{STATE}.json.
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
import pandas as pd
import geopandas as gpd
from sqlalchemy import text

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_sync_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

def generate_all_state_boundaries(force: bool = False):
    logger.info("Starting boundary pre-generation pipeline...")
    
    # 1. Output Cache Directory
    cache_dir = PROJECT_ROOT / "data" / "geojson_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Check Shapefile existence
    shp_path = PROJECT_ROOT / "data" / "raw" / "tl_2024_us_zcta520" / "tl_2024_us_zcta520.shp"
    if not shp_path.exists():
        logger.error(f"US ZCTA shapefile not found at: {shp_path}")
        logger.error("Please ensure you have downloaded and placed the ZCTA shapefiles there.")
        return
        
    # 3. Load database ZIP code lookup mapping
    engine = get_sync_engine()
    query = text("""
        SELECT 
            z.zip_code, 
            z.state,
            z.utility_name,
            z.eia_utility_id,
            r.residential_rate, 
            r.commercial_rate, 
            r.industrial_rate
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
    """)
    
    try:
        logger.info("Querying utility zip mappings and rates from database...")
        df_db = pd.read_sql(query, con=engine)
    except Exception as e:
        logger.error(f"Failed to query database mappings: {e}")
        return
        
    if df_db.empty:
        logger.warning("No ZIP codes found in utility_zip_lookup table. Seeding may be required.")
        return
        
    # Normalize zip codes to 5-digit strings
    df_db['zip_code'] = df_db['zip_code'].astype(str).str.strip().str.zfill(5)
    df_db['state'] = df_db['state'].str.strip().str.upper()
    
    # Group by state and zip_code to prepare properties mapping
    logger.info("Grouping and aggregating properties by state and zip...")
    state_zip_properties = {}
    
    for (state, zip_code), group in df_db.groupby(['state', 'zip_code']):
        if state not in state_zip_properties:
            state_zip_properties[state] = {}
            
        utilities = group['utility_name'].dropna().tolist()
        rates = group['residential_rate'].dropna().tolist()
        comm_rates = group['commercial_rate'].dropna().tolist()
        ind_rates = group['industrial_rate'].dropna().tolist()
        
        avg_res_rate = sum(rates) / len(rates) if rates else None
        avg_comm_rate = sum(comm_rates) / len(comm_rates) if comm_rates else None
        avg_ind_rate = sum(ind_rates) / len(ind_rates) if ind_rates else None
        
        primary_utility = utilities[0] if utilities else "Unknown"
        utility_list_str = ", ".join(utilities)
        
        state_zip_properties[state][zip_code] = {
            "zip_code": zip_code,
            "state": state,
            "utility_names": utility_list_str,
            "primary_utility": primary_utility,
            "residential_rate": avg_res_rate,
            "commercial_rate": avg_comm_rate,
            "industrial_rate": avg_ind_rate
        }
        
    states_to_process = sorted(list(state_zip_properties.keys()))
    logger.info(f"Identified {len(states_to_process)} states in database: {states_to_process}")
    
    # 4. Load national shapefile into memory ONCE
    t0 = time.time()
    logger.info(f"Loading national ZCTA shapefile (820MB) into memory... this will take ~2-3 seconds.")
    try:
        gdf = gpd.read_file(shp_path)
        logger.info(f"Loaded national shapefile with {len(gdf)} features in {time.time() - t0:.2f} seconds.")
    except Exception as e:
        logger.error(f"Failed to read shapefile: {e}")
        return

    # Ensure the ZCTA geometry column exists
    if 'ZCTA5CE20' not in gdf.columns:
        logger.error("Expected column ZCTA5CE20 not found in shapefile columns.")
        return
        
    gdf['ZCTA5CE20'] = gdf['ZCTA5CE20'].astype(str).str.strip().str.zfill(5)

    # 5. Process state-by-state
    for state in states_to_process:
        cache_file = cache_dir / f"zctas_{state}.json"
        
        if cache_file.exists() and not force:
            logger.info(f"[{state}] Cache file already exists at {cache_file.name} — skipping (use force=True to override)")
            continue
            
        t_state = time.time()
        zip_map = state_zip_properties[state]
        zip_list = list(zip_map.keys())
        
        # Filter geometries
        gdf_filtered = gdf[gdf['ZCTA5CE20'].isin(zip_list)].copy()
        
        if gdf_filtered.empty:
            logger.warning(f"[{state}] No matching geometries found in shapefile for the {len(zip_list)} zip codes.")
            continue
            
        logger.info(f"[{state}] Filtering matched {len(gdf_filtered)} ZCTAs out of {len(zip_list)} zip codes.")
        
        # Simplify geometry to keep geojson files tiny (approx 1MB instead of 15MB+)
        gdf_filtered['geometry'] = gdf_filtered['geometry'].simplify(tolerance=0.001, preserve_topology=True)
        
        # Helper to retrieve properties
        def get_prop(zip_code, prop_name):
            props = zip_map.get(zip_code)
            if props:
                return props.get(prop_name)
            return None
            
        # Merge properties into shapefile geodataframe
        gdf_filtered['zip_code'] = gdf_filtered['ZCTA5CE20']
        gdf_filtered['state'] = state
        gdf_filtered['utility_names'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'utility_names'))
        gdf_filtered['primary_utility'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'primary_utility'))
        gdf_filtered['residential_rate'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'residential_rate'))
        gdf_filtered['commercial_rate'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'commercial_rate'))
        gdf_filtered['industrial_rate'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'industrial_rate'))
        
        # Select target columns
        gdf_final = gdf_filtered[[
            'zip_code', 'state', 'utility_names', 'primary_utility', 
            'residential_rate', 'commercial_rate', 'industrial_rate', 'geometry'
        ]]
        
        # Export to GeoJSON
        try:
            geojson_data = json.loads(gdf_final.to_json())
            
            with open(cache_file, "w") as f:
                json.dump(geojson_data, f)
                
            file_size_mb = cache_file.stat().st_size / 1024 / 1024
            logger.info(f"[{state}] Generated {cache_file.name} ({file_size_mb:.2f} MB, {len(gdf_final)} features) in {time.time() - t_state:.2f} seconds.")
        except Exception as e:
            logger.error(f"[{state}] Failed to save cached GeoJSON: {e}")
            
    logger.info("Boundary pre-generation pipeline complete.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Pre-generate simplified GeoJSON boundaries by state")
    parser.add_argument("--force", action="store_true", help="Overwrite existing cache files")
    args = parser.parse_args()
    
    generate_all_state_boundaries(force=args.force)
