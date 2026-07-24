import os
import json
from pathlib import Path
import pandas as pd

raw_dir = Path("data/raw")

raw_files_info = []

for root, dirs, files in os.walk(raw_dir):
    for f in sorted(files):
        fp = Path(root) / f
        rel_path = str(fp.relative_to(raw_dir)).replace("\\", "/")
        size_bytes = fp.stat().st_size
        if size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        ext = fp.suffix.lower()

        info = {
            "rel_path": rel_path,
            "full_path": str(fp).replace("\\", "/"),
            "ext": ext,
            "size": size_str,
            "size_bytes": size_bytes
        }

        if ext in [".csv", ".parquet"]:
            try:
                if ext == ".csv":
                    df = pd.read_csv(fp, low_memory=False)
                else:
                    df = pd.read_parquet(fp)
                
                info["rows"] = len(df)
                info["cols"] = len(df.columns)
                info["column_list"] = list(df.columns)
                info["dtypes"] = {c: str(df[c].dtype) for c in df.columns}
                info["null_pct"] = round(float(df.isnull().mean().mean() * 100), 2) if len(df) > 0 else 0.0
                info["duplicate_rows"] = int(df.duplicated().sum()) if len(df) > 0 else 0
                
                # Sample 3 rows (values serialized as strings)
                sample = df.head(3).to_dict(orient="records")
                info["sample_records"] = sample

                # Date range check
                date_cols = [c for c in df.columns if any(k in c.lower() for k in ['date', 'period', 'year', 'time', 'month'])]
                if date_cols and len(df) > 0:
                    try:
                        c = date_cols[0]
                        info["date_range"] = f"{df[c].min()} to {df[c].max()}"
                    except Exception:
                        info["date_range"] = "N/A"
                else:
                    info["date_range"] = "N/A"
            except Exception as e:
                info["error"] = str(e)
        else:
            info["type"] = "Media / Document / Geo Asset"

        raw_files_info.append(info)

print(f"Total raw files analyzed: {len(raw_files_info)}")

def json_default(obj):
    if isinstance(obj, (pd.Timestamp, pd.Timedelta)):
        return str(obj)
    return str(obj)

with open("scratch/data_raw_inspection.json", "w") as f:
    json.dump(raw_files_info, f, indent=2, default=json_default)

print("Saved inspection to scratch/data_raw_inspection.json")
