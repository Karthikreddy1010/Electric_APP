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

def mcp_call_tool(tool_name, arguments, req_id=1):
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res_data = r.read().decode('utf-8')
            return json.loads(res_data)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

project_id = "3410340932868783177"
screen_id = "96758b9bca0b424b9cd20b41beabebf6"

print(f"1. Getting screen details for Project {project_id}, Screen {screen_id}...")
# Note: Stitch names projects like "projects/3410340932868783177" or "projects/3410340932868783177/screens/96758b9bca0b424b9cd20b41beabebf6"
screen_name = f"projects/{project_id}/screens/{screen_id}"

res_screen = mcp_call_tool("get_screen", {"name": screen_name}, 10)

with open("scratch/stitch_get_screen.json", "w", encoding="utf-8") as f:
    json.dump(res_screen, f, indent=2)

print("Saved raw get_screen result to scratch/stitch_get_screen.json!")

if res_screen and "result" in res_screen:
    print("Result structure keys:", res_screen["result"].keys())
    content = res_screen["result"].get("content", [])
    for idx, item in enumerate(content):
        print(f"Content Item {idx} type: {item.get('type')}")
        if item.get("type") == "text":
            print(f"Text snippet: {item.get('text')[:300]}...")
