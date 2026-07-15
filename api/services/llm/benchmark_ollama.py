"""
Diagnostic benchmark script for Ollama performance, timing breakdown, and hardware bounds.
"""
import time
import httpx
import json
import psutil
import socket

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"

def get_system_resources():
    cpu_pct = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    return {
        "cpu_percent": cpu_pct,
        "ram_used_gb": round(ram.used / (1024**3), 2),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "ram_percent": ram.percent
    }

def test_ollama_tags():
    print("--- 1. Testing GET /api/tags ---")
    start = time.time()
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        dur = round((time.time() - start) * 1000, 2)
        print(f"Status: {resp.status_code} | Duration: {dur}ms")
        if resp.status_code == 200:
            models = [m.get("name") for m in resp.json().get("models", [])]
            print(f"Installed Models: {models}")
            return models
    except Exception as e:
        print(f"Error querying /api/tags: {e}")
    return []

def test_ollama_running_models():
    print("\n--- 2. Testing GET /api/ps (Currently Loaded Models) ---")
    start = time.time()
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=5.0)
        dur = round((time.time() - start) * 1000, 2)
        print(f"Status: {resp.status_code} | Duration: {dur}ms")
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            print(f"Currently Loaded Models in Memory: {models}")
            return models
    except Exception as e:
        print(f"Error querying /api/ps: {e}")
    return []

def benchmark_prompt(prompt: str, max_tokens: int = 50, keep_alive: str = "30m", label: str = "Benchmark"):
    print(f"\n--- 3. Running Benchmark: {label} (max_tokens={max_tokens}, keep_alive={keep_alive}) ---")
    resources_before = get_system_resources()
    print(f"Resources Before: {resources_before}")
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {
            "temperature": 0.2,
            "num_predict": max_tokens
        }
    }
    
    start_time = time.time()
    try:
        resp = httpx.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120.0)
        total_dur = round(time.time() - start_time, 3)
        resources_after = get_system_resources()
        
        print(f"HTTP Status: {resp.status_code} | Total Wall Time: {total_dur}s")
        print(f"Resources After: {resources_after}")
        
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("response", "").strip()
            total_duration_ns = data.get("total_duration", 0)
            load_duration_ns = data.get("load_duration", 0)
            prompt_eval_ns = data.get("prompt_eval_duration", 0)
            eval_ns = data.get("eval_duration", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)
            
            print(f"Response Preview: {response_text[:150]}...")
            print(f"Timing Breakdown:")
            print(f"  - Model Load Time  : {load_duration_ns / 1e9:.3f}s")
            print(f"  - Prompt Eval Time : {prompt_eval_ns / 1e9:.3f}s ({prompt_eval_count} tokens)")
            print(f"  - Generation Time  : {eval_ns / 1e9:.3f}s ({eval_count} tokens)")
            print(f"  - Total Ollama Time: {total_duration_ns / 1e9:.3f}s")
            
            tok_per_sec = (eval_count / (eval_ns / 1e9)) if eval_ns > 0 else 0
            print(f"  - Speed            : {tok_per_sec:.2f} tokens/sec")
        else:
            print(f"Ollama returned error: {resp.text}")
    except Exception as e:
        print(f"Benchmark call failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("================ OLLAMA DIAGNOSTIC BENCHMARK ================")
    models = test_ollama_tags()
    test_ollama_running_models()
    
    # 1. Warmup / Minimal Prompt Test
    benchmark_prompt("Reply with OK.", max_tokens=10, keep_alive="30m", label="Minimal Benchmark (Warmup)")
    
    # 2. Check loaded models after warmup
    test_ollama_running_models()
    
    # 3. Full Explanation Prompt Test (Warm model)
    test_explanation_prompt = (
        "Analyze this electricity bill: total bill is $160.62 for 750 kWh. "
        "BGS Supply is $81.00 and Delivery is $41.25. State tax is $9.98. "
        "Explain the primary cost drivers in 3 concise bullet points."
    )
    benchmark_prompt(test_explanation_prompt, max_tokens=250, keep_alive="30m", label="Full Explanation Benchmark (Warm Model)")
