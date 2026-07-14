import urllib.request
import json
import os
import sys

URL = "https://stitch.googleapis.com/mcp"
API_KEY = os.getenv("STITCH_API_KEY", "")

headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY
}

def mcp_request(method, params=None, req_id=1):
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            res_data = r.read().decode('utf-8')
            return json.loads(res_data)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print("1. Initializing MCP connection...")
init_params = {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "ElectricAI-Agent", "version": "1.0"}
}
res_init = mcp_request("initialize", init_params, 1)
print("Initialize Response:", json.dumps(res_init, indent=2))

print("\n2. Listing Available MCP Tools...")
res_tools = mcp_request("tools/list", {}, 2)
print("Tools List Response:", json.dumps(res_tools, indent=2))

if res_tools and "result" in res_tools:
    tools = res_tools["result"].get("tools", [])
    print(f"\nDiscovered {len(tools)} Stitch MCP tools:")
    for t in tools:
        print(f" - {t.get('name')}: {t.get('description')}")
