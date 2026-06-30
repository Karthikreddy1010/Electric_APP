import json
import sqlite3
from pathlib import Path
import pandas as pd
import geopandas as gpd

def get_boundaries(state="NJ"):
    # 1. Query ZIPs and utilities from database
    conn = sqlite3.connect('data/electricity.db')
    query = """
        SELECT 
            z.zip_code, 
            z.utility_name,
            z.eia_utility_id,
            r.residential_rate, 
            r.commercial_rate, 
            r.industrial_rate
        FROM utility_zip_lookup z
        LEFT JOIN utility_rates r ON z.eia_utility_id = r.eia_utility_id AND z.state = r.state
        WHERE z.state = ?
    """
    df_db = pd.read_sql(query, conn, params=[state])
    conn.close()
    
    if df_db.empty:
        print("No ZIP codes found in database for state:", state)
        return
    
    # Clean zip code: strip and zero-pad to 5 chars
    df_db['zip_code'] = df_db['zip_code'].str.strip().str.zfill(5)
    
    # Group by zip_code to aggregate properties
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
        
        zip_properties[zip_code] = {
            "zip_code": zip_code,
            "state": state,
            "utility_names": utility_list_str,
            "primary_utility": primary_utility,
            "residential_rate": avg_res_rate,
            "commercial_rate": avg_comm_rate,
            "industrial_rate": avg_ind_rate
        }
        
    print("Aggregate info for sample ZIP:", list(zip_properties.values())[0])

    # 2. Load and filter shapefile
    shp_path = Path('data/raw/tl_2024_us_zcta520/tl_2024_us_zcta520.shp')
    gdf = gpd.read_file(shp_path)
    
    # Filter geometries
    gdf_filtered = gdf[gdf['ZCTA5CE20'].isin(zip_properties.keys())].copy()
    print(f"Found {len(gdf_filtered)} geometries out of {len(zip_properties)} zip codes in database.")
    
    # Simplify geometry
    gdf_filtered['geometry'] = gdf_filtered['geometry'].simplify(tolerance=0.001, preserve_topology=True)
    
    # Merge properties
    # Let's map zip_properties onto the GeoDataFrame
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
    
    # Retain only necessary columns
    gdf_final = gdf_filtered[['zip_code', 'state', 'utility_names', 'primary_utility', 'residential_rate', 'commercial_rate', 'industrial_rate', 'geometry']]
    
    # Export to GeoJSON
    geojson_data = json.loads(gdf_final.to_json())
    print("Created GeoJSON structure with keys:", geojson_data.keys())
    print("Number of features:", len(geojson_data['features']))
    print("Feature properties sample:", geojson_data['features'][0]['properties'])

if __name__ == '__main__':
    get_boundaries()
