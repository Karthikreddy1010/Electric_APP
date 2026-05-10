"""
Integration tests for the FastAPI endpoints.
"""
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="module")
def client():
    from api.main import app
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "models_loaded" in data


class TestBillBreakdown:
    def test_breakdown_default(self, client):
        resp = client.get("/bill-breakdown")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 12
        if data:
            assert "total_bill" in data[0]
            assert "components" in data[0]
            assert "usage_kwh" in data[0]

    def test_breakdown_custom_months(self, client):
        resp = client.get("/bill-breakdown?months=6")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 6


class TestTrends:
    def test_trends_returns_arrays(self, client):
        resp = client.get("/trends?months=24")
        assert resp.status_code == 200
        data = resp.json()
        assert "months" in data
        assert "total_bills" in data
        assert len(data["months"]) == len(data["total_bills"])


class TestForecastEndpoint:
    def test_forecast_default(self, client):
        resp = client.post("/forecast", json={"months_ahead": 6})
        assert resp.status_code == 200
        data = resp.json()
        assert "forecasts" in data
        assert len(data["forecasts"]) == 6

    def test_forecast_with_ci(self, client):
        resp = client.post("/forecast", json={"months_ahead": 3, "include_ci": True})
        assert resp.status_code == 200
        data = resp.json()
        for fc in data["forecasts"]:
            assert fc["lower"] is not None
            assert fc["upper"] is not None
            assert fc["lower"] <= fc["forecast"] <= fc["upper"]


class TestImpactEndpoint:
    def test_impact_analysis(self, client):
        resp = client.post("/impact", json={"top_n": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert "top_drivers" in data
        assert "base_value" in data
        assert len(data["top_drivers"]) <= 5


class TestBenchmarkEndpoint:
    def test_benchmark_nj(self, client):
        resp = client.post("/benchmark", json={"year": 2024, "compare_state": "NJ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["focus_state"]["state"] == "NJ"
        assert data["national_avg"] > 0
        assert len(data["states"]) > 0


class TestPlanSimulation:
    def test_simulation_runs(self, client):
        resp = client.post("/plan-simulation", json={
            "monthly_usage_kwh": 750,
            "n_simulations": 1000,
            "horizon_months": 12,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "comparison" in data
        assert "recommended" in data
        assert len(data["comparison"]) > 0
        for plan in data["comparison"]:
            assert plan["expected_annual_cost"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
