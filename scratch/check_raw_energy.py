from database.connection import get_sync_engine
import pandas as pd

engine = get_sync_engine()
with engine.connect() as conn:
    print("Unique sources in raw_energy_data:")
    df_src = pd.read_sql("SELECT DISTINCT source FROM raw_energy_data", con=conn)
    print(df_src)
    
    print("\nUnique region_ids in raw_energy_data:")
    df_reg = pd.read_sql("SELECT DISTINCT region_id FROM raw_energy_data", con=conn)
    print(df_reg)
    
    print("\nRow count:")
    df_cnt = pd.read_sql("SELECT COUNT(*) as count FROM raw_energy_data", con=conn)
    print(df_cnt)
