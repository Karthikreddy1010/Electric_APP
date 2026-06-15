"""
Security & Auth Module — handles user authentication and role-based access control (RBAC).

Uses HMAC-SHA256 tokens for session security without external dependencies.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Secret key for token signing (in production, read from env)
SECRET_KEY = os.environ.get("API_SECRET_KEY", "electric-ai-super-secret-key-1010!")
TOKEN_EXPIRE_SECONDS = 3600  # 1 hour

# Bearer token scheme
security_scheme = HTTPBearer()

# In-memory user database for demo purposes
USERS_DB = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256(b"admin123").hexdigest(),
        "role": "admin"
    },
    "viewer": {
        "username": "viewer",
        "password_hash": hashlib.sha256(b"viewer123").hexdigest(),
        "role": "viewer"
    }
}


def create_access_token(payload: dict, expires_in: int = TOKEN_EXPIRE_SECONDS) -> str:
    """Generate a secure signed token."""
    header = {"alg": "HS256", "typ": "JWT"}
    
    # Add expiration claim
    payload_copy = payload.copy()
    payload_copy["exp"] = int(time.time()) + expires_in
    
    # Encode header and payload to base64
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload_copy).encode()).decode().rstrip("=")
    
    # Sign signature
    msg = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode a signed token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
            
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        msg = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None
            
        # Decode payload (pad base64 if needed)
        padding_needed = 4 - (len(payload_b64) % 4)
        if padding_needed < 4:
            payload_b64 += "=" * padding_needed
            
        payload_data = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        
        # Check expiration
        if payload_data.get("exp", 0) < time.time():
            return None
            
        return payload_data
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> dict:
    """Dependency that extracts the authenticated user from the request header."""
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


class RoleChecker:
    """RBAC checker dependency."""
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("role")
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{user_role}' does not have permissions.",
            )
        return user
