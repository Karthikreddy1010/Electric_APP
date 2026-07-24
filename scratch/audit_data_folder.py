import os
import json
import sqlite3
from pathlib import Path
import pandas as pd

data_dir = Path("data")
db_path = Path("electric.db")

results = []

def analyze_df(df, rel_path):
    n_rows, n_cols = df.shape
    cols = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in cols}
    null_pct = round(float(df.isnull().mean().mean() * 100), 2) if n_rows > 0 else 0.0
    dup_cnt = int(df.duplicated().sum()) if n_rows > 0 else 0
    
    date_range = "N/A"
    date_cols = [c for c in cols if any(k in c.lower() for k in ['date', 'period', 'year', 'time', 'month'])]
    if date_cols and n_rows > 0:
        c = date_cols[0]
        try:
            date_range = f"{df[c].min()} to {df[c].max()}"
        except Exception:
            pass
            
    return {
        "path": str(rel_path),
        "rows": n_rows,
        "cols": n_cols,
        "col_names": cols,
        "dtypes": dtypes,
        "null_pct": null_pct,
        "dup_cnt": dup_cnt,
        "date_range": str(date_range)
    }

print("=== STARTING DATASET AUDIT ===")

file_audit = []

PROJECT_ROOT = Path(__file__).resolve().parent.parent

for root, dirs, files in os.walk(data_dir):
    for f in sorted(files):
        fp = Path(root) / f
        rel = fp.relative_to(Path("."))
        size_bytes = fp.stat().st_size
        if size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        ext = fp.suffix.lower()
        
        entry = {
            "path": str(fp),
            "rel_path": str(fp).replace("\\", "/"),
            "size": size_str,
            "size_bytes": size_bytes,
            "ext": ext,
            "mtime": pd.to_datetime(fp.stat().st_mtime, unit='s').strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if ext == ".parquet":
            try:
                df = pd.read_parquet(fp)
                entry.update(analyze_df(df, fp))
            except Exception as e:
                entry["error"] = str(e)
        elif ext == ".csv":
            try:
                df = pd.read_csv(fp)
                entry.update(analyze_df(df, fp))
            except Exception as e:
                entry["error"] = str(e)
        elif ext in [".json", ".jsonl"]:
            entry["category"] = "JSON Document/Annotations"
        elif ext in [".png", ".jpg", ".jpeg", ".pdf", ".txt"]:
            entry["category"] = "Media / PDF / OCR text"
            
        file_audit.append(entry)

print(f"Scanned total {len(file_audit)} files.")

# Also inspect SQLite database electric.db if exists
if db_path.exists():
    print("Found electric.db database!")
    conn = sqlite3.connect(db_path)
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)['name'].tolist()
    print(f"Tables in electric.db: {tables}")
    db_audit = []
    for t in tables:
        df_t = pd.read_sql(f"SELECT * FROM {t};", conn)
        info = analyze_df(df_t, f"electric.db::{t}")
        info["size"] = f"{len(df_t)} rows"
        info["ext"] = "SQLite table"
        db_audit.append(info)
    conn.close()
    with open("scratch/db_audit.json", "w") as f:
        json.dump(db_audit, f, indent=2)

with open("scratch/data_files_audit.json", "w") as f:
    json.dump(file_audit, f, indent=2)

print("Saved audit data to scratch/data_files_audit.json and scratch/db_audit.json")
