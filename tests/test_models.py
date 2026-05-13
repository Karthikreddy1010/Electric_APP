"""
Unit tests for ML models: impact, forecast, simulation.
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

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
        from models.forecast_model import SARIMAForecaster
        model = SARIMAForecaster(order=(1, 1, 0), seasonal_order=(0, 1, 0, 12))
        model.train(monthly_series)
        preds = model.predict(steps=6)
        assert len(preds) == 6
        assert "forecast" in preds.columns
        assert "lower" in preds.columns
        assert "upper" in preds.columns
        assert (preds["upper"] >= preds["forecast"]).all()

    def test_sarima_evaluate(self, monthly_series):
        from models.forecast_model import SARIMAForecaster
        model = SARIMAForecaster()
        train, test = monthly_series[:36], monthly_series[36:]
        metrics = model.evaluate(train, test)
        assert "rmse" in metrics
        assert "mape" in metrics
        assert metrics["rmse"] > 0


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
