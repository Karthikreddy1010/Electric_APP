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
        resp = client.get("/forecast?horizon=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "forecast" in data
        assert "metrics" in data

    def test_forecast_with_ci(self, client):
        resp = client.get("/forecast?horizon=7&include_ci=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "forecast" in data
        for fc in data["forecast"]:
            assert fc["lower"] is not None
            assert fc["upper"] is not None
            assert fc["lower"] <= fc["value"] <= fc["upper"]


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


class TestImpactV2AndAI:
    def test_what_if_v2_with_overrides(self, client):
        payload = {
            "changes": {"bgs_rate": 10.0, "distribution_rate": -5.0},
            "kwh": 800,
            "base_rates": {
                "customer_charge": 8.24,
                "bgs_rate": 0.105,
                "distribution_rate": 0.045,
                "transmission_rate": 0.015,
                "sbc_rate": 0.007,
                "transition_rate": 0.002,
                "nug_rate": 0.001,
                "rider_rate": 0.003
            },
            "base_costs": {
                "customer_charge": 8.24,
                "bgs_cost": 84.0,
                "distribution_cost": 36.0,
                "transmission_cost": 12.0,
                "sbc_cost": 5.6,
                "transition_cost": 1.6,
                "nug_cost": 0.8,
                "rider_cost": 2.4,
                "sales_tax": 9.98,
                "total_bill": 160.62
            }
        }
        resp = client.post("/impact/what-if-v2", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "simulated_bill" in data
        assert "contributions" in data
        assert "distribution_rate" in data["contributions"]
        
        contribs = data["contributions"]
        total_sum = sum(c["simulated_cost"] for c in contribs.values())
        assert abs(total_sum - data["simulated_bill"]) < 0.05

    def test_explain_endpoint(self, client):
        uploaded_bill = {"usage_kwh": 800, "total_bill": 160.62}
        simulation_results = {
            "base_bill": 160.62,
            "simulated_bill": 172.50,
            "total_impact": 11.88,
            "usage_change_kwh": 0.0,
            "learned_elasticity": -0.20,
            "decomposition": {
                "direct_price_effect": 11.0,
                "indirect_behavioral_effect": 0.0,
                "weather_effect": 0.0,
                "interaction_effect": 0.0
            },
            "contributions": {
                "customer_charge": {"name": "Customer Charge", "simulated_cost": 8.24, "difference": 0.0, "type": "fixed", "controllable": "No"},
                "bgs_rate": {"name": "BGS Supply", "simulated_cost": 92.40, "difference": 8.40, "type": "variable", "controllable": "No"},
                "distribution_rate": {"name": "Distribution", "simulated_cost": 36.0, "difference": 0.0, "type": "variable", "controllable": "Yes"}
            }
        }
        payload = {
            "uploaded_bill": uploaded_bill,
            "simulation_results": simulation_results,
            "scenario_inputs": {"changes": {"bgs_rate": 10.0}}
        }
        resp = client.post("/impact/explain", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "explanation" in data

    def test_chat_endpoint(self, client):
        uploaded_bill = {"usage_kwh": 800, "total_bill": 160.62}
        simulation_results = {
            "base_bill": 160.62,
            "simulated_bill": 172.50,
            "total_impact": 11.88,
            "usage_change_kwh": 0.0,
            "learned_elasticity": -0.20,
            "decomposition": {
                "direct_price_effect": 11.0,
                "indirect_behavioral_effect": 0.0,
                "weather_effect": 0.0,
                "interaction_effect": 0.0
            },
            "contributions": {
                "customer_charge": {"name": "Customer Charge", "simulated_cost": 8.24, "difference": 0.0, "type": "fixed", "controllable": "No"},
                "bgs_rate": {"name": "BGS Supply", "simulated_cost": 92.40, "difference": 8.40, "type": "variable", "controllable": "No"},
                "distribution_rate": {"name": "Distribution", "simulated_cost": 36.0, "difference": 0.0, "type": "variable", "controllable": "Yes"}
            }
        }
        payload = {
            "message": "Why did BGS Supply increase?",
            "history": [],
            "uploaded_bill": uploaded_bill,
            "simulation_results": simulation_results
        }
        resp = client.post("/impact/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "answer" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
