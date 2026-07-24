import json
import pandas as pd

with open("scratch/data_raw_inspection.json") as f:
    raw_info = json.load(f)

print(f"Loaded inspection for {len(raw_info)} files under data/raw/\n")

df_meta = []
for item in raw_info:
    if "rows" in item:
        df_meta.append({
            "rel_path": item["rel_path"],
            "size": item["size"],
            "rows": item["rows"],
            "cols": item["cols"],
            "null_pct": item["null_pct"],
            "dup_rows": item["duplicate_rows"],
            "date_range": item["date_range"],
            "columns": item["column_list"],
            "sample": item.get("sample_records", [])[:1]
        })

print(f"Tabular datasets count: {len(df_meta)}\n")

for i, m in enumerate(sorted(df_meta, key=lambda x: x["rel_path"]), 1):
    cols_str = ", ".join(m["columns"][:6]) + ("..." if len(m["columns"]) > 6 else "")
    print(f"[{i}] {m['rel_path']}")
    print(f"    Size: {m['size']} | Rows: {m['rows']} | Cols: {m['cols']} | Nulls: {m['null_pct']}% | Dups: {m['dup_rows']}")
    print(f"    Dates: {m['date_range']}")
    print(f"    Cols ({m['cols']}): {cols_str}\n")
