"""
/grid/demand must work on every configured database backend.

The hourly window was built with `INTERVAL '<n> hours'`, which is PostgreSQL
syntax. The app falls back to SQLite when Postgres is unreachable (the default
for local development), where INTERVAL does not exist — so the endpoint raised
`sqlite3.OperationalError: no such column: INTERVAL` and returned a 500.
"""
import pytest
from fastapi.testclient import TestClient

import api.main as main_module


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        yield c


def test_grid_demand_returns_series(client):
    resp = client.get("/grid/demand?ba=PJM&hours=24")
    assert resp.status_code == 200, resp.text


def test_grid_demand_respects_hours_window(client):
    """A wider window must not return fewer points than a narrow one."""
    narrow = client.get("/grid/demand?ba=PJM&hours=6")
    wide = client.get("/grid/demand?ba=PJM&hours=48")
    assert narrow.status_code == 200, narrow.text
    assert wide.status_code == 200, wide.text

    def points(resp):
        body = resp.json()
        return body["data"] if isinstance(body, dict) and "data" in body else body

    assert len(points(wide)) >= len(points(narrow))


def test_grid_demand_unknown_ba_is_not_a_server_error(client):
    """An unknown balancing authority is a client/404 condition, not a 500."""
    resp = client.get("/grid/demand?ba=NOSUCHBA&hours=24")
    assert resp.status_code < 500, resp.text
