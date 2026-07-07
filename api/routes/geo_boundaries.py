import logging
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from database.connection import get_sync_engine
from sqlalchemy import text
import pandas as pd
import numpy as np
import geopandas as gpd

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geo", tags=["geo-insights"])


@router.get("/boundaries")
async def get_geo_boundaries(
    state: str = Query("NJ", description="State code, e.g. NJ"),
):
    """
    Get ZCTA boundaries with utility mapping and electricity prices for a state.
    Uses cached GeoJSON if available, otherwise generates it from raw shapefiles.
    """
    state = state.strip().upper()
    cache_dir = Path("data/geojson_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"zctas_{state}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cached boundaries for {state}: {e}")
            
    engine = get_sync_engine()
    
    query = text("""
        SELECT 
            z.zip_code, 
            z.utility_name,
            z.eia_utility_id,
            r.residential_rate, 
            r.commercial_rate, 
            r.industrial_rate,
            em.total_customers,
            em.peak_demand,
            em.nm_customers,
            em.dynamic_pricing_flag,
            em.demand_response_flag
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
        LEFT JOIN eia861_master em ON z.eia_utility_id = em.utility_id AND z.state = em.state AND em.year = (SELECT MAX(year) FROM eia861_master)
        WHERE z.state = :state
    """)
    
    try:
        df_db = pd.read_sql(query, con=engine, params={"state": state})
    except Exception as e:
        logger.error(f"Database query error in get_geo_boundaries: {e}")
        raise HTTPException(500, "Database query error")
        
    if df_db.empty:
        return {"type": "FeatureCollection", "features": []}
        
    df_db['zip_code'] = df_db['zip_code'].astype(str).str.strip().str.zfill(5)
    
    zip_properties = {}
    for zip_code, group in df_db.groupby('zip_code'):
        utilities = group['utility_name'].dropna().tolist()
        rates = group['residential_rate'].dropna().tolist()
        comm_rates = group['commercial_rate'].dropna().tolist()
        ind_rates = group['industrial_rate'].dropna().tolist()
        
        avg_res_rate = sum(rates) / len(rates) if rates else None
        avg_comm_rate = sum(comm_rates) / len(comm_rates) if comm_rates else None
        avg_ind_rate = sum(ind_rates) / len(ind_rates) if ind_rates else None
        
        primary_utility = utilities[0] if utilities else "Unknown"
        utility_list_str = ", ".join(utilities)

        total_cust = float(group['total_customers'].sum()) if group['total_customers'].notna().any() else 0.0
        peak_dem = float(group['peak_demand'].sum()) if group['peak_demand'].notna().any() else 0.0
        nm_cust = float(group['nm_customers'].sum()) if group['nm_customers'].notna().any() else 0.0
        dyn_pricing = int(group['dynamic_pricing_flag'].max()) if group['dynamic_pricing_flag'].notna().any() else 0
        dem_resp = int(group['demand_response_flag'].max()) if group['demand_response_flag'].notna().any() else 0
        
        zip_properties[zip_code] = {
            "zip_code": zip_code,
            "state": state,
            "utility_names": utility_list_str,
            "primary_utility": primary_utility,
            "residential_rate": avg_res_rate,
            "commercial_rate": avg_comm_rate,
            "industrial_rate": avg_ind_rate,
            "total_customers": total_cust,
            "peak_demand": peak_dem,
            "net_metering_customers": nm_cust,
            "dynamic_pricing": dyn_pricing,
            "demand_response": dem_resp
        }
        
    shp_path = Path("data/raw/tl_2024_us_zcta520/tl_2024_us_zcta520.shp")
    if not shp_path.exists():
        logger.error(f"Shapefile not found: {shp_path}")
        raise HTTPException(404, "ZCTA shapefile not found on server")
        
    try:
        gdf = gpd.read_file(shp_path)
        gdf_filtered = gdf[gdf['ZCTA5CE20'].isin(zip_properties.keys())].copy()
        
        if gdf_filtered.empty:
            return {"type": "FeatureCollection", "features": []}
            
        gdf_filtered['geometry'] = gdf_filtered['geometry'].simplify(tolerance=0.001, preserve_topology=True)
        
        def get_prop(zip_code, prop_name):
            props = zip_properties.get(zip_code)
            if props:
                return props.get(prop_name)
            return None
            
        gdf_filtered['zip_code'] = gdf_filtered['ZCTA5CE20']
        gdf_filtered['state'] = state
        gdf_filtered['utility_names'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'utility_names'))
        gdf_filtered['primary_utility'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'primary_utility'))
        gdf_filtered['residential_rate'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'residential_rate'))
        gdf_filtered['commercial_rate'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'commercial_rate'))
        gdf_filtered['industrial_rate'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'industrial_rate'))
        gdf_filtered['total_customers'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'total_customers'))
        gdf_filtered['peak_demand'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'peak_demand'))
        gdf_filtered['net_metering_customers'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'net_metering_customers'))
        gdf_filtered['dynamic_pricing'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'dynamic_pricing'))
        gdf_filtered['demand_response'] = gdf_filtered['zip_code'].apply(lambda z: get_prop(z, 'demand_response'))
        
        gdf_final = gdf_filtered[[
            'zip_code', 'state', 'utility_names', 'primary_utility',
            'residential_rate', 'commercial_rate', 'industrial_rate',
            'total_customers', 'peak_demand', 'net_metering_customers',
            'dynamic_pricing', 'demand_response', 'geometry'
        ]]
        
        geojson_str = gdf_final.to_json()
        geojson_data = json.loads(geojson_str)
        
        with open(cache_file, "w") as f:
            json.dump(geojson_data, f)
            
        return geojson_data
    except Exception as e:
        logger.error(f"Error generating boundaries for {state}: {e}")
        raise HTTPException(500, f"Error processing shapefiles: {str(e)}")


@router.get("/zip-stats")
async def get_zip_stats(state: str = Query("NJ")):
    state = state.strip().upper()
    engine = get_sync_engine()
    query = text("""
        SELECT 
            z.zip_code, 
            r.residential_rate, 
            r.commercial_rate, 
            r.industrial_rate
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
        WHERE z.state = :state
    """)
    
    try:
        df = pd.read_sql(query, con=engine, params={"state": state})
    except Exception as e:
        logger.error(f"Database query error in get_zip_stats: {e}")
        raise HTTPException(500, "Database query error")
        
    if df.empty:
        return {
            "state": state,
            "total_zips": 0,
            "avg_rate": 0.0,
            "min_rate": None,
            "max_rate": None,
            "std_dev": 0.0,
            "zips": []
        }
        
    df['zip_code'] = df['zip_code'].astype(str).str.strip().str.zfill(5)
    grouped = df.groupby('zip_code').agg({
        'residential_rate': 'mean',
        'commercial_rate': 'mean',
        'industrial_rate': 'mean'
    }).dropna(subset=['residential_rate']).reset_index()
    
    if grouped.empty:
        return {
            "state": state,
            "total_zips": 0,
            "avg_rate": 0.0,
            "min_rate": None,
            "max_rate": None,
            "std_dev": 0.0,
            "zips": []
        }
        
    rates = grouped['residential_rate'].values
    avg_rate = float(np.mean(rates))
    min_idx = np.argmin(rates)
    max_idx = np.argmax(rates)
    std_dev = float(np.std(rates)) if len(rates) > 1 else 0.0
    
    zips_list = []
    for _, row in grouped.sort_values('residential_rate', ascending=False).iterrows():
        zips_list.append({
            "zip_code": row['zip_code'],
            "residential_rate": round(float(row['residential_rate']), 4),
            "commercial_rate": round(float(row['commercial_rate']), 4) if pd.notna(row['commercial_rate']) else None,
            "industrial_rate": round(float(row['industrial_rate']), 4) if pd.notna(row['industrial_rate']) else None,
        })
        
    return {
        "state": state,
        "total_zips": len(grouped),
        "avg_rate": round(avg_rate, 4),
        "min_rate": {
            "zip_code": grouped.iloc[min_idx]['zip_code'],
            "rate": round(float(rates[min_idx]), 4)
        },
        "max_rate": {
            "zip_code": grouped.iloc[max_idx]['zip_code'],
            "rate": round(float(rates[max_idx]), 4)
        },
        "std_dev": round(std_dev, 4),
        "zips": zips_list
    }


@router.get("/utility-territories")
async def get_utility_territories(state: str = Query("NJ")):
    state = state.strip().upper()
    engine = get_sync_engine()
    query = text("""
        SELECT 
            z.zip_code, 
            z.utility_name,
            z.eia_utility_id,
            r.residential_rate
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
        WHERE z.state = :state
    """)
    
    try:
        df = pd.read_sql(query, con=engine, params={"state": state})
    except Exception as e:
        logger.error(f"Database query error in get_utility_territories: {e}")
        raise HTTPException(500, "Database query error")
        
    if df.empty:
        return []
        
    df['zip_code'] = df['zip_code'].astype(str).str.strip().str.zfill(5)
    
    utils = []
    for (name, eia_id), group in df.groupby(['utility_name', 'eia_utility_id']):
        unique_zips = group['zip_code'].nunique()
        avg_rate = group['residential_rate'].mean()
        
        utils.append({
            "utility_name": name,
            "eia_utility_id": int(eia_id),
            "zip_count": unique_zips,
            "avg_residential_rate": round(float(avg_rate), 4) if pd.notna(avg_rate) else None
        })
        
    utils.sort(key=lambda x: x['zip_count'], reverse=True)
    return utils
