import urllib.request
import json
import os

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
        with urllib.request.urlopen(req, timeout=30) as r:
            res_data = r.read().decode('utf-8')
            return json.loads(res_data)
    except Exception as e:
        print(f"Error {method}: {e}")
        return None

def mcp_call_tool(tool_name, arguments, req_id=1):
    return mcp_request("tools/call", {"name": tool_name, "arguments": arguments}, req_id)

project_name = "projects/3410340932868783177"

print("1. Querying get_project...")
res_proj = mcp_call_tool("get_project", {"name": project_name}, 20)
print("Project Info:", json.dumps(res_proj, indent=2))

print("\n2. Querying list_screens...")
res_screens = mcp_call_tool("list_screens", {"parent": project_name}, 21)
print("Screens List:", json.dumps(res_screens, indent=2))

print("\n3. Querying resources/list...")
res_res = mcp_request("resources/list", {}, 22)
print("Resources List:", json.dumps(res_res, indent=2))
