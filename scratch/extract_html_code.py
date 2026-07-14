import json

with open("scratch/screen_obj_dump.json", "r", encoding="utf-8") as f:
    screen_obj = json.load(f)

html_code = screen_obj.get("htmlCode", {})
print("Keys inside htmlCode:", html_code.keys() if isinstance(html_code, dict) else type(html_code))

if isinstance(html_code, dict):
    for k, v in html_code.items():
        print(f"  Field '{k}': type={type(v)}, len={len(v) if hasattr(v, '__len__') else 'N/A'}")
        if isinstance(v, str):
            print(f"    Preview of '{k}': {v[:200]}...")
            with open(f"scratch/stitch_{k}.html", "w", encoding="utf-8") as out:
                out.write(v)
            print(f"    Saved scratch/stitch_{k}.html")
        elif isinstance(v, dict):
            print(f"    Subkeys of '{k}':", v.keys())
            with open(f"scratch/stitch_{k}.json", "w", encoding="utf-8") as out:
                json.dump(v, out, indent=2)
