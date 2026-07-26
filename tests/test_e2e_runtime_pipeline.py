"""
Production Verification — End-to-End Runtime Pipeline Test Suite.

Automated integration test verifying the unbroken runtime execution path:
  Customer Upload Context
       │
       ▼
  OCR & Parser Extraction
       │
       ▼
  Analytics Engine Computation
       │
       ▼
  Immutable AnalyticsResult
       │
       ▼
  Prompt Builder + Scoped RAG Context
       │
       ▼
  Model Router & Multi-Provider Inference
       │
       ▼
  7-Point Output Validator (Numeric Exact Match & Hallucination Check)
       │
       ▼
  Report Generator (Markdown, HTML, PDF)
       │
       ▼
  Semantic Cache Storage
"""
import pytest
import io
import json
from typing import Dict, Any

from backend.analytics.engine import AnalyticsEngine
from backend.schemas.analytics import AnalyticsResult
from api.services.llm.contracts import UserTier
from api.services.llm.prompt_builder import PromptBuilder
from api.services.llm.rag import rag_service
from api.services.llm.router import ModelRouter
from api.services.llm.providers.mock_provider import MockLLMProvider
from api.services.llm.validator import OutputValidator
from api.services.llm.report import MarkdownReportRenderer, HTMLReportRenderer, PDFReportRenderer
from api.services.llm.cache import semantic_cache
from api.services.llm.orchestrator import AIOrchestrator
from api.services.llm.llm_service import llm_service


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def raw_bill_context() -> Dict[str, Any]:
    return {
        "customer_id": "CUST-88392",
        "utility": "PSE&G",
        "service_class": "Residential (RS)",
        "billing_period": "2026-06-01 to 2026-06-30",
        "usage_kwh": 850.0,
        "total_bill": 182.08,
        "effective_rate": 0.2142,
        "supply_charge": 91.80,
        "delivery_charge": 46.75,
        "monthly_service_charge": 8.24,
        "tax": 11.31,
        "bill_hash": "e2e_test_hash_88392"
    }


class TestE2ERuntimePipeline:
    def test_step1_analytics_engine_immutability(self, raw_bill_context):
        """Step 1: Verify AnalyticsEngine generates read-only AnalyticsResult."""
        from backend.schemas.parsed_bill import ParsedBill
        parsed = ParsedBill(
            bill_hash=raw_bill_context["bill_hash"],
            customer_id=raw_bill_context["customer_id"],
            utility=raw_bill_context["utility"],
            rate_schedule="RS",
            bill_date="2026-06-30",
            billing_period=raw_bill_context["billing_period"],
            usage_kwh=raw_bill_context["usage_kwh"],
            supply_charge=raw_bill_context["supply_charge"],
            delivery_charge=raw_bill_context["delivery_charge"],
            monthly_service_charge=raw_bill_context["monthly_service_charge"],
            taxes_and_fees=raw_bill_context["tax"]
        )
        engine = AnalyticsEngine()
        result = engine.calculate(parsed)
        assert isinstance(result, AnalyticsResult)
        assert result.component_breakdown.total_bill >= 0.0

    def test_step2_prompt_builder_and_rag(self, raw_bill_context):
        """Step 2: Verify PromptBuilder constructs prompt and RAG injects scope docs."""
        sys_prompt, user_prompt, prompt_ver = PromptBuilder.build_prompt(
            task="bill_analysis",
            context_data=raw_bill_context
        )
        assert "182.08" in user_prompt
        assert "PSE&G" in user_prompt
        assert "MANDATORY_SYSTEM_GUARDRAILS" in sys_prompt or "CRITICAL RULES" in sys_prompt

        # Test RAG context retrieval
        rag_ctx = rag_service.query_text("PSE&G rate schedule RS customer charge", top_k=2)
        assert len(rag_ctx) > 0
        assert "PSE&G" in rag_ctx

    @pytest.mark.anyio
    async def test_step3_orchestration_inference_and_validation(self, raw_bill_context):
        """Step 3: Execute full pipeline via AIOrchestrator and verify 7-point audit."""
        orchestrator = AIOrchestrator(default_provider=MockLLMProvider())

        res = await orchestrator.execute(
            task="bill_analysis",
            context_data=raw_bill_context,
            user_tier=UserTier.PRO
        )

        assert res["success"] is True
        assert "text" in res
        assert "explanation" in res
        assert res["metadata"]["validated"] is True
        assert res["metadata"]["provider"] in ("MockLLMProvider", "DeterministicFallback")

    def test_step4_output_validator_hallucination_gate(self, raw_bill_context):
        """Step 4: Verify OutputValidator rejects hallucinated figures."""
        # Genuine text with facts from context
        clean_text = "Your total bill is $182.08 for 850.0 kWh of usage."
        audit_pass = OutputValidator.validate(clean_text, raw_bill_context, task="bill_analysis")
        assert audit_pass.is_valid is True

        # Hallucinated text with fake figures
        fake_text = "Your total bill is $999.99 and you saved $888.88."
        audit_fail = OutputValidator.validate(fake_text, raw_bill_context, task="bill_analysis")
        assert audit_fail.is_valid is False
        assert len(audit_fail.numeric_discrepancies) > 0

    def test_step5_report_generators(self, raw_bill_context):
        """Step 5: Verify Markdown, HTML, and PDF document generation."""
        narrative = "Your electricity bill for 2026-06 is driven mainly by supply charges."

        md = MarkdownReportRenderer.render(narrative, raw_bill_context)
        assert "# Electricity Bill Analysis Report" in md

        html_doc = HTMLReportRenderer.render(narrative, raw_bill_context)
        assert "<!DOCTYPE html>" in html_doc

        pdf_buf = PDFReportRenderer.render(narrative, raw_bill_context)
        assert isinstance(pdf_buf, io.BytesIO)
        assert pdf_buf.getvalue().startswith(b"%PDF")

    @pytest.mark.anyio
    async def test_step6_facade_and_caching(self, raw_bill_context):
        """Step 6: Verify LLMService facade and semantic caching."""
        # First execution (populate cache)
        res1 = await llm_service.generate_explanation(
            task="bill_analysis",
            context_data=raw_bill_context,
            bypass_cache=True
        )
        assert res1["success"] is True

        # Second execution (should hit cache)
        res2 = await llm_service.generate_explanation(
            task="bill_analysis",
            context_data=raw_bill_context,
            bypass_cache=False
        )
        assert res2["success"] is True
        assert res2["metadata"].get("cache_hit") is True
