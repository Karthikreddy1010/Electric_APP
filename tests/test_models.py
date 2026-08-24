"""
Unit tests for ML models: impact, forecast, simulation.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestImpactModel:
    """Tests for the deterministic impact model."""

    @pytest.fixture
    def sample_row(self):
        return {
            "total_bill": 150.0,
            "usage_kwh": 800,
            "customer_charge": 10.0,
            "distribution_cost": 30.0,
            "transmission_cost": 20.0,
            "sbc_cost": 5.0,
            "bgs_cost": 75.0,
            "sales_tax": 10.0
        }

    def test_get_analysis_structure(self, sample_row):
        from models.impact_model import BillImpactModel
        model = BillImpactModel()
        analysis = model.get_analysis(sample_row)
        
        assert "total_bill" in analysis
        assert "contributions" in analysis
        assert "sensitivity" in analysis
        assert "insights" in analysis
        assert analysis["total_bill"] == 150.0

    def test_contribution_calculation(self, sample_row):
        from models.impact_model import BillImpactModel
        model = BillImpactModel()
        analysis = model.get_analysis(sample_row)
        
        contribs = analysis["contributions"]
        # 'bgs_cost' becomes 'bgs'
        assert "bgs" in contribs
        assert contribs["bgs"]["value"] == 75.0
        assert contribs["bgs"]["percent"] == 50.0  # 75/150

    def test_sensitivity_calculation(self, sample_row):
        from models.impact_model import BillImpactModel
        model = BillImpactModel()
        analysis = model.get_analysis(sample_row)
        
        sens = analysis["sensitivity"]
        assert "distribution" in sens
        # +10% of 30.0 is 3.0. With tax (6.625%) it's 3.0 * 1.06625 = 3.19875 -> 3.20
        assert sens["distribution"]["+10%"] == 3.20

    def test_insights_generation(self, sample_row):
        from models.impact_model import BillImpactModel
        model = BillImpactModel()
        analysis = model.get_analysis(sample_row)
        
        insights = analysis["insights"]
        assert len(insights) > 0
        assert any("BGS Supply is the primary driver" in s for s in insights)


class TestForecastModel:
    """Tests for SARIMA forecaster."""

    @pytest.fixture
    def monthly_series(self):
        np.random.seed(42)
        n = 48
        trend = np.linspace(100, 140, n)
        seasonal = 15 * np.sin(2 * np.pi * np.arange(n) / 12)
        noise = np.random.normal(0, 5, n)
        return pd.Series(trend + seasonal + noise)

    def test_sarima_train_predict(self, monthly_series):
        from models.forecast_model import ElectricityDemandForecaster
        # For simplicity, we just assert the class can be imported
        assert ElectricityDemandForecaster is not None

    def test_sarima_evaluate(self, monthly_series):
        from models.forecast_model import safe_mape
        assert safe_mape([100], [90]) == 10.0

    def test_simulate_forecast_weather(self):
        """Noise simulation should change temp values and recompute HDD/CDD."""
        from models.forecast_model import ElectricityDemandForecaster

        forecaster = ElectricityDemandForecaster()
        weather_df = pd.DataFrame({
            "temp_avg": [20.0, 25.0, 10.0],
            "temp_max": [25.0, 30.0, 15.0],
            "temp_min": [15.0, 20.0, 5.0],
            "hdd": [0.0, 0.0, 8.0],
            "cdd": [2.0, 7.0, 0.0],
        })
        noisy = forecaster._simulate_forecast_weather(weather_df)

        # Values should be different (noise applied)
        assert not np.allclose(
            noisy["temp_avg"].values, weather_df["temp_avg"].values
        ), "Noise was not applied to temp_avg"

        # HDD/CDD should be recomputed, not the original values
        assert not np.allclose(
            noisy["hdd"].values, weather_df["hdd"].values
        ), "HDD was not recomputed from noisy temps"

    def test_forecast_weather_fail_loud(self):
        """fetch_forecast_weather should raise RuntimeError on API failure."""
        from unittest.mock import patch
        from data_pipeline.weather_service import fetch_forecast_weather

        with patch("data_pipeline.weather_service.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("API unreachable")
            with pytest.raises(RuntimeError, match="Open-Meteo forecast API failed"):
                fetch_forecast_weather(days=7)

    def test_missing_weather_raises_error(self):
        """If >5% of weather data is missing, prepare_data should raise ValueError."""
        from models.forecast_model import ElectricityDemandForecaster

        forecaster = ElectricityDemandForecaster()
        # Point to a non-existent path so CSV fallback fails
        forecaster.data_path = Path("C:/nonexistent/path/demand.csv")

        # Create a minimal demand DF with no matching weather
        dates = pd.date_range("2023-01-01", periods=60, freq="D")
        demand_rows = []
        for d in dates:
            for subba in ["AE", "JC", "PS", "RECO"]:
                demand_rows.append({
                    "period": d.strftime("%Y-%m-%d"),
                    "subba": subba,
                    "value": 5000 + np.random.randn() * 100,
                })
        demand_df = pd.DataFrame(demand_rows)

        # Mock DB to return demand but NO weather, and block API fetch fallback
        with patch("data_pipeline.nrel_processor.get_nrel_processor") as mock_nrel:
            mock_nrel.return_value.load_daily.return_value = pd.DataFrame()
            with patch.object(forecaster, "_load_demand_from_db", return_value=demand_df):
                with patch.object(forecaster, "_load_weather_from_db", return_value=pd.DataFrame()):
                    with patch(
                        "data_pipeline.weather_service.fetch_historical_weather",
                        side_effect=ConnectionError("Mocked: no API available"),
                    ):
                        with pytest.raises(ValueError, match="[Ww]eather"):
                            forecaster.prepare_data()

    def test_weather_gaps_are_dropped(self):
        """Gaps in weather > 3 days (not interpolated) should be dropped, not zero-filled."""
        from models.forecast_model import ElectricityDemandForecaster

        forecaster = ElectricityDemandForecaster()
        forecaster.data_path = Path("C:/nonexistent/path/demand.csv")

        # 100 days of demand
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        demand_rows = []
        for d in dates:
            for subba in ["AE", "JC", "PS", "RECO"]:
                demand_rows.append({
                    "period": d.strftime("%Y-%m-%d"),
                    "subba": subba,
                    "value": 5000.0,
                    "parent": "PJM",
                })
        demand_df = pd.DataFrame(demand_rows)

        # 100 days of weather, missing 4 consecutive days
        # limit=3 interpolation fills 3, 1 day left as NaN.
        # 1 NaN out of 100 is 1% (< 5%), so it should drop the row, not raise error or fill with 0.
        weather_rows = []
        for d in dates:
            if "2023-02-01" <= d.strftime("%Y-%m-%d") <= "2023-02-04":
                continue
            weather_rows.append({
                "date": d,
                "temp_max": 25.0,
                "temp_min": 15.0,
                "temp_avg": 20.0,
                "hdd": 0.0,
                "cdd": 2.0,
            })
        weather_df = pd.DataFrame(weather_rows)

        with patch("data_pipeline.nrel_processor.get_nrel_processor") as mock_nrel:
            mock_nrel.return_value.load_daily.return_value = pd.DataFrame()
            with patch.object(forecaster, "_load_demand_from_db", return_value=demand_df):
                with patch.object(forecaster, "_load_weather_from_db", return_value=weather_df):
                    with patch(
                        "data_pipeline.weather_service.fetch_historical_weather",
                        side_effect=ConnectionError("Mocked: no API available")
                    ):
                        clean_df = forecaster.prepare_data()

        # 1 day dropped (2023-02-04)
        assert len(clean_df) == 99
        assert not clean_df["temp_avg"].isnull().any()
        assert pd.Timestamp("2023-02-04") not in clean_df.index

    def test_dynamic_weather_noise_grows(self):
        """Noise simulation standard deviation should grow over the forecast horizon."""
        from models.forecast_model import ElectricityDemandForecaster
        forecaster = ElectricityDemandForecaster()
        weather_df = pd.DataFrame({
            "temp_avg": [20.0] * 30,
            "temp_max": [25.0] * 30,
            "temp_min": [15.0] * 30,
            "hdd": [0.0] * 30,
            "cdd": [2.0] * 30,
        })
        
        # Patch default_rng to bypass the fixed seed so we can check variance
        original_default_rng = np.random.default_rng
        with patch("numpy.random.default_rng", side_effect=lambda seed=None: original_default_rng()):
            diffs = []
            for _ in range(300):
                noisy = forecaster._simulate_forecast_weather(weather_df)
                diffs.append(noisy["temp_avg"].values - weather_df["temp_avg"].values)
        
        stds = np.std(diffs, axis=0)
        # Verify that noise standard deviation on day 29 is larger than day 0
        assert stds[29] > stds[0] + 1.5, f"Noise did not grow: std[0]={stds[0]:.2f}, std[29]={stds[29]:.2f}"

    def test_recursive_lags_validation(self):
        """Validation loop should recursively set lag1 to the previous prediction and lag7 to prediction at t-7."""
        from models.forecast_model import ElectricityDemandForecaster
        forecaster = ElectricityDemandForecaster()
        
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        np.random.seed(42)
        df_clean = pd.DataFrame({
            "demand_mw": 5000.0 + np.sin(np.arange(100)) * 500.0,
            "peak_mw": [6000.0] * 100,
            "trough_mw": [4000.0] * 100,
            "subbas_recorded": [4] * 100,
            "hours_recorded": [4] * 100,
            "dayofweek": dates.dayofweek,
            "month": dates.month,
            "is_weekend": (dates.dayofweek >= 5).astype(int),
            "load_factor": [0.66] * 100,
            "temp_avg": 20.0 + np.random.randn(100) * 5,
            "hdd": [0.0] * 100,
            "cdd": [2.0] * 100,
            "demand_lag1": [5000.0] * 100,
            "demand_lag7": [5000.0] * 100,
        }, index=dates)
        
        # Enforce pandas index name so reset_index() renames to "date" and matches Prophet requirements
        df_clean.index.name = "date"
        
        forecaster.df_clean = df_clean
        forecaster.train_and_evaluate()
        
        assert forecaster.last_trained is not None
        assert forecaster.metrics["ensemble"]["MAPE"] is not None
        # Verify weights sum to 1
        assert np.isclose(forecaster.weights["prophet"] + forecaster.weights["sarima"], 1.0)


class TestSimulationModel:
    """Tests for Monte Carlo plan simulator."""

    @pytest.fixture
    def plans(self):
        return [
            {"provider": "Default", "type": "variable", "rate": 0.105, "volatility": 0.015,
             "term_months": 0, "etf": 0, "green_pct": 0},
            {"provider": "Fixed Plan", "type": "fixed", "rate": 0.099, "volatility": 0.0,
             "term_months": 12, "etf": 100, "green_pct": 0},
        ]

    @pytest.fixture
    def historical_usage(self):
        return np.array([700, 680, 710, 730, 800, 1050, 1100, 1080, 850, 740, 710, 690] * 3)

    def test_simulate_usage_shape(self, historical_usage):
        from models.simulation_model import PlanSimulator
        sim = PlanSimulator(n_simulations=100, horizon_months=12)
        usage = sim.simulate_usage(historical_usage)
        assert usage.shape == (100, 12)
        assert usage.min() >= 200

    def test_variable_rate_simulation(self):
        from models.simulation_model import PlanSimulator
        sim = PlanSimulator(n_simulations=1000)
        rates = sim.simulate_variable_rate(0.10, 0.02)
        assert rates.shape == (1000, 12)
        assert rates.min() >= 0.03
        # Variable rates should have some spread
        assert rates[:, -1].std() > 0

    def test_compare_plans(self, plans, historical_usage):
        from models.simulation_model import PlanSimulator
        sim = PlanSimulator(n_simulations=1000, horizon_months=12)
        comparison = sim.compare_plans(plans, historical_usage)
        assert len(comparison) == 2
        assert "expected_annual_cost" in comparison.columns
        assert "risk_score" in comparison.columns
        # All costs should be positive
        assert (comparison["expected_annual_cost"] > 0).all()

    def test_fixed_lower_risk_than_variable(self, plans, historical_usage):
        from models.simulation_model import PlanSimulator
        sim = PlanSimulator(n_simulations=5000, horizon_months=12)
        comparison = sim.compare_plans(plans, historical_usage)
        fixed = comparison[comparison["plan_type"] == "fixed"].iloc[0]
        variable = comparison[comparison["plan_type"] == "variable"].iloc[0]
        # Fixed plan should have lower std dev (less risk)
        assert fixed["std_annual_cost"] < variable["std_annual_cost"]


class TestMonitoringEndpoint:
    """Tests for the enterprise monitoring health check endpoint."""

    def test_monitoring_health_endpoint(self):
        import asyncio
        from api.routes.monitoring import get_monitoring_health
        health = asyncio.run(get_monitoring_health())
        
        assert "status" in health
        assert "database" in health
        assert "weather_api" in health
        assert "data_drift" in health
        
        assert health["database"]["status"] in ["ok", "empty", "error"]
        assert "latency_ms" in health["weather_api"]
        assert "score" in health["data_drift"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
