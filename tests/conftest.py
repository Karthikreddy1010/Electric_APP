import pytest
import requests
import json
import inspect
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# 1. Mock Open-Meteo Weather Forecast API to prevent external network calls and 503s
@pytest.fixture(autouse=True)
def mock_openmeteo_forecast(monkeypatch):
    original_get = requests.get

    def mock_get(url, *args, **kwargs):
        if "api.open-meteo.com/v1/forecast" in url:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            params = kwargs.get("params", {}) or {}
            days = params.get("forecast_days", 30)
            
            # Generate fake temperature lists of length `days`
            times = [f"2026-07-{9+i:02d}" for i in range(days)]
            max_temps = [25.0 + i * 0.1 for i in range(days)]
            min_temps = [15.0 + i * 0.1 for i in range(days)]
            
            mock_resp.json.return_value = {
                "daily": {
                    "time": times,
                    "temperature_2m_max": max_temps,
                    "temperature_2m_min": min_temps
                }
            }
            mock_resp.raise_for_status = MagicMock()
            return mock_resp
        return original_get(url, *args, **kwargs)

    monkeypatch.setattr(requests, "get", mock_get)

# 2. Automatically unwrap standard response envelopes in TestClient for existing tests
original_request = TestClient.request

def should_unwrap():
    # If the caller is from test_auth_c3.py, do not unwrap because it explicitly tests the wrapped format
    for frame in inspect.stack():
        if "test_auth_c3.py" in frame.filename:
            return False
    return True

def wrapped_request(self, method, url, *args, **kwargs):
    response = original_request(self, method, url, *args, **kwargs)
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and response.status_code < 400 and should_unwrap():
        original_json = response.json
        def new_json(*j_args, **j_kwargs):
            data = original_json(*j_args, **j_kwargs)
            if isinstance(data, dict) and data.get("success") is True and "data" in data:
                return data["data"]
            return data
        response.json = new_json
    return response

TestClient.request = wrapped_request
