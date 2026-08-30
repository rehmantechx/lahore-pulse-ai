"""Test configuration and shared fixtures.

Provides reusable test infrastructure for all test modules.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.auth import TokenPayload, require_officer
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Settings configured for testing."""
    return Settings(
        environment="testing",
        log_level="DEBUG",
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def app(test_settings: Settings):
    """Create a FastAPI application configured for testing.

    Overrides auth dependency so POST endpoints requiring
    authentication work in tests without real tokens.
    """
    application = create_app(settings=test_settings)

    # Bypass auth for testing — all POST endpoints become callable
    def _mock_require_officer():
        return TokenPayload(sub="test-officer", role="officer", exp=9999999999.0)

    application.dependency_overrides[require_officer] = _mock_require_officer
    return application


@pytest.fixture
def client(app) -> TestClient:
    """Create a test client for the application."""
    return TestClient(app, raise_server_exceptions=False)
