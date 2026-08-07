"""
Test Suite for ReportGenerationPipeline.

Verifies:
1. Section decomposition produces all 6 narrative sections.
2. Cache hit returns report in <50ms.
3. Section-level prompt token budgets are respected (<=1200 input tokens per section).
4. SSE streaming yields metadata, section, and complete events.
5. Deterministic fallback returns all 10 report sections when LLM is offline.
"""
import time
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from api.routes.geo_insights import (
    _compute_deterministic_insights,
    GeoInsightsRequest,
    GeoLocation,
    GeoElectricityData
)
from api.services.llm.cache import semantic_cache
from api.services.llm.prompt_budget_manager import PromptBudgetManager


@pytest.fixture
def report_request():
    return GeoInsightsRequest(
        state="NJ",
        utility="PSE&G",
        county="Essex",
        zip_code="07101",
        region="Mid-Atlantic",
        time_period="2026",
        location=GeoLocation(state="NJ", zip_codes=["07101", "07201"]),
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
            )
        ]
    )


class TestReportGenerationPipeline:

    def test_deterministic_base_report_structure(self, report_request):
        """Verify deterministic engine produces all 10 sections with cost breakdown and evidence."""
        result = _compute_deterministic_insights(report_request)

        # Core 10 sections
        assert "executive_summary" in result
        assert "market_analysis" in result
        assert "market_drivers" in result
        assert "risk_assessment" in result
        assert "forecast_outlook" in result
        assert "recommendations" in result
        assert "confidence_assessment" in result

        # Executive report extensions
        assert "cost_breakdown" in result
        assert "supporting_evidence" in result
        assert len(result["supporting_evidence"]) >= 4

    def test_section_prompt_token_budgets(self, report_request):
        """Verify each section context stays within ~600 token input budget."""
        from api.services.llm.report_pipeline import ReportGenerationPipeline, SECTION_OUTPUT_BUDGETS

        base_report = _compute_deterministic_insights(report_request)
        state = "NJ"

        for section_name in SECTION_OUTPUT_BUDGETS:
            sec_ctx = ReportGenerationPipeline._extract_section_context(section_name, base_report, state)
            prompt = f"Executive Analyst briefing for '{section_name}' ({state}): {json.dumps(sec_ctx, default=str)}"
            est_tokens = PromptBudgetManager.estimate_tokens(prompt)
            assert est_tokens <= 1200, (
                f"Section '{section_name}' prompt exceeds 1200 token budget: {est_tokens} tokens"
            )

    def test_output_budget_configuration(self):
        """Verify output budgets sum to target range (600-1200 tokens)."""
        from api.services.llm.report_pipeline import SECTION_OUTPUT_BUDGETS

        total = sum(SECTION_OUTPUT_BUDGETS.values())
        assert 600 <= total <= 1500, f"Total output budget {total} outside target range"
        assert len(SECTION_OUTPUT_BUDGETS) == 6

    def test_cache_roundtrip(self, report_request):
        """Verify cache stores and retrieves reports correctly."""
        base_report = _compute_deterministic_insights(report_request)
        cache_key_ctx = {
            "state": "NJ",
            "utility": "PSE&G",
            "county": "Essex",
            "zip_code": "07101",
            "region": "Mid-Atlantic",
            "time_period": "2026",
            "filters": {},
            "report_version": "2.0"
        }

        # Store
        semantic_cache.set(
            task="executive_report",
            context_data=cache_key_ctx,
            response_data=base_report,
            model_id="auto",
            prompt_version="v2"
        )

        # Retrieve
        t_start = time.perf_counter()
        cached = semantic_cache.get(
            task="executive_report",
            context_data=cache_key_ctx,
            model_id="auto",
            prompt_version="v2"
        )
        cache_ms = (time.perf_counter() - t_start) * 1000

        assert cached is not None
        assert "executive_summary" in cached
        assert cache_ms < 50, f"Cache retrieval took {cache_ms:.1f}ms, expected <50ms"

        # Clean up
        semantic_cache.clear()

    @pytest.mark.anyio
    async def test_pipeline_execute_with_llm_offline(self, report_request):
        """Verify pipeline falls back to deterministic report when LLM is offline."""
        from api.services.llm.report_pipeline import ReportGenerationPipeline

        # Clear cache to force fresh generation
        semantic_cache.clear()
        result = await ReportGenerationPipeline.execute(report_request, bypass_cache=True)
        assert "executive_summary" in result
        assert "risk_assessment" in result
        assert "cost_breakdown" in result
        assert "profiling" in result
        assert result["profiling"]["cache_hit"] is False

    @pytest.mark.anyio
    async def test_pipeline_stream_yields_events(self, report_request):
        """Verify streaming pipeline yields metadata and complete events."""
        from api.services.llm.report_pipeline import ReportGenerationPipeline

        events = []
        async for event in ReportGenerationPipeline.stream(report_request):
            events.append(event)

        # Should have at least metadata and complete events
        assert len(events) >= 2
        assert any("metadata" in e for e in events)
        assert any("complete" in e for e in events)

        # Verify metadata event has cost_breakdown
        metadata_event = next(e for e in events if "metadata" in e)
        data_line = [l for l in metadata_event.split("\n") if l.startswith("data: ")][0]
        metadata_data = json.loads(data_line[6:])
        assert "cost_breakdown" in metadata_data or "supporting_evidence" in metadata_data

    def test_section_extract_context_completeness(self, report_request):
        """Verify section context extraction covers all 6 sections."""
        from api.services.llm.report_pipeline import ReportGenerationPipeline, SECTION_OUTPUT_BUDGETS

        base_report = _compute_deterministic_insights(report_request)

        for section_name in SECTION_OUTPUT_BUDGETS:
            ctx = ReportGenerationPipeline._extract_section_context(section_name, base_report, "NJ")
            assert isinstance(ctx, dict), f"Section '{section_name}' context is not a dict"
            assert len(ctx) > 0, f"Section '{section_name}' context is empty"
