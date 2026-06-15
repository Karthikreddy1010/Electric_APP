import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.state import app_state

def test_bgs_rates_endpoint():
    """Verify the /bgs/rates endpoint returns pivoted historical BGS data."""
    with TestClient(app) as client:
        # Ensure app_state has data
        if app_state.get("bgs_auction_df") is None:
            pytest.skip("BGS Auction data not loaded into app_state")

        response = client.get("/bgs/rates")
        assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "data" in data
    assert isinstance(data["data"], list)
    
    if len(data["data"]) > 0:
        row = data["data"][0]
        assert "year" in row
        # Ensure at least one EDC column exists
        assert any(edc in row for edc in ["PSE&G", "JCP&L", "ACE", "RECO"])

def test_municipal_list_endpoint():
    """Verify the /municipal/list endpoint returns a list of municipalities."""
    with TestClient(app) as client:
        if app_state.get("community_energy_df") is None:
            pytest.skip("Community energy data not loaded into app_state")

        response = client.get("/municipal/list")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "municipalities" in data
        assert isinstance(data["municipalities"], list)

def test_municipal_benchmark_endpoint():
    """Verify the /municipal/benchmark endpoint returns benchmark history for a valid muni."""
    with TestClient(app) as client:
        if app_state.get("community_energy_df") is None:
            pytest.skip("Community energy data not loaded into app_state")

        # Fetch list to get a valid name
        list_res = client.get("/municipal/list").json()
        if not list_res.get("municipalities"):
            pytest.skip("No municipalities found in dataset")
            
        valid_name = list_res["municipalities"][0]

        response = client.get(f"/municipal/benchmark?name={valid_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["municipality"] == valid_name
        assert "history" in data
        assert isinstance(data["history"], list)
        
        if len(data["history"]) > 0:
            hist = data["history"][0]
            assert "residential_electricity_kwh" in hist
            assert "year" in hist

def test_municipal_benchmark_not_found():
    """Verify /municipal/benchmark handles invalid municipalities."""
    with TestClient(app) as client:
        if app_state.get("community_energy_df") is None:
            pytest.skip("Community energy data not loaded into app_state")

        response = client.get("/municipal/benchmark?name=InvalidTownNameXYZ123")
        assert response.status_code == 404
