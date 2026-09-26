"""
/utility/search must work on every configured database backend.

The name filter used `ILIKE`, which is PostgreSQL-only. This app falls back to
SQLite whenever Postgres is unreachable (the default for local development),
where ILIKE does not exist — so both branches of the query raised
`sqlite3.OperationalError` and the endpoint returned a 500.
"""
import pytest
from fastapi.testclient import TestClient

import api.main as main_module


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        yield c


def test_search_without_state(client):
    resp = client.get("/utility/search?name=Public")
    assert resp.status_code == 200, resp.text


def test_search_with_state(client):
    resp = client.get("/utility/search?name=Public&state=NJ")
    assert resp.status_code == 200, resp.text


def test_search_is_case_insensitive(client):
    """ILIKE was case-insensitive; the portable replacement must stay so."""
    lower = client.get("/utility/search?name=public")
    upper = client.get("/utility/search?name=PUBLIC")
    assert lower.status_code == 200, lower.text
    assert upper.status_code == 200, upper.text

    def rows(resp):
        body = resp.json()
        return body["data"] if isinstance(body, dict) and "data" in body else body

    assert len(rows(lower)) == len(rows(upper))


def test_search_no_match_is_not_a_server_error(client):
    resp = client.get("/utility/search?name=zzzznosuchutility")
    assert resp.status_code < 500, resp.text
