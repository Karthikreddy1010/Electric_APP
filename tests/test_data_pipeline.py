"""
Unit tests for the data pipeline: synthetic data, cleaning, feature engineering.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestSyntheticData:
    """Tests for synthetic data generation."""

    def test_billing_data_shape(self):
        from data_pipeline.synthetic_data import generate_billing_data
        df = generate_billing_data("2020-01-01", "2022-12-31")
        assert len(df) == 36  # 3 years * 12 months
        assert "date" in df.columns
        assert "total_bill" in df.columns
        assert "usage_kwh" in df.columns

    def test_billing_data_values(self):
        from data_pipeline.synthetic_data import generate_billing_data
        df = generate_billing_data()
        assert df["usage_kwh"].min() >= 300
        assert df["total_bill"].min() > 0
        assert df["sales_tax"].min() >= 0
        # BGS should be largest component
        assert df["bgs_cost"].mean() > df["sbc_cost"].mean()

    def test_weather_data_hdd_cdd(self):
        from data_pipeline.synthetic_data import generate_weather_data
        df = generate_weather_data("2020-01-01", "2020-12-31")
        assert len(df) == 366  # 2020 is leap year
        # HDD and CDD should be mutually exclusive at temp=65
        assert (df["hdd"] * df["cdd"]).sum() == 0  # Can't have both > 0
        # Summer should have CDD, winter should have HDD
        summer = df[df["date"].dt.month.isin([7, 8])]
        winter = df[df["date"].dt.month.isin([1, 2])]
        assert summer["cdd"].mean() > winter["cdd"].mean()
        assert winter["hdd"].mean() > summer["hdd"].mean()

    def test_pjm_data_lmp_range(self):
        from data_pipeline.synthetic_data import generate_pjm_data
        df = generate_pjm_data()
        assert df["lmp_da"].min() >= 10
        assert df["lmp_da"].max() <= 500
        assert "zone" in df.columns

    def test_state_benchmarks(self):
        from data_pipeline.synthetic_data import generate_state_benchmarks
        df = generate_state_benchmarks()
        assert "NJ" in df["state"].values
        nj = df[df["state"] == "NJ"]
        assert len(nj) == 7  # 2019-2025
        assert nj["avg_rate"].mean() > 0.15  # NJ is above average

    def test_retail_plans(self):
        from data_pipeline.synthetic_data import generate_retail_plans
        df = generate_retail_plans()
        assert len(df) >= 5
        assert "fixed" in df["type"].values
        assert "variable" in df["type"].values
        fixed = df[df["type"] == "fixed"]
        assert (fixed["volatility"] == 0).all()

    def test_generate_all_creates_files(self, tmp_path):
        from data_pipeline.synthetic_data import generate_all
        datasets = generate_all(str(tmp_path))
        assert len(datasets) == 5
        assert (tmp_path / "billing.parquet").exists()
        assert (tmp_path / "weather.parquet").exists()
        assert (tmp_path / "pjm_market.csv").exists()


class TestCleaners:
    """Tests for data cleaning pipeline."""

    def test_billing_cleaner_handles_missing(self):
        from data_pipeline.cleaners import BillingCleaner
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=12, freq="MS"),
            "usage_kwh": [700, np.nan, 750, 800, 850, 900, 1000, 950, 800, 750, 700, 680],
            "total_bill": [100, 110, np.nan, 120, 130, 140, 160, 150, 130, 120, 105, 100],
            "bgs_rate": [0.08]*12,
            "bgs_cost": [56]*12,
            "transmission_rate": [0.015]*12,
            "transmission_cost": [10]*12,
            "distribution_rate": [0.04]*12,
            "distribution_cost": [28]*12,
            "sbc_rate": [0.005]*12,
            "sbc_cost": [3.5]*12,
            "nug_rate": [0.003]*12,
            "nug_cost": [2.1]*12,
            "subtotal": [95]*12,
        })
        cleaner = BillingCleaner()
        clean_df = cleaner.clean(df)
        assert clean_df["usage_kwh"].isna().sum() == 0
        assert clean_df["total_bill"].isna().sum() == 0
        assert "effective_rate" in clean_df.columns

    def test_billing_cleaner_removes_negative_usage(self):
        from data_pipeline.cleaners import BillingCleaner
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=6, freq="MS"),
            "usage_kwh": [700, -50, 750, 800, 850, 900],
            "total_bill": [100, 110, 105, 120, 130, 140],
            "subtotal": [95]*6,
        })
        cleaner = BillingCleaner()
        clean_df = cleaner.clean(df)
        assert (clean_df["usage_kwh"] >= 0).all()

    def test_weather_cleaner_recomputes_hdd_cdd(self):
        from data_pipeline.cleaners import WeatherCleaner
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=10, freq="D"),
            "avg_temp_f": [30, 45, 60, 70, 80, 90, 65, 50, 40, 35],
            "hdd": [0]*10,  # intentionally wrong
            "cdd": [0]*10,
            "precip_in": [0]*10,
            "humidity_pct": [50]*10,
        })
        cleaner = WeatherCleaner()
        clean_df = cleaner.clean(df)
        # HDD should be recomputed
        assert clean_df.loc[0, "hdd"] == 35.0  # 65 - 30
        assert clean_df.loc[4, "cdd"] == 15.0  # 80 - 65


class TestFeatureEngineering:
    """Tests for feature engineering pipeline."""

    def test_temporal_features(self):
        from data_pipeline.features import add_temporal_features
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=12, freq="MS"),
            "value": range(12),
        })
        result = add_temporal_features(df)
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns
        assert "is_summer_peak" in result.columns
        assert result.loc[5, "is_summer_peak"] == 1  # June

    def test_lag_features(self):
        from data_pipeline.features import add_lag_features
        df = pd.DataFrame({"value": range(20)})
        result = add_lag_features(df, "value", lags=[1, 3])
        assert "value_lag_1" in result.columns
        assert "value_lag_3" in result.columns
        assert result.loc[5, "value_lag_1"] == 4
        assert result.loc[5, "value_lag_3"] == 2

    def test_rolling_features(self):
        from data_pipeline.features import add_rolling_features
        df = pd.DataFrame({"value": [10, 20, 30, 40, 50]})
        result = add_rolling_features(df, "value", windows=[3])
        assert "value_rolling_mean_3" in result.columns
        assert abs(result.loc[2, "value_rolling_mean_3"] - 20.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
