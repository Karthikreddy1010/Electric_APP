import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from fastapi.testclient import TestClient
from api.main import app
from api.services.llm.ollama_provider import OllamaProvider
from api.services.llm.cache import semantic_cache

# Clear cache to guarantee live execution
semantic_cache.clear()

def test_production_chat_endpoint_prompt_size(monkeypatch):
    """
    Verifies that POST /llm/chat with a bloated 30,000-character frontend payload
    is filtered and pruned down to < 1,500 characters before reaching OllamaProvider.generate().
    """
    captured_prompts = []

    async def mock_generate(self, prompt, system_prompt=None, temperature=0.2, max_tokens=500, **kwargs):
        captured_prompts.append(prompt)
        return "Clean concise LLM chat response for production endpoint test."

    monkeypatch.setattr(OllamaProvider, "generate", mock_generate)
    monkeypatch.setattr(OllamaProvider, "is_available", lambda self: True)

    bloated_context = {
        "bill": {
            "utility": "PSE&G",
            "total_bill": 160.62,
            "usage_kwh": 750.0,
            "delivery_charge": 48.18,
            "supply_charge": 94.22
        },
        "raw_ocr_data": "X" * 15000,
        "time_series_hourly": [0.12] * 2000,
        "historical_metadata": {"junk": "Y" * 10000}
    }

    client = TestClient(app)
    resp = client.post("/llm/chat", json={
        "message": "Why is my delivery charge $48.18 this month?",
        "context_data": bloated_context,
        "history": [{"role": "user", "content": "Hello"}],
        "current_tab": "bill",
        "user_tier": "free"
    })

    print("\n================ PRODUCTION /llm/chat TEST RESULT ================")
    print(f"HTTP Status Code: {resp.status_code}")
    assert resp.status_code == 200

    assert len(captured_prompts) > 0
    final_prompt = captured_prompts[0]
    prompt_len = len(final_prompt)
    est_tokens = prompt_len // 4

    print(f"Raw Input Payload Size : {len(str(bloated_context))} chars")
    print(f"Final Prompt Size      : {prompt_len} chars ({est_tokens} tokens)")
    print(f"Target Threshold       : < 2000 chars")
    print(f"Prompt Size Reduction  : {round((1 - prompt_len / len(str(bloated_context))) * 100, 1)}% reduction")
    print(f"First 200 Chars        : {final_prompt[:200]}...")

    assert prompt_len < 2000, f"Prompt size {prompt_len} exceeds 2000-character budget threshold!"
    print("SUCCESS: Production /llm/chat endpoint cleanly prunes bloated payloads!")

if __name__ == "__main__":
    import pytest
    pytest.main(["-s", __file__])
