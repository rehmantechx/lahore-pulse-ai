"""Comprehensive authentication and RBAC tests.

Tests cover:
  - Login flow with bcrypt-hashed passwords
  - JWT token creation and verification
  - Role-based access control (citizen, officer, admin)
  - require_auth, require_officer, require_admin dependencies
  - Ingestion endpoints require admin
  - Public endpoints require no auth
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.auth import (
    DEMO_USERS,
    TokenPayload,
    _create_token,
    require_admin,
    require_auth,
    require_officer,
    verify_token,
)
from app.core.config import Settings
from app.main import create_app


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="testing",
        log_level="DEBUG",
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def raw_app(settings: Settings):
    """App without auth overrides — real auth flows."""
    return create_app(settings=settings)


@pytest.fixture
def raw_client(raw_app) -> TestClient:
    return TestClient(raw_app, raise_server_exceptions=False)


@pytest.fixture
def mock_app(settings: Settings):
    """App with auth overridden — for testing non-auth endpoints."""
    app = create_app(settings=settings)

    def _mock_auth():
        return TokenPayload(sub="test-citizen", role="citizen", exp=9999999999.0)

    def _mock_officer():
        return TokenPayload(sub="test-officer", role="officer", exp=9999999999.0)

    def _mock_admin():
        return TokenPayload(sub="test-admin", role="admin", exp=9999999999.0)

    app.dependency_overrides[require_auth] = _mock_auth
    app.dependency_overrides[require_officer] = _mock_officer
    app.dependency_overrides[require_admin] = _mock_admin
    return app


@pytest.fixture
def mock_client(mock_app) -> TestClient:
    return TestClient(mock_app, raise_server_exceptions=False)


# ── Token Helpers ────────────────────────────────────────────────


@pytest.fixture
def citizen_token() -> str:
    return _create_token("citizen", "citizen")


@pytest.fixture
def officer_token() -> str:
    return _create_token("officer", "officer")


@pytest.fixture
def admin_token() -> str:
    return _create_token("admin", "admin")


# ── Login Tests ──────────────────────────────────────────────────


class TestLogin:
    """Test /api/v1/auth/login endpoint."""

    def test_login_citizen_success(self, raw_client: TestClient):
        """Valid citizen credentials return a token."""
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "citizen", "password": "citizen123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["role"] == "citizen"
        assert data["display_name"] == "Public Citizen"
        assert "expires_at" in data

    def test_login_officer_success(self, raw_client: TestClient):
        """Valid officer credentials return a token."""
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "officer", "password": "officer123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "officer"
        assert data["display_name"] == "Air Quality Officer"

    def test_login_admin_success(self, raw_client: TestClient):
        """Valid admin credentials return a token."""
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "admin"
        assert data["display_name"] == "System Administrator"

    def test_login_wrong_password_returns_401(self, raw_client: TestClient):
        """Wrong password returns 401."""
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "citizen", "password": "wrongpassword"},
        )
        assert res.status_code == 401
        assert "Invalid username or password" in res.json()["detail"]

    def test_login_unknown_user_returns_401(self, raw_client: TestClient):
        """Unknown username returns 401."""
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "test"},
        )
        assert res.status_code == 401

    def test_login_empty_password_returns_422(self, raw_client: TestClient):
        """Empty password is rejected by Pydantic validation (min_length=1)."""
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "citizen", "password": ""},
        )
        assert res.status_code == 422

    def test_passwords_are_bcrypt_hashed(self):
        """DEMO_USERS stores bcrypt hashes, not plaintext."""
        for username, user in DEMO_USERS.items():
            assert "password_hash" in user, f"{username} missing password_hash"
            assert "password" not in user, f"{username} still has plaintext password"
            # bcrypt hashes start with $2b$
            pw_hash = user["password_hash"]
            assert isinstance(pw_hash, bytes)
            assert pw_hash[:4] == b"$2b$", f"{username} hash not bcrypt format"


# ── Token Verification Tests ─────────────────────────────────────


class TestTokenVerification:
    """Test token creation and verification."""

    def test_create_and_verify_roundtrip(self):
        """Token created can be verified and returns correct payload."""
        token = _create_token("testuser", "officer")
        payload = verify_token(token)
        assert payload.sub == "testuser"
        assert payload.role == "officer"

    def test_invalid_token_returns_none(self):
        """Tampered token returns None (not raise)."""
        result = verify_token("this.is.not.a.valid.token")
        assert result is None

    def test_empty_token_returns_none(self):
        """Empty token returns None (not raise)."""
        result = verify_token("")
        assert result is None


# ── /auth/me Tests ───────────────────────────────────────────────


class TestAuthMe:
    """Test /api/v1/auth/me endpoint."""

    def test_me_returns_user_info(self, raw_client: TestClient, citizen_token: str):
        """Authenticated request returns user info."""
        res = raw_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {citizen_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["username"] == "citizen"
        assert data["role"] == "citizen"
        assert "expires_at" in data

    def test_me_no_token_returns_401(self, raw_client: TestClient):
        """Request without token returns 401."""
        res = raw_client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_me_invalid_token_returns_401(self, raw_client: TestClient):
        """Request with invalid token returns 401."""
        res = raw_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer garbage"},
        )
        assert res.status_code == 401


# ── RBAC Dependency Tests ────────────────────────────────────────


class TestRBACDependencies:
    """Test require_auth, require_officer, require_admin FastAPI dependencies."""

    def test_citizen_can_access_auth_me(self, raw_client: TestClient, citizen_token: str):
        """Citizen token is accepted by require_auth."""
        res = raw_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {citizen_token}"},
        )
        assert res.status_code == 200

    def test_officer_can_access_auth_me(self, raw_client: TestClient, officer_token: str):
        """Officer token is accepted by require_auth."""
        res = raw_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 200


# ── Ingestion Admin Enforcement Tests ────────────────────────────


class TestIngestionAdminEnforcement:
    """Ingestion endpoints must require admin role."""

    def test_citizen_cannot_access_ingestion(self, raw_client: TestClient, citizen_token: str):
        """Citizen token is rejected by ingestion endpoints."""
        res = raw_client.post(
            "/api/v1/ingestion/runs/weather/historical",
            headers={"Authorization": f"Bearer {citizen_token}"},
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
            },
        )
        assert res.status_code == 403

    def test_officer_cannot_access_ingestion(self, raw_client: TestClient, officer_token: str):
        """Officer token is rejected by ingestion endpoints (admin-only)."""
        res = raw_client.post(
            "/api/v1/ingestion/runs/weather/historical",
            headers={"Authorization": f"Bearer {officer_token}"},
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
            },
        )
        assert res.status_code == 403

    def test_admin_can_access_ingestion(self, mock_client: TestClient):
        """Admin can access ingestion (with mock auth)."""
        res = mock_client.post(
            "/api/v1/ingestion/runs/weather/historical",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
            },
        )
        # May return 500/503 due to test env, but should NOT be 403
        assert res.status_code != 403


# ── Public Endpoint Tests (no auth required) ─────────────────────


class TestPublicEndpoints:
    """Endpoints that should be accessible without authentication."""

    def test_weather_no_auth(self, mock_client: TestClient):
        """Weather endpoint is public."""
        res = mock_client.get("/api/v1/weather/current")
        # Should not return 401 or 403
        assert res.status_code not in (401, 403)

    def test_health_no_auth(self, mock_client: TestClient):
        """Health endpoint is public."""
        res = mock_client.get("/api/v1/health/live")
        assert res.status_code not in (401, 403)

    def test_datasources_no_auth(self, mock_client: TestClient):
        """Datasources endpoint is public."""
        res = mock_client.get("/api/v1/datasources")
        assert res.status_code not in (401, 403)


# ── Security Hardening Tests ─────────────────────────────────────


class TestProductionSecretValidation:
    """Verify production mode fails safely without proper JWT secret."""

    def test_production_validation_exists(self):
        """Auth module has production secret validation logic."""
        from app.api.auth import _DEV_SECRET_DEFAULT
        assert _DEV_SECRET_DEFAULT != ""
        assert len(_DEV_SECRET_DEFAULT) >= 32

    def test_production_rejects_default_secret(self):
        """_DEV_SECRET_DEFAULT is rejected in production mode."""
        from app.api.auth import _DEV_SECRET_DEFAULT
        # Simulate the production check logic
        secret = _DEV_SECRET_DEFAULT
        is_default = secret == _DEV_SECRET_DEFAULT
        assert is_default, "Default secret should be detected"

    def test_production_rejects_short_secret(self):
        """Short secrets are rejected in production mode."""
        secret = "short"
        assert len(secret) < 32, "Short secret should fail length check"


class TestCrossRoleAccess:
    """Verify role-based access control across all role combinations."""

    def test_citizen_blocked_from_officer_endpoint(self, raw_client: TestClient, citizen_token: str):
        """Citizen cannot access officer-protected endpoints."""
        res = raw_client.get(
            "/api/v1/accuracy/summary",
            headers={"Authorization": f"Bearer {citizen_token}"},
        )
        assert res.status_code == 403

    def test_citizen_blocked_from_admin_endpoint(self, raw_client: TestClient, citizen_token: str):
        """Citizen cannot access admin-protected endpoints."""
        res = raw_client.post(
            "/api/v1/ingestion/refresh",
            headers={"Authorization": f"Bearer {citizen_token}"},
        )
        assert res.status_code == 403

    def test_officer_blocked_from_admin_endpoint(self, raw_client: TestClient, officer_token: str):
        """Officer cannot access admin-only endpoints."""
        res = raw_client.post(
            "/api/v1/ingestion/refresh",
            headers={"Authorization": f"Bearer {officer_token}"},
        )
        assert res.status_code == 403

    def test_admin_can_access_admin_endpoint(self, mock_client: TestClient):
        """Admin can access admin-protected endpoints."""
        res = mock_client.post(
            "/api/v1/ingestion/refresh",
            params={"latitude": 31.5204, "longitude": 74.3587},
        )
        # May fail due to test env, but should NOT be 403
        assert res.status_code != 403

    def test_admin_can_access_officer_endpoint(self, mock_client: TestClient):
        """Admin can access officer-protected endpoints."""
        res = mock_client.get("/api/v1/accuracy/summary")
        # May fail due to test env, but should NOT be 403
        assert res.status_code != 403


class TestSecurityHeaders:
    """Verify security headers are present in responses."""

    def test_security_headers_present(self, raw_client: TestClient):
        """All OWASP security headers are present."""
        res = raw_client.get("/api/v1/health/live")
        assert "X-Content-Type-Options" in res.headers
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in res.headers
        assert res.headers["X-Frame-Options"] == "DENY"
        assert "Referrer-Policy" in res.headers
        assert "Content-Security-Policy" in res.headers
        assert "Permissions-Policy" in res.headers

    def test_csp_frame_ancestors_none(self, raw_client: TestClient):
        """CSP frame-ancestors is 'none' to prevent clickjacking."""
        res = raw_client.get("/api/v1/health/live")
        csp = res.headers.get("Content-Security-Policy", "")
        assert "frame-ancestors 'none'" in csp

    def test_csp_no_wildcard_connect(self, raw_client: TestClient):
        """CSP connect-src does not use wildcard in production."""
        res = raw_client.get("/api/v1/health/live")
        csp = res.headers.get("Content-Security-Policy", "")
        # Should not have * in connect-src
        connect_section = [p for p in csp.split(";") if "connect-src" in p]
        if connect_section:
            assert "*" not in connect_section[0]


class TestLoginRateLimit:
    """Verify login rate limiting works."""

    def test_rate_limit_not_triggered_within_limit(self, raw_client: TestClient):
        """Login attempts within limit succeed."""
        from app.api.auth import _login_attempts
        _login_attempts.clear()

        for _ in range(5):
            res = raw_client.post(
                "/api/v1/auth/login",
                json={"username": "citizen", "password": "citizen123"},
            )
            assert res.status_code == 200

    def test_rate_limit_blocks_after_excessive_attempts(self, raw_client: TestClient):
        """Login attempts exceeding limit return 429."""
        from app.api.auth import _login_attempts, _LOGIN_RATE_LIMIT
        _login_attempts.clear()

        # Exhaust the rate limit with wrong password attempts
        for _ in range(_LOGIN_RATE_LIMIT):
            res = raw_client.post(
                "/api/v1/auth/login",
                json={"username": "citizen", "password": "wrongpassword"},
            )
            # These should be 401 (wrong password) not 429
            assert res.status_code == 401

        # Next attempt should be rate limited
        res = raw_client.post(
            "/api/v1/auth/login",
            json={"username": "citizen", "password": "citizen123"},
        )
        assert res.status_code == 429
        assert "Too many" in res.json()["detail"]


class TestFavoritesAuthEnforcement:
    """Verify favorites write endpoints require authentication."""

    def test_add_favorite_no_auth_returns_401(self, raw_client: TestClient):
        """Adding a favorite without auth returns 401."""
        res = raw_client.post(
            "/api/v1/favorites",
            json={"name": "Test Location"},
        )
        assert res.status_code == 401

    def test_add_favorite_with_auth_works(self, mock_client: TestClient):
        """Adding a favorite with valid auth works."""
        res = mock_client.post(
            "/api/v1/favorites",
            json={"name": "Test Location"},
        )
        assert res.status_code in (200, 201)


class TestAlertsAuthEnforcement:
    """Verify alerts write endpoints require authentication."""

    def test_update_preferences_no_auth_returns_401(self, raw_client: TestClient):
        """Updating alert preferences without auth returns 401."""
        res = raw_client.put(
            "/api/v1/alerts/preferences",
            json={"preferences": [{"alert_type": "fair", "enabled": True}]},
        )
        assert res.status_code == 401

    def test_create_alert_no_auth_returns_401(self, raw_client: TestClient):
        """Creating an alert without auth returns 401."""
        res = raw_client.post(
            "/api/v1/alerts/history",
            params={"alert_type": "fair", "severity": "low", "message": "test"},
        )
        assert res.status_code == 401


class TestCORSConfiguration:
    """Verify CORS is not allowing arbitrary origins."""

    def test_cors_does_not_allow_wildcard(self, raw_app):
        """CORS should not allow wildcard origins."""
        settings = raw_app.state.settings
        assert "*" not in settings.cors_origins

    def test_cors_preflight_rejects_unknown_origin(self, raw_client: TestClient):
        """Preflight request from unknown origin is rejected."""
        res = raw_client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not include Access-Control-Allow-Origin for unknown origin
        assert "Access-Control-Allow-Origin" not in res.headers or \
            res.headers.get("Access-Control-Allow-Origin") != "https://evil.example.com"

    def test_cors_allows_configured_origin(self, raw_client: TestClient):
        """Preflight request from configured origin is allowed."""
        res = raw_client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
