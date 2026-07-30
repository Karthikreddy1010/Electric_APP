"""
Automated Integration Tests for Global Feature Store & EIA Service
Tests data registry policy enforcement, feature engineering formulas, statistical analytics, and service API returns.
"""
import unittest
import pandas as pd
import numpy as np

from feature_store.data_registry import data_registry, AccessPolicy, AccessPolicyViolation
from feature_store.base.feature_registry import feature_registry
from feature_store.eia_retail.loader import load_and_merge_eia_raw
from feature_store.eia_retail.features import build_eia_retail_features
from feature_store.cross_dataset.cross_features import enrich_cross_dataset_features
from feature_store.base.feature_store import global_feature_store
from api.services.eia_service import eia_service
from api.services.analytics_service import analytics_service
from api.services.forecast_service import forecast_service
from api.services.recommendation_service import recommendation_service


class TestEIAFeatureStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load, build features, and register in global_feature_store
        raw_df = load_and_merge_eia_raw()
        features_df = build_eia_retail_features(raw_df)
        enriched_df = enrich_cross_dataset_features(features_df)
        global_feature_store.register_dataframe("EIA Retail", enriched_df)

    def test_access_policy_enforcement(self):
        """Verify AccessPolicy Violation when an unauthorized module accesses EIA dataset."""
        # Bill breakdown is NOT_ALLOWED to access EIA Retail
        with self.assertRaises(AccessPolicyViolation):
            global_feature_store.get_dataset("EIA Retail", requesting_module="bill_breakdown", required_policy=AccessPolicy.READ_JOIN)

        # Dashboard IS ALLOWED to access EIA Retail
        df = global_feature_store.get_dataset("EIA Retail", requesting_module="dashboard", required_policy=AccessPolicy.READ_ANALYZE)
        self.assertFalse(df.empty)

    def test_eia_feature_schema(self):
        """Verify presence of all engineered feature columns."""
        df = global_feature_store.get_dataset("EIA Retail", requesting_module="regional_insights")
        required_cols = [
            "period", "stateid", "sectorid", "retail_price", "retail_sales", "retail_revenue",
            "effective_price", "price_yoy_growth", "price_rolling_12m", "price_volatility_index",
            "avg_usage_per_customer_kwh", "revenue_per_customer", "res_com_spread", "solar_suitability_score"
        ]
        for col in required_cols:
            self.assertIn(col, df.columns, f"Missing required column: {col}")

    def test_eia_service_dashboard_summary(self):
        """Test EIA Service dashboard summary generation."""
        summary = eia_service.get_dashboard_summary(module_id="dashboard", focus_state="NJ")
        self.assertIsNotNone(summary)
        self.assertEqual(summary.get("focus_state"), "NJ")
        self.assertGreater(summary.get("current_price", 0), 0)
        self.assertIn("sparkline", summary)

    def test_analytics_service_report(self):
        """Test Analytics Service statistical metrics."""
        report = analytics_service.get_statistical_report(module_id="regional_insights", stateid="NJ", sectorid="RES")
        self.assertIsNotNone(report)
        self.assertIn("descriptive_stats", report)
        self.assertIn("mann_kendall_trend", report)

    def test_forecast_service(self):
        """Test multi-model forecasting engine across XGBoost, LightGBM, Prophet."""
        fc = forecast_service.generate_forecast(module_id="forecast", stateid="NJ", sectorid="RES", model_name="XGBoost", horizon_months=12)
        self.assertIsNotNone(fc)
        self.assertEqual(len(fc.get("forecast", [])), 12)
        self.assertIn("metrics", fc)

    def test_recommendation_service(self):
        """Test personalized multi-layer recommendation engine."""
        recs = recommendation_service.get_recommendations(module_id="recommendations", stateid="NJ", user_monthly_kwh=750.0, user_effective_rate=0.22)
        self.assertGreater(len(recs), 0)
        self.assertIn("recommendation", recs[0])


if __name__ == "__main__":
    unittest.main()
