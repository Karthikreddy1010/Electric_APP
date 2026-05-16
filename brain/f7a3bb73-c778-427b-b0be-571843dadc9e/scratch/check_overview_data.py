import requests

try:
    res = requests.get("http://localhost:8000/overview")
    data = res.json()
    print("Breakdown Labels:")
    for b in data['breakdown']:
        print(f" - {b['label']}")
except Exception as e:
    print(f"Error: {e}")
