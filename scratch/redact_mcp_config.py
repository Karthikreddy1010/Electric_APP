import os
import json

path = os.path.expanduser(r"~\.gemini\config\mcp_config.json")
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Check args
    for server_name, server_cfg in data.get("mcpServers", {}).items():
        args = server_cfg.get("args", [])
        new_args = []
        for arg in args:
            if arg.startswith("X-Goog-Api-Key:"):
                new_args.append("X-Goog-Api-Key: YOUR_NEW_REGENERATED_API_KEY")
            else:
                new_args.append(arg)
        server_cfg["args"] = new_args

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Sanitized mcp_config.json on disk!")
