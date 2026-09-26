"""
Google OAuth sign-in.

These cover the parts that must hold without contacting Google: the CSRF state
handshake, the behaviour when credentials are absent, and the account-linking
policy. The token exchange and ID-token verification are stubbed, since a real
round trip needs live Google credentials.
"""
import secrets
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

import api.main as main_module
import api.routes.oauth_router as oauth
from api.auth_config import auth_config


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def configured(monkeypatch):
    """Pretend OAuth credentials are present."""
    monkeypatch.setattr(auth_config, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(auth_config, "GOOGLE_CLIENT_SECRET", "test-client-secret")


def _error_code(response) -> str | None:
    """Pull the ?error= code off the redirect back to the login page."""
    location = response.headers.get("location", "")
    return parse_qs(urlparse(location).query).get("error", [None])[0]


# ── Configuration ────────────────────────────────────────────────────────────

def test_login_without_credentials_reports_not_configured(client, monkeypatch):
    """Absent credentials must give a clear message, not a crash or a silent no-op."""
    monkeypatch.setattr(auth_config, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(auth_config, "GOOGLE_CLIENT_SECRET", "")

    resp = client.get("/auth/google/login", follow_redirects=False)
    assert resp.status_code == 303
    assert _error_code(resp) == "google_not_configured"


# ── Authorization request ────────────────────────────────────────────────────

def test_login_redirects_to_google_with_state_cookie(client, configured):
    resp = client.get("/auth/google/login", follow_redirects=False)
    assert resp.status_code == 303

    location = resp.headers["location"]
    assert location.startswith(oauth.GOOGLE_AUTH_ENDPOINT)

    query = parse_qs(urlparse(location).query)
    assert query["client_id"] == ["test-client-id.apps.googleusercontent.com"]
    assert query["response_type"] == ["code"]
    assert "openid" in query["scope"][0]
    assert query["state"], "no state parameter issued"

    # The state must also be stored in a cookie so the callback can compare.
    assert oauth._STATE_COOKIE in resp.cookies
    assert resp.cookies[oauth._STATE_COOKIE] == query["state"][0]


def test_state_cookie_is_http_only(client, configured):
    """The state cookie is a CSRF control and must not be readable by JS."""
    resp = client.get("/auth/google/login", follow_redirects=False)
    set_cookie = "".join(
        v for k, v in resp.headers.items()
        if k.lower() == "set-cookie" and oauth._STATE_COOKIE in v
    )
    assert "httponly" in set_cookie.lower()


# ── Callback: CSRF state handling ────────────────────────────────────────────

def test_callback_rejects_missing_state_cookie(client, configured):
    """A code with no matching cookie is a forged callback."""
    resp = client.get(
        "/auth/google/callback?code=abc&state=whatever", follow_redirects=False
    )
    assert _error_code(resp) == "google_state_mismatch"


def test_callback_rejects_mismatched_state(client, configured):
    client.cookies.set(oauth._STATE_COOKIE, "the-real-state")
    try:
        resp = client.get(
            "/auth/google/callback?code=abc&state=an-attacker-state",
            follow_redirects=False,
        )
        assert _error_code(resp) == "google_state_mismatch"
    finally:
        client.cookies.clear()


def test_callback_without_code_is_rejected(client, configured):
    state = secrets.token_urlsafe(16)
    client.cookies.set(oauth._STATE_COOKIE, state)
    try:
        resp = client.get(
            f"/auth/google/callback?state={state}", follow_redirects=False
        )
        assert _error_code(resp) == "google_no_code"
    finally:
        client.cookies.clear()


def test_callback_surfaces_user_denial(client, configured):
    """Dismissing the consent screen is not an error state worth alarming about."""
    resp = client.get(
        "/auth/google/callback?error=access_denied", follow_redirects=False
    )
    assert _error_code(resp) == "google_denied"


# ── Callback: identity assertions ────────────────────────────────────────────

def _stub_google(monkeypatch, claims):
    """Stub the token exchange and ID-token verification."""
    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"id_token": "stub-id-token"}

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(
        oauth.google_id_token, "verify_oauth2_token", lambda *a, **kw: claims
    )


def test_unverified_google_email_is_refused(client, configured, monkeypatch):
    """Without Google's email_verified claim the address proves nothing."""
    _stub_google(monkeypatch, {"email": "nobody@example.com", "email_verified": False})

    state = secrets.token_urlsafe(16)
    client.cookies.set(oauth._STATE_COOKIE, state)
    try:
        resp = client.get(
            f"/auth/google/callback?code=abc&state={state}", follow_redirects=False
        )
        assert _error_code(resp) == "google_email_unverified"
    finally:
        client.cookies.clear()


def test_id_token_without_email_is_refused(client, configured, monkeypatch):
    _stub_google(monkeypatch, {"email_verified": True})

    state = secrets.token_urlsafe(16)
    client.cookies.set(oauth._STATE_COOKIE, state)
    try:
        resp = client.get(
            f"/auth/google/callback?code=abc&state={state}", follow_redirects=False
        )
        assert _error_code(resp) == "google_no_email"
    finally:
        client.cookies.clear()


def test_invalid_id_token_is_refused(client, configured, monkeypatch):
    """A token failing signature/audience checks must never establish a session."""
    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"id_token": "forged"}

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(oauth.httpx, "AsyncClient", _Client)

    def _reject(*a, **kw):
        raise ValueError("Token has wrong audience")

    monkeypatch.setattr(oauth.google_id_token, "verify_oauth2_token", _reject)

    state = secrets.token_urlsafe(16)
    client.cookies.set(oauth._STATE_COOKIE, state)
    try:
        resp = client.get(
            f"/auth/google/callback?code=abc&state={state}", follow_redirects=False
        )
        assert _error_code(resp) == "google_invalid_token"
    finally:
        client.cookies.clear()
