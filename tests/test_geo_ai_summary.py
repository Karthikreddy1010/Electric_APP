"""
Automated Test Suite for Regional Executive AI Intelligence Overhaul.
Verifies:
1. POST /geo/generate-insights returns valid 10-section executive report.
2. Deterministic calculation engine populates all 10 sections accurately.
3. Fallback path functions with zero errors when LLM is offline.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes.geo_insights import _compute_deterministic_insights, GeoInsightsRequest, GeoLocation, GeoElectricityData


@pytest.fixture
def sample_geo_request():
    return GeoInsightsRequest(
        location=GeoLocation(state="NJ", zip_codes=["07101", "07201", "07301"]),
        electricity_data=[
            GeoElectricityData(
                zip_code="07101",
                state="NJ",
                month=6,
                year=2026,
                avg_price=0.1852,
                consumption_kwh=750.0,
                peak_demand=3.2,
                renewable_ratio=0.15
            ),
            GeoElectricityData(
                zip_code="07201",
                state="NJ",
                month=6,
                year=2026,
                avg_price=0.1920,
                consumption_kwh=820.0,
                peak_demand=3.8,
                renewable_ratio=0.12
            )
        ]
    )


class TestGeoAISummary:
    def test_deterministic_10_section_calculation(self, sample_geo_request):
        """Verifies _compute_deterministic_insights builds all 10 sections programmatically."""
        res = _compute_deterministic_insights(sample_geo_request)

        assert "executive_summary" in res
        assert "market_analysis" in res
        assert "market_drivers" in res
        assert "risk_assessment" in res
        assert "forecast_outlook" in res
        assert "geographic_intelligence" in res
        assert "economic_impact" in res
        assert "recommendations" in res
        assert "confidence_assessment" in res
        assert "data_limitations" in res

        # Check section 1
        sec1 = res["executive_summary"]
        assert "overall_health" in sec1
        assert "primary_finding" in sec1
        assert "confidence_level" in sec1

        # Check section 4 risk categories
        sec4 = res["risk_assessment"]
        assert "risks" in sec4
        assert len(sec4["risks"]) == 6
        for risk in sec4["risks"]:
            assert risk["severity"] in ["Low", "Medium", "High"]

        # Check section 5 forecast horizons
        sec5 = res["forecast_outlook"]
        assert "horizons" in sec5
        assert len(sec5["horizons"]) == 3

    def test_api_generate_insights_endpoint(self, sample_geo_request):
        """Verifies POST /geo/generate-insights returns HTTP 200 with 10 structured sections."""
        with TestClient(app) as client:
            resp = client.post("/geo/generate-insights", json=sample_geo_request.model_dump())
            assert resp.status_code == 200
            
            body = resp.json().get("data", {}) or resp.json()
            assert "executive_summary" in body
            assert "risk_assessment" in body
            assert "forecast_outlook" in body
            assert "confidence_assessment" in body

    def test_offline_fallback_safety(self, sample_geo_request, monkeypatch):
        """Verifies endpoint handles LLM exception and falls back to 10-section report safely."""
        from api.services.llm.llm_service import llm_service

        def mock_generate_explanation(*args, **kwargs):
            raise RuntimeError("Ollama server down")

        monkeypatch.setattr(llm_service, "generate_explanation", mock_generate_explanation)

        with TestClient(app) as client:
            resp = client.post("/geo/generate-insights", json=sample_geo_request.model_dump())
            assert resp.status_code == 200

            body = resp.json().get("data", {}) or resp.json()
            assert "executive_summary" in body
            assert "recommendations" in body
            assert body["confidence_assessment"]["overall_confidence_score"] > 0

    def test_contextual_request_with_supporting_evidence(self):
        """Verifies request with active regional context returns cost breakdown and evidence provenance."""
        req = GeoInsightsRequest(
            state="NJ",
            utility="PSE&G",
            county="Essex",
            zip_code="07101",
            region="Mid-Atlantic",
            time_period="2026"
        )
        res = _compute_deterministic_insights(req)
        assert "executive_summary" in res
        assert "cost_breakdown" in res
        assert "supporting_evidence" in res
        assert len(res["supporting_evidence"]) >= 4
        assert res["cost_breakdown"]["generation_pct"] > 0

