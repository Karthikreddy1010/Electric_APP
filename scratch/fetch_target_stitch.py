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
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f"Error {tool_name}: {e}")
        return None

project_id = "8291854293309965546"
screen_id = "96f281109fef41a38b8dca1946738ffc"
name = f"projects/{project_id}/screens/{screen_id}"

res = mcp_call_tool("get_screen", {"name": name, "projectId": project_id, "screenId": screen_id}, 1)
print("Raw res keys:", res.keys() if res else "None")

with open("scratch/target_screen_dump.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

if res and "result" in res:
    content = res["result"].get("content", [])
    for item in content:
        if item.get("type") == "text":
            text_str = item.get("text", "{}")
            print("Text length:", len(text_str))
            obj = json.loads(text_str)
            print("JSON keys:", obj.keys())
            if "htmlCode" in obj:
                print("htmlCode type:", type(obj["htmlCode"]))
                print("htmlCode value:", str(obj["htmlCode"])[:500])
            if "screenshot" in obj:
                print("screenshot:", obj["screenshot"])
                url = obj["screenshot"].get("downloadUrl")
                if url:
                    urllib.request.urlretrieve(url, "scratch/target_screen_shot.png")
                    print("Saved screenshot to scratch/target_screen_shot.png")
