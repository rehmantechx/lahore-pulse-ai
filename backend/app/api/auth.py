"""Authentication endpoints.

Provides role-based authentication for hackathon demo.
Uses HMAC-SHA256 tokens with role-based access control.

Roles:
    - citizen: Read-only access to public data
    - officer: Read + command center access
    - admin: Full access including ingestion control

Security:
    - Passwords are bcrypt-hashed (never stored in plaintext)
    - JWT secret is required in production via LPA_AUTH_SECRET
    - Tokens encode role and expiry, signed with HMAC-SHA256
    - Login endpoint is rate-limited to prevent brute-force attacks
"""

from __future__ import annotations

import collections
import hashlib
import hmac
import json
import os
import secrets
import time
import warnings
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from pydantic import BaseModel, Field

from ..core.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Token Configuration ──────────────────────────────────────────
# Secret key for HMAC signing — REQUIRED in production
settings = get_settings()

_TOKEN_EXPIRY_HOURS = 24  # Tokens expire after 24 hours

# Default secret for development only — must never be used in production
_DEV_SECRET_DEFAULT = "lahore-plus-hackathon-dev-only-not-for-production"

if settings.is_production:
    _raw_secret = os.environ.get("LPA_AUTH_SECRET", "")
    if not _raw_secret:
        raise RuntimeError(
            "FATAL: LPA_AUTH_SECRET environment variable must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    if _raw_secret == _DEV_SECRET_DEFAULT:
        raise RuntimeError(
            "FATAL: LPA_AUTH_SECRET is still the development default. "
            "Set it to a unique random value for production."
        )
    if len(_raw_secret) < 32:
        raise RuntimeError(
            "FATAL: LPA_AUTH_SECRET must be at least 32 characters for security."
        )
    _TOKEN_SECRET = _raw_secret
    logger.info("Production JWT secret loaded from environment")
else:
    _TOKEN_SECRET = os.environ.get("LPA_AUTH_SECRET", _DEV_SECRET_DEFAULT)
    if _TOKEN_SECRET == _DEV_SECRET_DEFAULT:
        logger.warning(
            "Using development LPA_AUTH_SECRET — set a real secret for production!"
        )


# ── Demo Users (bcrypt-hashed passwords) ─────────────────────────
# Passwords are hashed at module load time with bcrypt.
# Plaintext values are never stored or logged.
_DEMO_PASSWORD_HASHES = {
    "citizen": bcrypt.hashpw(b"citizen123", bcrypt.gensalt()),
    "officer": bcrypt.hashpw(b"officer123", bcrypt.gensalt()),
    "admin": bcrypt.hashpw(b"admin123", bcrypt.gensalt()),
}

DEMO_USERS = {
    "citizen": {
        "password_hash": _DEMO_PASSWORD_HASHES["citizen"],
        "role": "citizen",
        "display_name": "Public Citizen",
    },
    "officer": {
        "password_hash": _DEMO_PASSWORD_HASHES["officer"],
        "role": "officer",
        "display_name": "Air Quality Officer",
    },
    "admin": {
        "password_hash": _DEMO_PASSWORD_HASHES["admin"],
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


# ── Login Rate Limiting ──────────────────────────────────────────
# In-memory rate limiter for login attempts.
# Tracks attempts per IP address with a sliding window.
_LOGIN_RATE_LIMIT = 10  # max attempts per window
_LOGIN_RATE_WINDOW_SECONDS = 300  # 5-minute window
_login_attempts: dict[str, list[float]] = collections.defaultdict(list)


def _check_login_rate_limit(ip: str) -> None:
    """Check if an IP has exceeded the login rate limit.

    Raises 429 Too Many Requests if limit exceeded.
    Cleans up old entries outside the window.
    """
    now = time.time()
    cutoff = now - _LOGIN_RATE_WINDOW_SECONDS

    # Clean old entries
    _login_attempts[ip] = [
        t for t in _login_attempts[ip] if t > cutoff
    ]

    if len(_login_attempts[ip]) >= _LOGIN_RATE_LIMIT:
        logger.warning("Login rate limit exceeded", ip=ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    _login_attempts[ip].append(now)


# ── Endpoints ────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    """Authenticate and receive a token.

    Rate-limited to prevent brute-force attacks.
    """
    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)

    user = DEMO_USERS.get(body.username)
    if not user or not bcrypt.checkpw(body.password.encode(), user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_token(body.username, user["role"])
    expiry = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS)

    # Clear rate limit on successful login
    _login_attempts.pop(client_ip, None)

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
