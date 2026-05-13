"""
Smoke test for all FastAPI endpoints.
Run with: python test_endpoints.py
"""
import urllib.request
import json
import sys

BASE = "http://localhost:8000"
passed = 0
failed = 0


def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())


def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())


def check(name, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  [PASS] {name}")
        passed += 1
        return result
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1
        return None


print("=" * 60)
print("ElectricAI FastAPI -- Endpoint Smoke Tests")
print("=" * 60)

# GET endpoints
check("GET /health", lambda: get("/health"))
check("GET /bill-breakdown?months=2", lambda: get("/bill-breakdown?months=2"))
check("GET /trends?months=6", lambda: get("/trends?months=6"))
check("GET /contribution", lambda: get("/contribution?month_index=-1"))
check("GET /sensitivity", lambda: get("/sensitivity?month_index=-1&pct=10"))
check("GET /geo-lookup", lambda: get("/geo-lookup?zip_code=07302"))
check("GET /geo-all-counties", lambda: get("/geo-all-counties"))

# POST endpoints
check("POST /forecast", lambda: post("/forecast", {"months_ahead": 3, "model_type": "ensemble", "include_ci": True}))
check("POST /impact", lambda: post("/impact", {"top_n": 5}))
check("POST /benchmark", lambda: post("/benchmark", {"year": 2025, "compare_state": "NJ"}))
check("POST /plan-simulation", lambda: post("/plan-simulation", {"monthly_usage_kwh": 750, "n_simulations": 1000, "horizon_months": 12}))
check("POST /simulate-bill", lambda: post("/simulate-bill", {"bgs_cost": 100.0, "usage_kwh": 800}))

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed == 0:
    print("ALL ENDPOINTS WORKING!")
else:
    print("Some endpoints failed.")
    sys.exit(1)
