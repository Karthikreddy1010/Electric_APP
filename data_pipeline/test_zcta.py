import sqlite3
import time
import geopandas as gpd
from pathlib import Path

def test():
    conn = sqlite3.connect('data/electricity.db')
    cursor = conn.cursor()
    cursor.execute("select distinct zip_code from utility_zip_lookup where state='NJ'")
    zips = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    print('NJ ZIP codes count:', len(zips))
    print('Sample NJ zips:', zips[:10])
    
    # Let's load the shapefile and filter
    t0 = time.time()
    shp_path = Path('data/raw/tl_2024_us_zcta520/tl_2024_us_zcta520.shp')
    print('Reading shapefile...')
    gdf = gpd.read_file(shp_path)
    print('Loaded shapefile in', time.time() - t0, 's')
    
    # Filter
    t0 = time.time()
    # ZCTA5CE20 values might have leading zeros.
    gdf_filtered = gdf[gdf['ZCTA5CE20'].isin(zips)]
    print('Filtered to', len(gdf_filtered), 'ZCTAs in', time.time() - t0, 's')
    
    # Try simplifying
    t0 = time.time()
    # simplify coordinates to make geojson small
    gdf_filtered = gdf_filtered.copy()
    gdf_filtered['geometry'] = gdf_filtered['geometry'].simplify(tolerance=0.001, preserve_topology=True)
    print('Simplified geometry in', time.time() - t0, 's')
    
    # Check size of output JSON
    json_str = gdf_filtered.to_json()
    print('GeoJSON length:', len(json_str) / 1024 / 1024, 'MB')

if __name__ == '__main__':
    test()
