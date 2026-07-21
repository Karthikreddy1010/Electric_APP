"""
PJM Locational Marginal Pricing (LMP) Ingestion & Seeding Pipeline.
Reads day-ahead hourly LMP components from raw/da_hrl_lmps(1).csv and loads them into database tables.
"""
from __future__ import annotations

import logging
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path
from database.connection import get_sync_session, get_sync_engine
from database.models import PjmLmpNode, PjmLmpHourly
from data_pipeline.config import RAW_DIR

logger = logging.getLogger(__name__)


def sync_pjm_lmps(limit_nodes: int = 25, limit_days: int = 14) -> int:
    """
    Parses da_hrl_lmps(1).csv and seeds PjmLmpNode and PjmLmpHourly tables.
    Assigns realistic latitude/longitude coordinates to nodes for map visualizations.
    """
    logger.info("Initializing PJM LMP Ingestion Pipeline...")
    csv_path = Path(RAW_DIR) / "da_hrl_lmps(1).csv"

    if not csv_path.exists():
        logger.error(f"PJM LMP raw CSV file not found at: {csv_path}")
        return 0

    # Load a portion of the CSV using pandas
    try:
        # Columns: datetime_beginning_ept, pnode_id, pnode_name, zone, system_energy_price_da, total_lmp_da, congestion_price_da, marginal_loss_price_da
        df = pd.read_csv(
            csv_path,
            usecols=[
                "datetime_beginning_ept",
                "pnode_id",
                "pnode_name",
                "zone",
                "system_energy_price_da",
                "total_lmp_da",
                "congestion_price_da",
                "marginal_loss_price_da"
            ]
        )
    except Exception as e:
        logger.error(f"Failed to read PJM CSV: {e}")
        return 0

    # Fill NaN zones
    df["zone"] = df["zone"].fillna("PJM-RTO")
    df["pnode_id"] = df["pnode_id"].astype(str)

    # 1. Identify unique nodes and seed them
    unique_nodes = df.drop_duplicates(subset=["pnode_id"]).copy()
    
    # Filter to PSEG, JCPL, AECO, RECO or top zones to keep database lean
    top_zones = ["PSEG", "JCPL", "AECO", "RECO", "PJM-RTO", "MID-ATL/APS"]
    unique_nodes = unique_nodes[unique_nodes["zone"].isin(top_zones)]
    
    # Limit to top N nodes to optimize performance
    unique_nodes = unique_nodes.head(limit_nodes)

    node_records = []
    # Seed coordinates mapping
    # NJ box: lat 38.9 to 41.3, lng -75.5 to -73.9
    np.random.seed(42)
    for _, row in unique_nodes.iterrows():
        zone = str(row["zone"])
        
        # Center points for NJ utility EDCs
        if zone == "PSEG":
            lat = np.random.uniform(40.5, 40.9)
            lng = np.random.uniform(-74.3, -74.1)
        elif "JC" in zone or "JCP" in zone:
            lat = np.random.uniform(40.1, 40.4)
            lng = np.random.uniform(-74.6, -74.2)
        elif "AECO" in zone or "ACE" in zone:
            lat = np.random.uniform(39.3, 39.7)
            lng = np.random.uniform(-74.8, -74.4)
        elif "RECO" in zone:
            lat = np.random.uniform(41.0, 41.2)
            lng = np.random.uniform(-74.2, -74.0)
        else: # PJM RTO
            lat = np.random.uniform(39.8, 40.2)
            lng = np.random.uniform(-75.2, -74.8)

        node_records.append({
            "node_id": str(row["pnode_id"]),
            "name": str(row["pnode_name"]),
            "zone": zone,
            "latitude": round(lat, 5),
            "longitude": round(lng, 5)
        })

    # Save nodes in database
    with get_sync_session() as session:
        for nr in node_records:
            exists = session.query(PjmLmpNode).filter_by(node_id=nr["node_id"]).first()
            if not exists:
                session.add(PjmLmpNode(**nr))
        session.commit()
    logger.info(f"Seeded {len(node_records)} unique grid nodes with NJ geographical coordinates.")

    # 2. Ingest hourly pricing records for the seeded nodes
    node_ids = [nr["node_id"] for nr in node_records]
    hourly_df = df[df["pnode_id"].isin(node_ids)].copy()
    
    # Parse timestamps
    hourly_df["timestamp"] = pd.to_datetime(hourly_df["datetime_beginning_ept"])
    
    # Filter to last N days of data to keep database small and fast
    latest_ts = hourly_df["timestamp"].max()
    start_ts = latest_ts - pd.Timedelta(days=limit_days)
    hourly_df = hourly_df[hourly_df["timestamp"] >= start_ts]

    logger.info(f"Ingesting {len(hourly_df)} hourly LMP price records...")
    
    inserted_count = 0
    with get_sync_session() as session:
        for _, row in hourly_df.iterrows():
            ts = row["timestamp"].to_pydatetime()
            exists = session.query(PjmLmpHourly).filter_by(
                node_id=str(row["pnode_id"]),
                timestamp=ts
            ).first()
            
            if not exists:
                session.add(PjmLmpHourly(
                    node_id=str(row["pnode_id"]),
                    timestamp=ts,
                    total_lmp=float(row["total_lmp_da"]),
                    energy_comp=float(row["system_energy_price_da"]),
                    congestion_comp=float(row["congestion_price_da"]),
                    loss_comp=float(row["marginal_loss_price_da"])
                ))
                inserted_count += 1
                
                # Commit in batches of 500
                if inserted_count % 500 == 0:
                    session.commit()
        session.commit()

    logger.info(f"Successfully seeded {inserted_count} hourly pricing records into pjm_lmp_hourly.")
    return inserted_count
