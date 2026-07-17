import pandas as pd
from pathlib import Path

csv_path = Path("data/raw/da_hrl_lmps(1).csv")
print(f"File exists: {csv_path.exists()}")
if csv_path.exists():
    print(f"File size: {csv_path.stat().st_size / 1024 / 1024:.2f} MB")
    df = pd.read_csv(csv_path, nrows=5)
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df)
