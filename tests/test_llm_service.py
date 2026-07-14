"""
Integration and Unit Test Suite for Centralized LLM Service Architecture.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient

from api.main import app
from api.services.llm.base_provider import BaseLLMProvider
from api.services.llm.mock_provider import MockLLMProvider
from api.services.llm.ollama_provider import OllamaProvider
from api.services.llm.llm_service import LLMService, llm_service
from api.services.llm.context_builder import ContextBuilder
from api.services.llm.prompt_builder import PromptBuilder
from api.services.llm.response_validator import ResponseValidator
from api.services.llm.deterministic_fallback import DeterministicFallback
from api.services.llm.cache_manager import LLMCacheManager
from api.services.llm.metadata import LLMResponseMetadata

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def test_bill_data():
    return {
        "customer_id": "CUST-12345",
        "utility": "PSE&G",
        "billing_period": "2026-06-01 to 2026-06-30",
        "usage_kwh": 750.0,
        "total_bill": 160.62,
        "effective_rate": 0.2142,
        "monthly_service_charge": 8.24,
        "delivery_charge": 41.25,
        "supply_charge": 81.00,
        "tax": 9.98,
        "canonical_bill": {
            "components": [
                {"name": "Customer Charge", "value": 8.24, "pct": 5.1},
                {"name": "BGS Supply", "value": 81.00, "pct": 50.4}
            ]
        }
    }

@pytest.fixture
def test_sim_data():
    return {
        "base_bill": 160.62,
        "simulated_bill": 175.50,
        "total_impact": 14.88,
        "usage_change_kwh": 0.0,
        "learned_elasticity": -0.215,
        "contributions": {
            "bgs_rate": {"name": "BGS Supply", "base_cost": 81.0, "simulated_cost": 94.88, "difference": 13.88}
        },
        "decomposition": {
            "direct_price_effect": 13.88,
            "indirect_behavioral_effect": 0.0,
            "weather_effect": 1.00,
            "interaction_effect": 0.0
        },
        "distribution": {"mean": 175.50, "std": 5.5, "p5": 165.0, "p95": 186.0}
    }

class TestLLMProviders:
    def test_mock_provider_availability(self):
        provider = MockLLMProvider()
        assert provider.is_available() is True
        assert provider.model == "mock-model"

    @pytest.mark.anyio
    async def test_mock_provider_generation(self):
        provider = MockLLMProvider()
        res = await provider.generate("Test prompt")
        assert "validated mock response" in res

    def test_ollama_provider_init(self):
        provider = OllamaProvider(model="qwen3:8b", base_url="http://127.0.0.1:11434")
        assert provider.model == "qwen3:8b"
        assert provider.base_url == "http://127.0.0.1:11434"

class TestContextAndPromptBuilders:
    def test_context_schema_compliance(self, test_bill_data, test_sim_data):
        ctx = ContextBuilder.build_impact_context(
            uploaded_bill=test_bill_data,
            simulation_results=test_sim_data
        )
        assert ctx["task"] == "impact"
        assert ctx["bill"]["total_bill"] == 160.62
        assert ctx["simulation"]["simulated_bill"] == 175.50
        assert ctx["metadata"]["schema_version"] == "v1.0"

    def test_prompt_builder_guardrails(self, test_bill_data):
        ctx = ContextBuilder.build_bill_analysis_context(test_bill_data)
        sys_prompt, user_prompt, version = PromptBuilder.build_prompt("bill_analysis", ctx)
        
        assert version == "v1.0"
        assert "NEVER invent numbers" in sys_prompt
        assert "NEVER perform mathematical operations" in sys_prompt
        assert "PSE&G" in user_prompt
        assert "160.62" in user_prompt

class TestResponseValidator:
    def test_validation_success_matching_numbers(self, test_bill_data):
        ctx = ContextBuilder.build_bill_analysis_context(test_bill_data)
        text = "Your total bill is $160.62 for 750.0 kWh of usage. Supply charge is $81.00 and customer charge is $8.24."
        is_valid, errors = ResponseValidator.validate(text, ctx)
        assert is_valid is True
        assert len(errors) == 0

    def test_validation_failure_hallucinated_numbers(self, test_bill_data):
        ctx = ContextBuilder.build_bill_analysis_context(test_bill_data)
        # 999.99 and 4567.89 are hallucinated numbers not present in context
        text = "Your total bill is $999.99 for 4567.89 kWh. You saved $1234.56!"
        is_valid, errors = ResponseValidator.validate(text, ctx)
        assert is_valid is False
        assert len(errors) > 0

class TestDeterministicFallback:
    def test_fallback_generators(self, test_bill_data, test_sim_data):
        ctx = ContextBuilder.build_impact_context(test_bill_data, test_sim_data)
        text = DeterministicFallback.get_fallback("impact", ctx)
        assert "Executive Financial Summary" in text
        assert "$175.50" in text
        assert "$14.88" in text

class TestLLMServiceOrchestration:
    @pytest.mark.anyio
    async def test_llm_service_with_mock_provider(self, test_bill_data, test_sim_data):
        service = LLMService(provider=MockLLMProvider())
        ctx = ContextBuilder.build_impact_context(test_bill_data, test_sim_data)
        
        res = await service.generate_explanation(task="impact", context_data=ctx)
        assert res["success"] is True
        assert "text" in res
        assert "metadata" in res
        assert res["metadata"]["provider"] == "MockLLMProvider"

    def test_llm_cache_manager(self):
        cache = LLMCacheManager()
        ctx = {"task": "test", "val": 123}
        cache.set("test", ctx, "model1", "v1.0", {"success": True, "text": "cached"})
        
        hit = cache.get("test", ctx, "model1", "v1.0")
        assert hit is not None
        assert hit["text"] == "cached"

class TestLLMAPIRoutes:
    def test_llm_explain_endpoint(self, test_bill_data):
        with TestClient(app) as client:
            ctx = ContextBuilder.build_bill_analysis_context(test_bill_data)
            resp = client.post("/llm/explain", json={
                "task": "bill_analysis",
                "context_data": ctx
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "text" in body
            assert "metadata" in body

    def test_llm_chat_endpoint(self, test_bill_data):
        with TestClient(app) as client:
            ctx = ContextBuilder.build_bill_analysis_context(test_bill_data)
            resp = client.post("/llm/chat", json={
                "task": "chat",
                "message": "Why is BGS supply so high?",
                "context_data": ctx,
                "current_tab": "Bill Analysis"
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "answer" in body
