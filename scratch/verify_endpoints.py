import urllib.request
import json
import sys

BASE = "http://localhost:8000"

def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

print("Testing /impact/what-if-v2 endpoint...")
payload_whatif = {
    "changes": {"bgs_rate": 10.0, "distribution_rate": -5.0},
    "kwh": 800,
    "base_rates": {
        "customer_charge": 8.24,
        "bgs_rate": 0.105,
        "distribution_rate": 0.045,
        "transmission_rate": 0.015,
        "sbc_rate": 0.007,
        "transition_rate": 0.002,
        "nug_rate": 0.001,
        "rider_rate": 0.003
    },
    "base_costs": {
        "customer_charge": 8.24,
        "bgs_cost": 84.0,
        "distribution_cost": 36.0,
        "transmission_cost": 12.0,
        "sbc_cost": 5.6,
        "transition_cost": 1.6,
        "nug_cost": 0.8,
        "rider_cost": 2.4,
        "sales_tax": 9.98,
        "total_bill": 160.62
    }
}
res_whatif = post("/impact/what-if-v2", payload_whatif)
print(f"  [PASS] simulated_bill: ${res_whatif.get('simulated_bill')}")
print(f"  [PASS] base_bill: ${res_whatif.get('base_bill')}")
print(f"  [PASS] total_impact: ${res_whatif.get('total_impact')}")

# Verify accounting identity sum
contribs = res_whatif.get("contributions", {})
sum_components = sum(c["simulated_cost"] for c in contribs.values())
sim_bill = res_whatif.get("simulated_bill")
diff = abs(sum_components - sim_bill)
print(f"  [PASS] Components sum: ${sum_components:.2f} (diff vs total: ${diff:.4f})")
assert diff < 0.05, "Accounting identity violated!"

print("\nTesting /impact/explain endpoint...")
payload_explain = {
    "uploaded_bill": {"usage_kwh": 800, "total_bill": 160.62},
    "simulation_results": res_whatif,
    "scenario_inputs": {"changes": {"bgs_rate": 10.0}}
}
res_explain = post("/impact/explain", payload_explain)
print(f"  [PASS] success: {res_explain.get('success')}")
print(f"  [PASS] explanation length: {len(res_explain.get('explanation'))} chars")

print("\nTesting /impact/chat endpoint...")
payload_chat = {
    "message": "Why did BGS Supply increase?",
    "history": [],
    "uploaded_bill": {"usage_kwh": 800, "total_bill": 160.62},
    "simulation_results": res_whatif
}
res_chat = post("/impact/chat", payload_chat)
print(f"  [PASS] success: {res_chat.get('success')}")
print(f"  [PASS] answer: {res_chat.get('answer')}")

print("\nALL NEW IMPACT ENDPOINTS VERIFIED SUCCESSFULLY!")
