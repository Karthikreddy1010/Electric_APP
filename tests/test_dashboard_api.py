import pytest
from fastapi.testclient import TestClient
from api.main import app
import numpy as np

client = TestClient(app)

def test_overview_schema():
    with TestClient(app) as client:
        response = client.get("/overview")
        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "breakdown" in data
        assert "trends" in data
        assert data["kpis"]["current_bill"] > 0

def test_forecast_horizon():
    with TestClient(app) as client:
        response = client.get("/forecast?horizon=12")
        assert response.status_code == 200
        data = response.json()
        assert len(data["forecasts"]) == 12
        for f in data["forecasts"]:
            assert f["forecast"] is not None

def test_simulator_math():
    with TestClient(app) as client:
        ov = client.get("/overview").json()
        base_bill = ov["kpis"]["current_bill"]
        
        payload = {
            "modifications": {"bgs_rate": 10},
            "kwh": ov["kpis"]["usage_kwh"]
        }
        response = client.post("/simulate", json=payload)
        assert response.status_code == 200
        res = response.json()
        assert res["new_bill"] != res["old_bill"]

def test_geo_ranking():
    with TestClient(app) as client:
        response = client.get("/geo")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_5_expensive"]) == 5
    assert len(data["top_5_cheapest"]) == 5
    # Check ranking order
    assert data["top_5_expensive"][0]["avg_bill"] >= data["top_5_expensive"][1]["avg_bill"]
