"""
Smoke Test script for EIA Retail Enterprise Feature Store & API endpoints.
Test direct FastAPI TestClient instantiation to verify all endpoints synchronously.
"""
from fastapi.testclient import TestClient
from api.main import app

def test_all_eia_endpoints():
    print("=" * 75)
    print("Testing EIA Retail Enterprise API Endpoints via TestClient (Lifespan Context)")
    print("=" * 75)

    endpoints = [
        ("GET", "/eia-retail/summary?focus_state=NJ"),
        ("GET", "/eia-retail/state-prices?stateid=NJ&sectorid=RES"),
        ("GET", "/eia-retail/rankings?sectorid=RES"),
        ("GET", "/eia-retail/quality-audit"),
        ("GET", "/eia-retail/datasets-registry"),
        ("GET", "/eia-retail/features-registry"),
        ("GET", "/forecast/eia?stateid=NJ&sectorid=RES&model=XGBoost&horizon_months=12"),
        ("GET", "/recommendations?stateid=NJ&monthly_kwh=750&effective_rate=0.22"),
        ("GET", "/admin-analytics/quality-dashboard"),
    ]

    passed = 0
    failed = 0

    with TestClient(app) as client:
        for method, path in endpoints:
            try:
                if method == "GET":
                    res = client.get(path)
                self_ok = res.status_code == 200
                if self_ok:
                    print(f"  [PASS] {method} {path} ({res.status_code})")
                    data = res.json()
                    if isinstance(data, dict) and "explainability" in data:
                        print(f"         Explainability metadata present: {data['explainability']['data_sources']}")
                    passed += 1
                else:
                    print(f"  [FAIL] {method} {path} ({res.status_code}): {res.text[:100]}")
                    failed += 1
            except Exception as e:
                print(f"  [FAIL] {method} {path}: {e}")
                failed += 1

    print("=" * 75)
    print(f"EIA API Endpoint Results: {passed} passed, {failed} failed out of {len(endpoints)} tests")
    assert failed == 0, f"{failed} endpoints failed!"

if __name__ == "__main__":
    test_all_eia_endpoints()
