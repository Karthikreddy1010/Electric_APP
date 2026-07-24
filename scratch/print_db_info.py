import json

with open("scratch/db_audit.json") as f:
    db = json.load(f)

for t in db:
    print(f"Table: {t['path']} | Rows: {t['rows']} | Cols: {t['cols']} | Nulls: {t['null_pct']}%")
    print(f"  Columns: {t['col_names']}\n")
