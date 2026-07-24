"""
Integration tests for ElectricAI Dataset Integration Roadmap.

Tests all services and endpoints added for:
  - PJM Day-Ahead Wholesale Market & Congestion
  - US BLS CPI Inflation Analytics
  - EIA-861 Operational Benchmarks & Incentive Programs
  - Community & Municipal Energy Analytics
  - Utility Reliability Indices (SAIDI / SAIFI / CAIDI)
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.pjm_service import pjm_service
from api.services.inflation_service import inflation_service
from api.services.eia861_analytics_service import eia861_analytics_service
from api.services.community_energy_service import community_energy_service
from api.services.reliability_service import reliability_service

client = TestClient(app)


# ── 1. PJM Wholesale Market Service & Router ─────────────────────────────────

def test_pjm_service_wholesale_exposure():
    result = pjm_service.compute_wholesale_exposure(usage_kwh=750, zone="PSEG", days=30)
    assert "usage_kwh" in result
    assert result["usage_kwh"] == 750
    assert "zone" in result
    assert result["zone"] == "PSEG"


def test_pjm_service_load_shifting():
    result = pjm_service.compute_load_shifting_savings(usage_kwh=750, shift_pct=0.15, zone="PSEG")
    assert "monthly_savings" in result
    assert "annual_savings" in result


def test_pjm_api_endpoints():
    r1 = client.get("/pjm/kpis?zone=PSEG")
    assert r1.status_code == 200

    r2 = client.get("/pjm/daily-analytics?zone=PSEG&days=7")
    assert r2.status_code == 200
    assert "data" in r2.json()

    r3 = client.get("/pjm/wholesale-exposure?usage_kwh=750&zone=PSEG")
    assert r3.status_code == 200

    r4 = client.get("/pjm/load-shifting?usage_kwh=750&shift_pct=0.15&zone=PSEG")
    assert r4.status_code == 200


# ── 2. BLS CPI Inflation Service & Router ───────────────────────────────────

def test_inflation_service_deflator():
    deflator = inflation_service.get_deflator(2023, 6)
    assert isinstance(deflator, float)
    assert deflator > 0


def test_inflation_service_bill_adjustment():
    adj = inflation_service.adjust_bill_for_inflation(nominal_bill=100.0, bill_year=2020, bill_month=1)
    assert "nominal_bill" in adj
    assert adj["nominal_bill"] == 100.0
    assert "real_bill" in adj
    assert "deflator" in adj


def test_inflation_api_endpoints():
    r1 = client.get("/inflation/trend")
    assert r1.status_code == 200
    assert "data" in r1.json()

    r2 = client.get("/inflation/kpis")
    assert r2.status_code == 200

    r3 = client.post("/inflation/adjust-bill", json={"nominal_bill": 150.0, "bill_year": 2021, "bill_month": 5})
    assert r3.status_code == 200
    assert "real_bill" in r3.json()


# ── 3. EIA-861 Operational & Incentive Router ──────────────────────────────

def test_eia861_api_endpoints():
    r1 = client.get("/eia861/operational-benchmark?state=NJ")
    assert r1.status_code == 200
    assert "data" in r1.json()

    r2 = client.get("/eia861/incentives?state=NJ")
    assert r2.status_code == 200

    r3 = client.get("/eia861/tou-savings?usage_kwh=750&shift_pct=0.15")
    assert r3.status_code == 200
    assert "annual_savings" in r3.json()


# ── 4. Community Energy Router ────────────────────────────────────────────────

def test_community_energy_api_endpoints():
    r1 = client.get("/municipal/community-rankings?top_n=5")
    assert r1.status_code == 200
    assert "data" in r1.json()

    r2 = client.get("/municipal/sector-history?county=Essex")
    assert r2.status_code == 200

    r3 = client.get("/municipal/county-benchmarks")
    assert r3.status_code == 200


# ── 5. Utility Reliability Router ────────────────────────────────────────────

def test_reliability_api_endpoints():
    r1 = client.get("/municipal/reliability?state=NJ")
    assert r1.status_code == 200
    assert "data" in r1.json()

    r2 = client.get("/municipal/reliability/trend?state=NJ")
    assert r2.status_code == 200

    r3 = client.get("/municipal/reliability/compare?state=NJ")
    assert r3.status_code == 200

    r4 = client.get("/municipal/reliability/kpis?state=NJ")
    assert r4.status_code == 200
