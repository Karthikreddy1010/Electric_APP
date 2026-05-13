"""
Full smoke test — all 15 endpoints (12 original + 3 new bill impact).
"""
import urllib.request
import json
import sys
import time

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
    t0 = time.time()
    try:
        result = fn()
        ms = (time.time() - t0) * 1000
        print(f"  [PASS] {name}  ({ms:.0f}ms)")
        passed += 1
        return result
    except Exception as e:
        ms = (time.time() - t0) * 1000
        print(f"  [FAIL] {name}  ({ms:.0f}ms): {e}")
        failed += 1
        return None


print("=" * 70)
print("ElectricAI FastAPI -- Full Endpoint Smoke Tests (15 endpoints)")
print("=" * 70)

# ── Original 12 ──────────────────────────────────────────────────────────
print("\n-- Original Endpoints (12) --")
check("GET  /health", lambda: get("/health"))
check("GET  /bill-breakdown?months=2", lambda: get("/bill-breakdown?months=2"))
check("GET  /trends?months=6", lambda: get("/trends?months=6"))
check("GET  /contribution", lambda: get("/contribution?month_index=-1"))
check("GET  /sensitivity", lambda: get("/sensitivity?month_index=-1&pct=10"))
check("GET  /geo-lookup", lambda: get("/geo-lookup?zip_code=07302"))
check("GET  /geo-all-counties", lambda: get("/geo-all-counties"))
check("POST /forecast", lambda: post("/forecast", {"months_ahead": 3, "model_type": "ensemble", "include_ci": True}))
check("POST /impact", lambda: post("/impact", {"top_n": 5}))
check("POST /benchmark", lambda: post("/benchmark", {"year": 2025, "compare_state": "NJ"}))
check("POST /plan-simulation", lambda: post("/plan-simulation", {"monthly_usage_kwh": 750, "n_simulations": 1000, "horizon_months": 12}))
check("POST /simulate-bill", lambda: post("/simulate-bill", {"bgs_cost": 100.0, "usage_kwh": 800}))

# ── New Bill Impact Engine (3) ───────────────────────────────────────────
print("\n-- New Bill Impact Endpoints (3) --")

# Sensitivity: +15% BGS rate
r = check("POST /impact/sensitivity (bgs_rate +15%)", lambda: post("/impact/sensitivity", {
    "component": "bgs_rate", "change_pct": 15.0
}))
if r:
    print(f"        Base: ${r['base_bill']} -> New: ${r['new_bill']}  (impact: ${r['impact_dollars']}, elasticity: {r['elasticity']})")

# What-if: multiple changes
r = check("POST /impact/what-if (multi-change)", lambda: post("/impact/what-if", {
    "changes": {"bgs_rate": 20, "sbc_rate": -10, "distribution_rate": 5},
    "kwh": 900
}))
if r:
    print(f"        Base: ${r['base_bill']} -> New: ${r['new_bill']}  (total impact: ${r['total_impact']})")

# Rank: all components
r = check("GET  /impact/rank", lambda: get("/impact/rank?test_pct=10"))
if r:
    top = r["rankings"][0]
    print(f"        #1 most impactful: {top['label']} (${top['impact_dollars']}/+10%, elasticity={top['elasticity']})")

print("\n" + "=" * 70)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed == 0:
    print("ALL 15 ENDPOINTS WORKING!")
else:
    print("Some endpoints failed.")
    sys.exit(1)
