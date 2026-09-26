"""
Google OAuth 2.0 sign-in.

Authorization-code flow: the browser is redirected to Google, comes back to
/auth/google/callback with a code, and the code is exchanged server-side, so
the client secret never reaches the browser.

On success the user receives exactly the same HTTP-only session cookies that
POST /auth/login issues, so the rest of the app needs no special handling for
OAuth sessions.

Account linking policy
----------------------
A Google identity is linked to an existing local account only when BOTH:
  * Google asserts the address is verified (the email_verified claim), and
  * the local account has already verified that same address.

Linking to an unverified local account would let anyone who registered an
address they do not own take it over by signing in with Google. Such attempts
are refused, and the user is told to sign in with their password and verify
the address first.
"""
from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_config import auth_config
from api.auth_utils import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    hash_password,
    set_auth_cookies,
    set_csrf_cookie,
)
from api.services import auth_service
from database.auth_models import User
from database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["auth"])

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Short-lived cookie holding the CSRF state for one round trip to Google.
_STATE_COOKIE = "google_oauth_state"
_STATE_TTL_SECONDS = 600


def _frontend_url(path: str, **params: str) -> str:
    """Build an absolute URL back into the SPA."""
    base = auth_config.FRONTEND_URL.rstrip("/")
    url = f"{base}/app{path}"
    return f"{url}?{urlencode(params)}" if params else url


def _fail(reason: str, log_message: str) -> RedirectResponse:
    """Send the browser back to the login screen with a displayable reason.

    This is a redirect flow, so errors cannot be returned as JSON: the user is
    sitting in front of a browser, not an API client. Details stay in the log
    and only a short code reaches the URL.
    """
    logger.warning("Google OAuth failed: %s", log_message)
    response = RedirectResponse(_frontend_url("/login", error=reason), status_code=303)
    response.delete_cookie(_STATE_COOKIE, path="/")
    return response


@router.get("/login")
async def google_login() -> Response:
    """Begin the flow by redirecting to Google's consent screen."""
    if not auth_config.google_oauth_configured:
        return _fail(
            "google_not_configured",
            "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set",
        )

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": auth_config.GOOGLE_CLIENT_ID,
        "redirect_uri": auth_config.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        # Always show the account chooser, so a signed-out user is not silently
        # re-authenticated as whoever the browser last used.
        "prompt": "select_account",
    }

    response = RedirectResponse(
        f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}", status_code=303
    )
    response.set_cookie(
        _STATE_COOKIE,
        state,
        max_age=_STATE_TTL_SECONDS,
        httponly=True,
        secure=auth_config.COOKIE_SECURE,
        # lax still sends the cookie on Google's top-level GET redirect back.
        samesite="lax",
        path="/",
    )
    return response


@router.get("/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    """Exchange the authorization code and establish a session."""
    if error:
        # The user dismissed the consent screen, or Google refused.
        return _fail("google_denied", f"Google returned error={error}")

    if not auth_config.google_oauth_configured:
        return _fail("google_not_configured", "OAuth credentials missing at callback")

    expected_state = request.cookies.get(_STATE_COOKIE)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        return _fail("google_state_mismatch", "state parameter did not match the cookie")

    if not code:
        return _fail("google_no_code", "callback arrived without an authorization code")

    # Exchange the code for tokens server-side.
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": auth_config.GOOGLE_CLIENT_ID,
                    "client_secret": auth_config.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": auth_config.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
    except httpx.HTTPError as exc:
        return _fail("google_unreachable", f"token endpoint unreachable: {exc}")

    if token_response.status_code != 200:
        return _fail(
            "google_token_exchange",
            f"token endpoint returned {token_response.status_code}",
        )

    raw_id_token = token_response.json().get("id_token")
    if not raw_id_token:
        return _fail("google_no_id_token", "token response contained no id_token")

    # Verify the ID token: signature, issuer, audience and expiry.
    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            auth_config.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        return _fail("google_invalid_token", f"ID token verification failed: {exc}")

    email = (claims.get("email") or "").lower().strip()
    if not email:
        return _fail("google_no_email", "ID token contained no email claim")

    # Google must vouch for the address, otherwise it proves nothing about who
    # is signing in.
    if not claims.get("email_verified"):
        return _fail("google_email_unverified", f"Google reports {email} as unverified")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if user is None:
        user = User(
            email=email,
            # No password is set for a Google-created account. The column is
            # NOT NULL, so store a hash of an unguessable random value: no
            # password can ever match it, and the user can adopt one later
            # through the normal password-reset flow.
            password_hash=hash_password(secrets.token_urlsafe(64)),
            first_name=(claims.get("given_name") or email.split("@")[0]).strip(),
            last_name=(claims.get("family_name") or "").strip(),
            # Google already proved ownership of the address.
            email_verified=True,
        )
        db.add(user)
        await db.flush()
        await auth_service.log_event(
            db,
            "signup",
            request,
            user_id=user.id,
            details={"email": email, "provider": "google"},
        )
    elif not user.email_verified:
        # See the account-linking policy in this module's docstring.
        return _fail(
            "google_link_requires_verified_account",
            f"refused to link Google identity to unverified local account {email}",
        )

    if user.account_status != "active":
        return _fail(
            "account_not_active", f"account {email} has status {user.account_status}"
        )

    # Issue the same session cookies a password login would.
    expires_days = auth_config.REFRESH_TOKEN_EXPIRE_DAYS
    access_token = create_access_token(
        {"sub": user.id, "email": user.email, "role": user.role}
    )
    raw_refresh_token = create_refresh_token(
        {"sub": user.id}, expires_delta=timedelta(days=expires_days)
    )

    response = RedirectResponse(_frontend_url("/overview"), status_code=303)
    set_auth_cookies(
        response, access_token, raw_refresh_token, remember_me=False
    )
    set_csrf_cookie(response, generate_csrf_token())
    response.delete_cookie(_STATE_COOKIE, path="/")

    await auth_service.create_session(
        db=db,
        request=request,
        user=user,
        raw_refresh_token=raw_refresh_token,
        expires_days=expires_days,
    )
    await auth_service.log_event(
        db, "login", request, user_id=user.id, details={"provider": "google"}
    )
    await db.commit()

    return response
