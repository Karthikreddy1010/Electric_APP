import urllib.request
import json
import sys

project_id = "3410340932868783177"
screen_id = "96758b9bca0b424b9cd20b41beabebf6"

urls = [
    f"https://stitch.canvas.google.com/projects/{project_id}/screens/{screen_id}",
    f"https://stitch.google/projects/{project_id}/screens/{screen_id}",
    f"https://stitch.corp.google.com/projects/{project_id}/screens/{screen_id}",
    f"https://stitch.googleapis.com/v1/projects/{project_id}/screens/{screen_id}",
    f"https://stitch-cdn.google.com/projects/{project_id}/screens/{screen_id}.html",
    f"https://stitch-export.google.com/{project_id}/{screen_id}",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

for url in urls:
    print(f"Testing: {url}")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as r:
            content = r.read().decode('utf-8', errors='ignore')
            print(f"  SUCCESS! HTTP {r.status}, Content Length: {len(content)}")
            print("  Preview:", content[:300])
            with open("scratch/stitch_screen.html", "w", encoding="utf-8") as f:
                f.write(content)
            break
    except Exception as e:
        print(f"  Error: {e}")
