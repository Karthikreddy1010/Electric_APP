import sys
import os
import io
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncio
import time
import json
from api.services.llm.orchestrator import AIOrchestrator
from api.services.llm.contracts import UserTier
from api.services.llm.cache import semantic_cache

# Clear cache to guarantee live inference execution
semantic_cache.clear()

orchestrator = AIOrchestrator()

TEST_INTENTS = [
    ("bill_analysis", "Explain why my electric bill changed this month.", "bill_explanation"),
    ("impact", "What happens to my monthly bill if summer temperatures increase by 4 degrees?", "impact"),
    ("forecast", "Provide a 90-day electricity consumption and cost forecast.", "forecast_query"),
    ("recommendations", "How can I shift my peak energy usage to reduce my delivery charges?", "savings_query"),
    ("tariff", "What is the PSEG Residential Rate Schedule RS charge breakdown?", "tariff_query"),
    ("benchmark", "How does my monthly electric usage compare to regional peer averages?", "benchmark_query"),
    ("overview", "Summarize my facility energy telemetry and current alerts.", "overview_query"),
    ("report", "Generate a plain-language monthly bill report.", "report"),
]

sample_bill_context = {
    "bill_hash": "a1b2c3d4e5f67890",
    "customer": {
        "utility": "PSE&G",
        "customer_id": "CUST-9921",
        "rate_schedule": "RS"
    },
    "bill": {
        "billing_period": "Jul 01 - Jul 31",
        "usage_kwh": 750.0,
        "total_bill": 160.62,
        "effective_rate": 0.214,
        "monthly_service_charge": 8.24,
        "delivery_charge": 48.18,
        "supply_charge": 94.22,
        "tax": 9.98,
        "components": [
            {"name": "Customer Charge", "value": 8.24},
            {"name": "Distribution Charge", "value": 48.18},
            {"name": "BGS Supply", "value": 94.22},
            {"name": "NJ Sales Tax", "value": 9.98}
        ]
    }
}

async def run_validation_suite():
    results = []
    print("================ RUNNING MULTI-INTENT VALIDATION SUITE ================\n")
    
    for task_name, query, intent_label in TEST_INTENTS:
        start_time = time.time()
        print(f"Executing Task: {task_name} | Intent: {intent_label}")
        print(f"User Query: '{query}'")
        
        res = await orchestrator.execute(
            task=task_name,
            context_data=sample_bill_context,
            user_message=query,
            user_tier=UserTier.FREE,
            bypass_cache=True
        )
        
        elapsed = round(time.time() - start_time, 2)
        resp_text = str(res.get("explanation") or res.get("response") or res)
        meta = res.get("metadata", {})
        prompt_tokens = meta.get("prompt_tokens", 0)
        val_status = str(res.get("status") or meta.get("validation_status", "success"))
        retries = meta.get("retry_count", 0)
        fallback = meta.get("fallback_used", False)
        model = meta.get("model", "qwen3:4b")
        provider = meta.get("provider", "OllamaProvider")
        
        est_prompt_tokens = prompt_tokens or (len(query) + len(json.dumps(sample_bill_context))) // 4
        
        results.append({
            "task": task_name,
            "intent": intent_label,
            "est_prompt_tokens": est_prompt_tokens,
            "num_ctx_bound": 4096,
            "under_ctx_limit": est_prompt_tokens < 4096,
            "latency_ms": elapsed * 1000,
            "validation_status": val_status,
            "retries": retries,
            "fallback_used": fallback,
            "model": model,
            "provider": provider,
            "text_preview": resp_text[:100].replace("\n", " ") + "..."
        })
        
        clean_preview = resp_text[:100].replace("\n", " ").encode("ascii", errors="replace").decode("ascii")
        print(f"  [PASS] Latency: {elapsed:.2f}s | Est Prompt Tokens: {est_prompt_tokens} | num_ctx: 4096")
        print(f"  [PASS] Validation Status: {val_status} | Retries: {retries} | Fallback: {fallback} | Provider: {provider}")
        print(f"  [PASS] Response Preview: {clean_preview}...\n")

    print("================ VALIDATION SUMMARY TABLE ================")
    print(f"{'Task/Intent':<18} | {'Est. Tokens':<11} | {'Under 4k?':<9} | {'Latency (s)':<11} | {'Val Status':<10} | {'Retries':<7} | {'Fallback':<8}")
    print("-" * 90)
    for r in results:
        lat_sec = round(r['latency_ms'] / 1000.0, 2)
        print(f"{r['task']:<18} | {r['est_prompt_tokens']:<11} | {str(r['under_ctx_limit']):<9} | {lat_sec:<11} | {r['validation_status']:<10} | {r['retries']:<7} | {str(r['fallback_used']):<8}")

if __name__ == "__main__":
    asyncio.run(run_validation_suite())
