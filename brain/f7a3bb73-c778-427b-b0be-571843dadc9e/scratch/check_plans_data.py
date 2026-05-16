import pandas as pd
from pathlib import Path

data_dir = Path(r"c:\Users\dukar\OneDrive\Desktop\Electric\data\raw")
file_path = data_dir / "retail_plans.parquet"

if file_path.exists():
    df = pd.read_parquet(file_path)
    print(f"File exists. Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print("First 5 rows:")
    print(df.head())
else:
    print(f"File {file_path} does not exist.")
