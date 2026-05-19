"""
Full smoke test — all 16 endpoints registered in ElectricAI.
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


def post_text(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req)
    return r.read().decode('utf-8')


def post_binary(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req)
    return r.read()  # returns raw binary


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


print("=" * 75)
print("ElectricAI FastAPI -- Up-to-date Smoke Tests (16 endpoints)")
print("=" * 75)

# 1. Health
check("GET  /health", lambda: get("/health"))

# 2. Dashboard overview KPIs
check("GET  /overview", lambda: get("/overview"))

# 3. Top-N cost component features
check("GET  /impact/top-features?n=5", lambda: get("/impact/top-features?n=5"))

# 4. Full impact analysis with OLS coefficients
full_res = check("GET  /impact/full-analysis", lambda: get("/impact/full-analysis"))
if full_res:
    print(f"        Base Bill: ${full_res.get('base_bill')}, Confidence: {full_res.get('confidence')}")

# 5. LLM or fallback explanation generator (using POST /report/generate)
check("POST /report/generate", lambda: post_text("/report/generate", {}))

# 6. PDF generation endpoint
pdf_bytes = check("POST /report/pdf", lambda: post_binary("/report/pdf", {}))
if pdf_bytes:
    print(f"        PDF Generated: {len(pdf_bytes)} bytes")

# 7. Simulator scenario logic
sim_body = {"modifications": {"bgs": 10}, "kwh": 750}
check("POST /simulate", lambda: post("/simulate", sim_body))

# 8. Geo Meta
meta = check("GET  /geo/meta", lambda: get("/geo/meta"))

# 9. Geo Map data for timeline
check("GET  /geo/data?month=2025-12&type=bill", lambda: get("/geo/data?month=2025-12&type=bill"))

# 10. Geo Trend analysis for state
check("GET  /geo/trend?region=NJ&type=bill", lambda: get("/geo/trend?region=NJ&type=bill"))

# 11. Geo Detail regional component breakdown
check("GET  /geo/detail?state=NJ&month=2025-12", lambda: get("/geo/detail?state=NJ&month=2025-12"))

# 12. Post AI insights analyzer for zipcodes
geo_insights_body = {
    "location": {"state": "NJ", "zip_codes": ["07302"]},
    "electricity_data": [
        {"zip_code": "07302", "state": "NJ", "month": 12, "year": 2025, "avg_price": 0.165, "consumption_kwh": 700.0, "peak_demand": 3.2, "renewable_ratio": 0.22}
    ]
}
check("POST /geo/generate-insights", lambda: post("/geo/generate-insights", geo_insights_body))

# 13. Billing breakdown
check("GET  /bill-breakdown?months=2", lambda: get("/bill-breakdown?months=2"))

# 14. Billing trend
check("GET  /trends?months=6", lambda: get("/trends?months=6"))

# 15. US benchmark rates
check("GET  /benchmark?year=2025&compare_state=NJ", lambda: get("/benchmark?year=2025&compare_state=NJ"))

# 16. Demand Forecast
check("GET  /forecast?horizon=30&model=ensemble", lambda: get("/forecast?horizon=30&model=ensemble"))

print("\n" + "=" * 75)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed == 0:
    print("ALL 16 ENDPOINTS WORKING AND VERIFIED!")
else:
    print("Some endpoints failed.")
    sys.exit(1)
