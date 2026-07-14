import urllib.request
import json
import os

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
    except Exception as e:
        print(f"Error {tool_name}: {e}")
        return None

project_id = "3410340932868783177"
screen_id = "c893b1bf9aca47ffb6f7daab9a0d90b6"
screen_name = f"projects/{project_id}/screens/{screen_id}"

print(f"Fetching screen details for {screen_name}...")
res = mcp_call_tool("get_screen", {"name": screen_name}, 200)

os.makedirs("artifacts", exist_ok=True)
if res and "result" in res:
    content = res["result"].get("content", [])
    for item in content:
        if item.get("type") == "text":
            obj = json.loads(item.get("text", "{}"))
            title = obj.get("title", "Regional & Peer Benchmarking Hub")
            shot = obj.get("screenshot", {}).get("downloadUrl")
            print(f"  Title: {title}")
            print(f"  Width: {obj.get('width')}, Height: {obj.get('height')}")
            if shot:
                save_path = f"artifacts/stitch_screen_{screen_id}.png"
                urllib.request.urlretrieve(shot, save_path)
                print(f"  [PASS] Downloaded image to {save_path}")
            
            with open("scratch/benchmarking_screen_obj.json", "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2)
            print("  [PASS] Saved JSON metadata to scratch/benchmarking_screen_obj.json")
