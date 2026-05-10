"""
Data storage utilities - write processed data to Parquet and SQLite.
"""
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def save_to_parquet(df: pd.DataFrame, output_dir: str, name: str) -> str:
    """Save DataFrame to compressed Parquet file."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(df)} rows to {path}")
    return str(path)


def save_to_sqlite(df: pd.DataFrame, db_path: str, table_name: str,
                   if_exists: str = "replace") -> None:
    """Save DataFrame to SQLite database (dev mode)."""
    import sqlite3
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    df.to_sql(table_name, conn, if_exists=if_exists, index=False)
    conn.close()
    logger.info(f"Saved {len(df)} rows to {table_name} in {path}")


def load_processed_data(data_dir: str) -> dict:
    """Load all processed Parquet files from directory."""
    path = Path(data_dir)
    datasets = {}
    for f in path.glob("*.parquet"):
        datasets[f.stem] = pd.read_parquet(f)
        logger.info(f"Loaded {f.stem}: {datasets[f.stem].shape}")
    return datasets
