import json
import pandas as pd
from pathlib import Path

with open("scratch/data_files_audit.json") as f:
    files = json.load(f)

print(f"Total files audited: {len(files)}")

# Group by directory / dataset group
groups = {}
tabular_files = []
non_tabular_groups = {}

for f in files:
    rel = f["rel_path"]
    ext = f.get("ext", "")
    parts = rel.split("/")
    
    if len(parts) > 1:
        top_dir = parts[1]
    else:
        top_dir = "root"
        
    if "rows" in f:
        tabular_files.append(f)
    else:
        non_tabular_groups[top_dir] = non_tabular_groups.get(top_dir, 0) + 1

print("\n=== TABULAR DATASETS IN DATA/ ===")
tabular_df = pd.DataFrame(tabular_files)
print(f"Found {len(tabular_df)} tabular data files.")

for idx, r in tabular_df.iterrows():
    cols_preview = ", ".join(r["col_names"][:5]) + ("..." if len(r["col_names"]) > 5 else "")
    print(f"[{idx+1}] {r['rel_path']}")
    print(f"    Size: {r['size']} | Rows: {r['rows']} | Cols: {r['cols']} | Nulls: {r['null_pct']}% | Dups: {r['dup_cnt']}")
    print(f"    Dates: {r['date_range']} | Dtypes/Cols: {cols_preview}")
    print()

print("\n=== NON-TABULAR ASSETS GROUPS ===")
for g, count in non_tabular_groups.items():
    print(f"Folder '{g}': {count} files (PNG/PDF/JSON/TXT synthetic bill assets)")

if Path("scratch/db_audit.json").exists():
    with open("scratch/db_audit.json") as f:
        db_tables = json.load(f)
    print("\n=== SQLITE DATABASE (electric.db) TABLES ===")
    for t in db_tables:
        cols_preview = ", ".join(t["col_names"][:6]) + ("..." if len(t["col_names"]) > 6 else "")
        print(f"Table '{t['path']}': {t['rows']} rows, {t['cols']} cols | Nulls: {t['null_pct']}% | Dups: {t['dup_cnt']}")
        print(f"  Cols: {cols_preview}")
