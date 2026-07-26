"""
tests/test_api_v1.py — Integration tests for Phase 1 /api/v1/bill endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_api_v1_bill_upload():
    response = client.post("/api/v1/bill/upload", data={"dev_mock": "true"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "task_id" in data
    assert "bill_id" in data
    assert "bill_hash" in data


def test_api_v1_bill_status():
    upload_res = client.post("/api/v1/bill/upload", data={"dev_mock": "true"}).json()
    task_id = upload_res["task_id"]

    response = client.get(f"/api/v1/bill/status?task_id={task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == task_id
    assert data["progress_pct"] == 100


def test_api_v1_bill_analytics():
    response = client.get("/api/v1/bill/analytics/bill-test-123")
    assert response.status_code == 200
    data = response.json()
    assert "component_breakdown" in data
    assert "tariff_calculations" in data
    assert "analytics_version" in data
    assert data["analytics_version"] == "1.0.0"


def test_api_v1_bill_recalculate():
    payload = {
        "rate_overrides": {"bgs_rate": 0.12},
        "usage_multiplier": 1.10,
    }
    response = client.post("/api/v1/bill/recalculate?bill_id=bill-test-123", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "component_breakdown" in data
    assert data["tariff_calculations"]["bgs_rate"] == 0.12
