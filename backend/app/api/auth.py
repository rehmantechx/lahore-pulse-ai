"""Authentication endpoints.

Provides minimal authentication for hackathon demo.
Uses HMAC-SHA256 tokens with role-based access control.

Roles:
    - citizen: Read-only access to public data
    - officer: Read + command center access
    - admin: Full access including ingestion control

For hackathon: role-based login with hardcoded demo credentials.
No real user database — tokens encode role and expiry.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Token Configuration ──────────────────────────────────────────
# Secret key for HMAC signing (in production, use env variable)
_TOKEN_SECRET = os.environ.get(
    "LPA_AUTH_SECRET",
    "lahore-plus-hackathon-secret-key-change-in-production",
)
_TOKEN_EXPIRY_HOURS = 24  # Tokens expire after 24 hours


# ── Demo Users ───────────────────────────────────────────────────
# Hardcoded for hackathon — no database needed
DEMO_USERS = {
    "citizen": {
        "password": "citizen123",
        "role": "citizen",
        "display_name": "Public Citizen",
    },
    "officer": {
        "password": "officer123",
        "role": "officer",
        "display_name": "Air Quality Officer",
    },
    "admin": {
        "password": "admin123",
        "role": "admin",
        "display_name": "System Administrator",
    },
}


# ── Request/Response Models ──────────────────────────────────────
class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., min_length=1, max_length=50, description="Username")
    password: str = Field(..., min_length=1, max_length=100, description="Password")


class LoginResponse(BaseModel):
    """Login response with token."""

    token: str = Field(..., description="Authentication token")
    role: str = Field(..., description="User role")
    display_name: str = Field(..., description="Display name")
    expires_at: str = Field(..., description="Token expiry ISO timestamp")


class TokenPayload(BaseModel):
    """Decoded token payload."""

    sub: str = Field(..., description="Subject (username)")
    role: str = Field(..., description="User role")
    exp: float = Field(..., description="Expiry timestamp")


# ── Token Utilities ──────────────────────────────────────────────
def _create_token(username: str, role: str) -> str:
    """Create an HMAC-SHA256 signed token.

    Token format: base64(header).base64(payload).signature
    Header: {"alg": "HS256", "typ": "JWT"}
    Payload: {"sub": username, "role": role, "exp": expiry_timestamp}
    """
    header = urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode()
    expiry = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS)
    payload_data = {
        "sub": username,
        "role": role,
        "exp": expiry.timestamp(),
    }
    payload = urlsafe_b64encode(json.dumps(payload_data).encode()).decode()

    # Sign with HMAC-SHA256
    message = f"{header}.{payload}".encode()
    signature = hmac.new(
        _TOKEN_SECRET.encode(), message, hashlib.sha256
    ).hexdigest()

    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> TokenPayload | None:
    """Verify and decode a token.

    Returns TokenPayload if valid, None if invalid/expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(
            _TOKEN_SECRET.encode(), message, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Decode payload
        payload_data = json.loads(urlsafe_b64decode(payload_b64 + "=="))

        # Check expiry
        if payload_data.get("exp", 0) < time.time():
            return None

        return TokenPayload(
            sub=payload_data["sub"],
            role=payload_data["role"],
            exp=payload_data["exp"],
        )
    except Exception:
        return None


# ── Dependency for protected routes ──────────────────────────────
async def require_auth(request: Request) -> TokenPayload:
    """FastAPI dependency: require valid authentication token.

    Reads token from Authorization header: "Bearer <token>"
    Raises 401 if missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Remove "Bearer " prefix
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_officer(token: TokenPayload = Depends(require_auth)) -> TokenPayload:
    """FastAPI dependency: require officer or admin role."""
    if token.role not in ("officer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions — officer role required",
        )
    return token


async def require_admin(token: TokenPayload = Depends(require_auth)) -> TokenPayload:
    """FastAPI dependency: require admin role."""
    if token.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions — admin role required",
        )
    return token


# ── Endpoints ────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate and receive a token.

    Demo users:
        - citizen / citizen123 (read-only public access)
        - officer / officer123 (read + command center)
        - admin / admin123 (full access)
    """
    user = DEMO_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_token(body.username, user["role"])
    expiry = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS)

    return LoginResponse(
        token=token,
        role=user["role"],
        display_name=user["display_name"],
        expires_at=expiry.isoformat(),
    )


@router.get("/me")
async def get_current_user(
    token: TokenPayload = Depends(require_auth),
) -> dict:
    """Get current authenticated user info."""
    expiry_dt = datetime.fromtimestamp(token.exp, tz=timezone.utc)
    return {
        "username": token.sub,
        "role": token.role,
        "expires_at": expiry_dt.isoformat(),
    }
