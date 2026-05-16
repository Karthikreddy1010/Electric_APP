import requests

try:
    res = requests.get("http://localhost:8000/plans")
    print(f"Status: {res.status_code}")
    print(f"Body: {res.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
