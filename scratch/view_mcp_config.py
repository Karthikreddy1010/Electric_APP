import os
import json

path = os.path.expanduser(r"~\.gemini\config\mcp_config.json")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Found mcp_config.json:")
    print(json.dumps(data, indent=2))
else:
    print("mcp_config.json does not exist at", path)
