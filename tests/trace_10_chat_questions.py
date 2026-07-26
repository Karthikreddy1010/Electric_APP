"""
Phase 2 / Phase 3 Chat Execution Path Tracing & Verification Script.

Executes 10 distinct natural-language questions through the AI Pipeline and logs:
  1. User Question
  2. Generated Prompt
  3. LLM Response
  4. Final Response
  5. Cache Status
"""
import sys
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.services.llm.llm_service import llm_service
from api.services.llm.prompt_builder import PromptBuilder
from api.services.llm.contracts import UserTier
from api.services.llm.cache import semantic_cache
from api.services.llm.providers.mock_provider import MockLLMProvider

SAMPLE_BILL = {
    "customer_id": "CUST-4410",
    "utility": "Jersey Central Power & Light (JCP&L)",
    "billing_period": "Jul 2026",
    "bill_date": "2026-07-25",
    "usage_kwh": 920.0,
    "monthly_service_charge": 12.50,
    "delivery_charge": 54.30,
    "supply_charge": 110.40,
    "tax": 12.80,
    "total_bill": 190.00,
    "effective_rate": 0.2065
}

TEN_TEST_QUESTIONS = [
    "Explain my customer charge.",
    "Why is my bill higher?",
    "Compare this month with last month.",
    "Explain taxes.",
    "Explain transmission charges.",
    "Summarize my bill.",
    "What is demand charge?",
    "How can I reduce my bill?",
    "What happens if I reduce usage by 15%?",
    "What is my biggest cost?"
]


async def run_chat_trace():
    print("=" * 80)
    print(" ELECTRICAI CONVERSATIONAL CHAT PIPELINE EXECUTION TRACE")
    print("=" * 80)

    # Use MockLLMProvider for deterministic local verification
    llm_service.orchestrator._default_provider = MockLLMProvider()

    for idx, question in enumerate(TEN_TEST_QUESTIONS, 1):
        print(f"\n--- [QUESTION {idx}/10] --------------------------------------------------")
        print(f"USER QUESTION : {question}")

        # 1. Prompt Builder Inspection
        context_data = {"uploadedBill": SAMPLE_BILL}
        sys_prompt, user_prompt, ver = PromptBuilder.build_prompt(
            task="chat",
            context_data=context_data,
            user_message=question
        )
        print(f"\nPROMPT VERSION : {ver}")
        print(f"GENERATED PROMPT (User Prompt Snippet):\n{user_prompt[:250]}...")

        # 2. Cache Key Inspection
        cache_key = semantic_cache._generate_key("chat", context_data, "auto", ver, question)
        cached_before = semantic_cache.get("chat", context_data, "auto", ver, question)
        cache_hit_str = "HIT" if cached_before else "MISS"
        print(f"CACHE KEY      : {cache_key[:24]}... (Status: {cache_hit_str})")

        # 3. Pipeline Execution
        res = await llm_service.generate_explanation(
            task="chat",
            context_data=context_data,
            user_message=question,
            user_tier=UserTier.FREE
        )

        llm_resp = res.get("text") or res.get("answer") or ""
        final_resp = res.get("answer") or res.get("text") or ""

        print(f"LLM RESPONSE   : {llm_resp}")
        print(f"FINAL RESPONSE : {final_resp}")
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(run_chat_trace())
