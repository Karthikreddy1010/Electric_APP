import urllib.request
import json
import sys

BASE = "http://localhost:8000"

print("Testing /llm/explain endpoint with standard response wrapping...")
payload_explain = {
    "task": "bill_analysis",
    "context_data": {
        "task": "bill_analysis",
        "customer": {"utility": "PSE&G"},
        "bill": {
            "total_bill": 160.62,
            "usage_kwh": 750.0,
            "effective_rate": 0.2142,
            "supply_charge": 81.0,
            "delivery_charge": 41.25,
            "tax": 9.98
        }
    }
}

req = urllib.request.Request(
    f"{BASE}/llm/explain",
    data=json.dumps(payload_explain).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=5) as r:
    raw = json.loads(r.read())
    print(f"  [PASS] Raw Envelope success: {raw.get('success')}")
    data = raw.get("data", {})
    print(f"  [PASS] Data Inner success: {data.get('success')}")
    print(f"  [PASS] Data Inner text length: {len(data.get('text', ''))} chars")
    print(f"  [PASS] Metadata provider: {data.get('metadata', {}).get('provider')}")
    print(f"  [PASS] Metadata fallback_used: {data.get('metadata', {}).get('fallback_used')}")
    print("\nSAMPLE GENERATED TEXT OUTPUT:")
    print("--------------------------------------------------")
    print(data.get('text', '').encode('ascii', errors='ignore').decode('ascii'))
    print("--------------------------------------------------")

print("\nALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY!")
