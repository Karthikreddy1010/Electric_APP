import sqlite3
import pandas as pd

conn = sqlite3.connect("data/electricity.db")
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)['name'].tolist()

print(f"Total SQLite Tables in data/electricity.db: {len(tables)}\n")

for t in sorted(tables):
    try:
        df = pd.read_sql(f"SELECT * FROM {t} LIMIT 5;", conn)
        count = pd.read_sql(f"SELECT COUNT(*) as c FROM {t};", conn)['c'].iloc[0]
        null_pct = round(float(df.isnull().mean().mean() * 100), 2)
        print(f"Table: '{t}' | Rows: {count} | Cols ({len(df.columns)}): {list(df.columns)}")
    except Exception as e:
        print(f"Error table {t}: {e}")

conn.close()
