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

screen_ids = [
    "96758b9bca0b424b9cd20b41beabebf6",
    "ab012552d91e40deb98962db79ae95cc",
    "ba20a0c772524a5481b11e3e7548a9ba",
    "bc05d543262341728b59958c1c3e6bf1",
    "c893b1bf9aca47ffb6f7daab9a0d90b6",
    "e167fb7feda1487db2a1b2159de5b6c2",
    "f6c2c83fdae946db82762e8dbc948bf2",
    "fce3500eca644bd2a67b4e193eb52299"
]

project_id = "3410340932868783177"
os.makedirs("artifacts", exist_ok=True)

for sid in screen_ids:
    name = f"projects/{project_id}/screens/{sid}"
    print(f"Checking screen: {sid}...")
    res = mcp_call_tool("get_screen", {"name": name}, 100)
    if res and "result" in res:
        content = res["result"].get("content", [])
        for item in content:
            if item.get("type") == "text":
                obj = json.loads(item.get("text", "{}"))
                title = obj.get("title", "Untitled")
                code = obj.get("htmlCode")
                shot = obj.get("screenshot", {}).get("downloadUrl")
                print(f"  Title: '{title}', Code keys: {code.keys() if isinstance(code, dict) else type(code)}")
                if shot:
                    save_path = f"artifacts/stitch_screen_{sid}.png"
                    try:
                        urllib.request.urlretrieve(shot, save_path)
                        print(f"  Saved image to {save_path}")
                    except Exception as e:
                        print(f"  Error downloading screenshot: {e}")
