"""
DataService: loads data, runs cleaning/feature pipeline, trains models.
Initialized once at startup and held in app.extensions['svc'].
"""
from __future__ import annotations

import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class DataService:
    """
    Singleton service that owns all data and trained models.
    Never retrain inside request handlers — use this service.
    """

    def __init__(self):
        self.billing_df: pd.DataFrame | None = None
        self.weather_df: pd.DataFrame | None = None
        self.market_df: pd.DataFrame | None = None
        self.benchmark_df: pd.DataFrame | None = None
        self.plans_df: pd.DataFrame | None = None
        self.feature_matrix: pd.DataFrame | None = None
        self.feature_cols: list[str] | None = None
        self.impact_model = None
        self.forecast_model = None
        self._ready = False

    # ─── Public readiness flag ───────────────────────────────────────────────

    @property
    def ready(self) -> bool:
        return self._ready

    # ─── Bootstrap ───────────────────────────────────────────────────────────

    def initialize(self, data_dir: str) -> None:
        """
        Full startup sequence:
        1. Generate synthetic data if missing
        2. Load parquet files
        3. Clean + feature-engineer
        4. Train impact model
        5. Train forecast ensemble
        """
        data_path = Path(data_dir)
        self._ensure_data(data_path)
        self._load_data(data_path)
        self._run_pipeline()
        self._train_impact_model()
        self._train_forecast_model()
        self._ready = True
        logger.info("DataService fully initialized and ready.")

    # ─── Step 1: ensure raw data exists ──────────────────────────────────────

    def _ensure_data(self, data_path: Path) -> None:
        expected = ["billing.parquet", "weather.parquet", "pjm_market.parquet",
                    "state_benchmark.parquet", "retail_plans.parquet"]
        missing = [f for f in expected if not (data_path / f).exists()]
        if missing:
            logger.info(f"Missing files {missing} — generating synthetic data...")
            from data_pipeline.synthetic_data import generate_all
            generate_all(str(data_path))
            logger.info("Synthetic data generated.")

    # ─── Step 2: load parquets ────────────────────────────────────────────────

    def _load_data(self, data_path: Path) -> None:
        try:
            self.billing_df   = pd.read_parquet(data_path / "billing.parquet")
            self.weather_df   = pd.read_parquet(data_path / "weather.parquet")
            self.market_df    = pd.read_parquet(data_path / "pjm_market.parquet")
            self.benchmark_df = pd.read_parquet(data_path / "state_benchmark.parquet")
            self.plans_df     = pd.read_parquet(data_path / "retail_plans.parquet")
            logger.info(f"Loaded billing={len(self.billing_df)}, "
                        f"weather={len(self.weather_df)}, "
                        f"market={len(self.market_df)}, "
                        f"benchmark={len(self.benchmark_df)}, "
                        f"plans={len(self.plans_df)} rows")
        except Exception as exc:
            logger.error(f"Data loading failed: {exc}")
            raise

    # ─── Step 3: clean + feature-engineer ────────────────────────────────────

    def _run_pipeline(self) -> None:
        try:
            from data_pipeline.cleaners import run_cleaning_pipeline
            from data_pipeline.features import build_feature_matrix

            billing, weather, market = run_cleaning_pipeline(
                self.billing_df, self.weather_df, self.market_df
            )
            # Store cleaned billing back for endpoint use
            self.billing_df = billing

            df, feature_cols, _ = build_feature_matrix(billing, weather, market)
            self.feature_matrix = df
            self.feature_cols = feature_cols
            logger.info(f"Feature matrix built: {df.shape[0]} rows × {len(feature_cols)} features")
        except Exception as exc:
            logger.warning(f"Pipeline failed (non-fatal): {exc}")

    # ─── Step 4: impact model ─────────────────────────────────────────────────

    def _train_impact_model(self) -> None:
        try:
            from models.impact_model import BillImpactModel
            self.impact_model = BillImpactModel()
            logger.info("BillImpactModel ready (deterministic — no training required).")
        except Exception as exc:
            logger.warning(f"Impact model init failed: {exc}")

    # ─── Step 5: forecast ensemble ────────────────────────────────────────────

    def _train_forecast_model(self) -> None:
        if self.billing_df is None:
            logger.warning("No billing data — skipping forecast training.")
            return
        try:
            from models.forecast_model import ForecastEnsemble
            ensemble = ForecastEnsemble()
            ensemble.train_all(self.billing_df["total_bill"], self.billing_df["date"])
            self.forecast_model = ensemble
            logger.info("Forecast ensemble trained.")
        except Exception as exc:
            logger.warning(f"Forecast model training failed: {exc}")
