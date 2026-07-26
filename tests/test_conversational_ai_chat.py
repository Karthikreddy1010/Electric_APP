"""
Phase 2 / Phase 3 Conversational AI Chat Test Suite.

Verifies that the AI Copilot Chat Endpoint handles ANY natural-language bill question
using the full AI Orchestration Pipeline:
  User Question → Context/History → PromptBuilder → RAG → Router → LLM/Fallback → Validator → Answer
"""
import pytest
from api.services.llm.llm_service import llm_service
from api.services.llm.contracts import UserTier
from api.services.llm.deterministic_fallback import DeterministicFallback

SAMPLE_BILL_CONTEXT = {
    "uploadedBill": {
        "customer_id": "CUST-9921",
        "utility": "PSE&G",
        "billing_period": "Jun 2026",
        "bill_date": "2026-06-30",
        "usage_kwh": 850.0,
        "monthly_service_charge": 8.24,
        "delivery_charge": 46.75,
        "supply_charge": 91.80,
        "tax": 11.31,
        "total_bill": 158.10,
        "effective_rate": 0.1860
    }
}

TEST_QUESTIONS = [
    "Why is my bill higher this month?",
    "Explain my bill.",
    "Why are delivery charges increasing?",
    "What does customer charge mean?",
    "Explain transmission charges.",
    "Why did my usage increase?",
    "Compare this bill with last month.",
    "Explain taxes.",
    "Which bill component increased the most?",
    "How can I reduce my bill?",
    "Explain my bill like I'm five.",
    "Summarize my bill.",
    "What happens if I reduce usage by 15%?",
    "What uses the most electricity?",
    "Explain weather impact.",
    "Explain my tariff.",
    "Why is this bill different from previous months?",
    "Give me recommendations.",
    "Who won the soccer world cup in 1970?",  # Unrelated out-of-scope question
    "Tell me a joke about cats."              # Unrelated out-of-scope question
]


class TestConversationalAIChat:

    @pytest.mark.anyio
    async def test_20_natural_language_chat_questions(self):
        """Execute 20 distinct natural language questions through the backend AI Service."""
        from api.services.llm.providers.mock_provider import MockLLMProvider
        llm_service.orchestrator._default_provider = MockLLMProvider()

        try:
            for idx, question in enumerate(TEST_QUESTIONS, 1):
                res = await llm_service.generate_explanation(
                    task="chat",
                    context_data=SAMPLE_BILL_CONTEXT,
                    user_message=question,
                    user_tier=UserTier.FREE
                )

                assert res["success"] is True
                answer = res.get("answer") or res.get("text") or res.get("explanation") or ""
                assert len(answer) > 10, f"Question {idx} ('{question}') produced empty or invalid response"

                if "world cup" in question.lower() or "cats" in question.lower():
                    assert "specialized" in answer.lower() or "electricity" in answer.lower(), \
                        f"Out-of-scope question {idx} ('{question}') was not politely restricted"
        finally:
            llm_service.orchestrator._default_provider = None

    def test_deterministic_fallback_chat_nlu(self):
        """Verify DeterministicFallback.generate_chat_fallback handles all 20 questions."""
        for idx, question in enumerate(TEST_QUESTIONS, 1):
            ans = DeterministicFallback.generate_chat_fallback(SAMPLE_BILL_CONTEXT, question)
            assert isinstance(ans, str)
            assert len(ans) > 10
