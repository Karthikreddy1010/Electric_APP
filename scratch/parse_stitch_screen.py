import json
import urllib.request
import os

with open("scratch/stitch_get_screen.json", "r", encoding="utf-8") as f:
    data = json.load(f)

content_items = data.get("result", {}).get("content", [])
screen_obj = {}
for item in content_items:
    if item.get("type") == "text":
        try:
            screen_obj = json.loads(item.get("text", "{}"))
        except Exception as e:
            print("Error parsing text item JSON:", e)

print("Screen Title:", screen_obj.get("title"))
print("Screen Name:", screen_obj.get("name"))
print("Keys in screen object:", screen_obj.keys())

# Check screenshot download URL
screenshot = screen_obj.get("screenshot", {})
download_url = screenshot.get("downloadUrl")
if download_url:
    print(f"Downloading Screenshot image from {download_url[:60]}...")
    try:
        os.makedirs("artifacts", exist_ok=True)
        img_path = os.path.abspath("artifacts/electric_ai_landing_redesign.png")
        urllib.request.urlretrieve(download_url, img_path)
        print(f"Saved screenshot to {img_path}")
    except Exception as e:
        print("Error downloading screenshot:", e)

# Check html / code components
code_obj = screen_obj.get("htmlCode") or screen_obj.get("code") or screen_obj.get("html")
if not code_obj:
    for k, v in screen_obj.items():
        if "html" in k.lower() or "code" in k.lower():
            print(f"Found code field '{k}':", str(v)[:200])

print("\nFull screen object dump saved to scratch/screen_obj_dump.json")
with open("scratch/screen_obj_dump.json", "w", encoding="utf-8") as f:
    json.dump(screen_obj, f, indent=2)
