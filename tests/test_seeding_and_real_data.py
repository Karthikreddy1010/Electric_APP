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


def test_eia861_master_loaded():
    """Verify EIA-861 master dataset is loaded into app_state and has valid records."""
    # Since lifespan context loads the app_state, we make a call or use a TestClient
    with TestClient(app) as client:
        df = app_state.get("eia861_master_df")
        assert df is not None, "EIA-861 master dataset is not loaded in app_state"
        assert len(df) > 0, "EIA-861 master dataset is empty"
        
        # Check that required columns exist
        required_cols = [
            "year", "utility_id", "utility_name", "state",
            "total_revenue", "total_sales_mwh", "total_customers", "avg_price",
            "nm_customers", "nm_energy_mwh", "peak_demand", "total_load",
            "demand_response_flag", "dynamic_pricing_flag"
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"


def test_billing_analyze_ocr_endpoint():
    """Verify the /analyze-ocr endpoint parses raw text correctly using fallback parser."""
    bill_txt = (
        "PSE&G Billing Statement\n"
        "Billing Period: 12/01/2025 - 12/31/2025\n"
        "Total Amount Due: $150.00\n"
        "Electricity Used: 800 kWh\n"
        "Supply Charges: $60.00\n"
        "Delivery Charges: $70.00\n"
        "Customer Charge: $15.00\n"
        "Sales Tax: $5.00\n"
    )
    with TestClient(app) as client:
        response = client.post("/analyze-ocr", json={"bill_text": bill_txt})
        assert response.status_code == 200
        data = response.json()
        assert "PSE&G" in data["utility_name"]
        assert "12/01/2025 - 12/31/2025" in data["billing_period"]
        assert data["kwh_used"] == 800.0
        assert data["total_amount"] == 150.0
        assert data["charges"]["supply"] == 60.0
        assert data["charges"]["delivery"] == 70.0
        assert data["charges"]["fixed"] == 15.0
        assert data["charges"]["tax"] == 5.0
        assert data["percentages"]["supply_pct"] == 40.0
        assert data["percentages"]["delivery_pct"] == 46.7
        assert data["percentages"]["fixed_pct"] == 10.0
        assert data["percentages"]["tax_pct"] == 3.3
        assert data["driver"] == "usage"
        assert "primary driver" in data["insight"].lower()


