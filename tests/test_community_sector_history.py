"""
Sector history must actually read the community_energy table.

The query selected residential_electricity_kwh / commercial_electricity_kwh /
industrial_electricity_kwh, but those columns are named without the `_kwh`
suffix. The resulting OperationalError was swallowed into a warning and the
service returned [], so /municipal/sector-history answered 200 with an empty
payload while the table held thousands of rows — a silent data loss that no
status code revealed.
"""
import pytest
from sqlalchemy import inspect, text
from fastapi.testclient import TestClient

import api.main as main_module
from api.services.community_energy_service import community_energy_service
from database.connection import get_sync_engine


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        yield c


def test_queried_columns_exist():
    """Guard against the column names drifting from the table again."""
    engine = get_sync_engine()
    cols = {c["name"] for c in inspect(engine).get_columns("community_energy")}
    for required in (
        "year",
        "residential_electricity",
        "commercial_electricity",
        "industrial_electricity",
        "total_electricity_kwh",
        "total_natural_gas_therms",
    ):
        assert required in cols, f"community_energy is missing {required}"


def test_sector_history_returns_rows_when_table_is_populated(client):
    engine = get_sync_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM community_energy")).scalar()
    if not rows:
        pytest.skip("community_energy is empty in this environment")

    result = community_energy_service.get_sector_history()
    assert result, "sector history returned nothing despite a populated table"


def test_sector_history_endpoint_is_not_silently_empty(client):
    engine = get_sync_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*) FROM community_energy")).scalar()
    if not rows:
        pytest.skip("community_energy is empty in this environment")

    resp = client.get("/municipal/sector-history")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    payload = body.get("data", body)
    if isinstance(payload, dict):
        payload = payload.get("data", payload)
    assert payload, f"endpoint returned an empty payload: {body}"
