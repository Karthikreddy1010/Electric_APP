"""
Component-key validation on the /impact endpoints.

`component` was typed as a bare `str`, so an unrecognised key reached an
unguarded COMPONENT_TYPES[...] lookup. /impact/sensitivity turned that into a
500, while /impact/what-if and /what-if-v2 quietly dropped the unknown key and
returned a successful-looking simulation that had not applied the requested
change. Both are client errors and must be rejected as such.
"""
import pytest
from fastapi.testclient import TestClient

import api.main as main_module
from api.services.bill_impact_engine import COMPONENT_TYPES


@pytest.fixture(scope="module")
def client():
    # `with` runs the lifespan so datasets/models load; without it every
    # request short-circuits to a 400 and proves nothing.
    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        yield c


VALID_COMPONENT = "bgs_rate"
INVALID_COMPONENT = "generation"


def test_component_literal_matches_engine():
    """The schema's allowed keys must not drift from the engine's."""
    from api.schemas import COMPONENT_KEYS

    assert set(COMPONENT_KEYS) == set(COMPONENT_TYPES), (
        "api.schemas.COMPONENT_KEYS is out of sync with "
        "bill_impact_engine.COMPONENT_TYPES"
    )


def test_sensitivity_accepts_valid_component(client):
    resp = client.post(
        "/impact/sensitivity", json={"component": VALID_COMPONENT, "change_pct": 10}
    )
    assert resp.status_code == 200, resp.text


def test_sensitivity_rejects_unknown_component(client):
    """Was a 500 (KeyError); an unknown key is the caller's error."""
    resp = client.post(
        "/impact/sensitivity", json={"component": INVALID_COMPONENT, "change_pct": 10}
    )
    assert resp.status_code == 422, resp.text
    assert resp.status_code != 500


def test_what_if_rejects_unknown_component(client):
    """Was a silent no-op returning 200."""
    resp = client.post(
        "/impact/what-if", json={"changes": {INVALID_COMPONENT: 10}, "kwh": 750}
    )
    assert resp.status_code == 422, resp.text


def test_what_if_v2_rejects_unknown_component(client):
    """Was a silent no-op returning 200."""
    resp = client.post(
        "/impact/what-if-v2", json={"changes": {INVALID_COMPONENT: 10}, "kwh": 750}
    )
    assert resp.status_code == 422, resp.text


def test_what_if_still_accepts_valid_components(client):
    resp = client.post(
        "/impact/what-if", json={"changes": {VALID_COMPONENT: 10}, "kwh": 750}
    )
    assert resp.status_code == 200, resp.text
