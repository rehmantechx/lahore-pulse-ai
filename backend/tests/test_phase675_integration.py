"""Phase 6.75 — Current-data refresh & forecast status integration tests.

Tests the new endpoints and services added in Phase 6.75:
  - POST /api/v1/ingestion/refresh
  - GET  /api/v1/forecast/status (with freshness field)
  - IngestionService.ingest_current_weather / ingest_current_air_quality

Design:
    - Uses REAL database — no fabricated data.
    - Tests response STRUCTURE and status codes, not provider data
      (providers may be unreachable from CI/CD).
    - Uses FastAPI TestClient (synchronous) to avoid async pytest-asyncio issues.
    - Mocks provider HTTP calls to keep tests deterministic and fast.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import Settings
from app.modeling.serving.freshness import (
    FreshnessState,
    assess_freshness,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lahore_pulse.db"


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def app():
    """Create a FastAPI test app with real database."""
    from app.api.auth import TokenPayload, require_officer

    settings = Settings(
        database_url=f"sqlite:///{DB_PATH}",
        openaq_api_key="test-key",
        aqicn_api_token="test-token",
    )
    application = create_app(settings=settings)

    # Bypass auth for testing
    def _mock_require_officer():
        return TokenPayload(sub="test-officer", role="officer", exp=9999999999.0)

    application.dependency_overrides[require_officer] = _mock_require_officer
    return application


@pytest.fixture
def client(app):
    """Synchronous test client."""
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════
# 1. Forecast Status Endpoint — Freshness Integration
# ═══════════════════════════════════════════════════════════════════


class TestForecastStatusFreshness:
    """Verify /forecast/status includes freshness assessment."""

    def test_status_returns_200(self, client):
        """Status endpoint should return 200."""
        response = client.get("/api/v1/forecast/status")
        assert response.status_code == 200

    def test_status_includes_freshness_field(self, client):
        """Status response must include a 'freshness' field."""
        response = client.get("/api/v1/forecast/status")
        data = response.json()
        assert "freshness" in data, (
            f"Expected 'freshness' in response, got keys: {list(data.keys())}"
        )

    def test_freshness_has_required_fields(self, client):
        """Freshness object should have all required fields."""
        response = client.get("/api/v1/forecast/status")
        data = response.json()
        freshness = data["freshness"]

        assert "state" in freshness
        assert "freshness_hours" in freshness
        assert "latest_observation_at" in freshness
        assert "parameters_available" in freshness
        assert "warnings" in freshness

    def test_freshness_state_is_valid_enum(self, client):
        """Freshness state should be one of the four valid states."""
        response = client.get("/api/v1/forecast/status")
        data = response.json()
        state = data["freshness"]["state"]

        valid_states = {s.value for s in FreshnessState}
        assert state in valid_states, (
            f"Invalid freshness state: {state}. "
            f"Valid states: {valid_states}"
        )

    def test_freshness_warnings_is_list(self, client):
        """Warnings should always be a list."""
        response = client.get("/api/v1/forecast/status")
        data = response.json()
        assert isinstance(data["freshness"]["warnings"], list)

    def test_status_includes_ready_field(self, client):
        """Status response should include ready indicator."""
        response = client.get("/api/v1/forecast/status")
        data = response.json()
        assert "ready" in data


# ═══════════════════════════════════════════════════════════════════
# 2. Refresh Endpoint — Structure Tests
# ═══════════════════════════════════════════════════════════════════


class TestRefreshEndpointStructure:
    """Verify POST /ingestion/refresh returns correct structure.

    Uses mocked providers to keep tests fast and deterministic.
    """

    def _mock_provider_run(self, accepted=50, rejected=10):
        """Create a mock IngestionRun with given counts."""
        from app.domain.models.ingestion import (
            IngestionOperation,
            IngestionRun,
            IngestionStatus,
        )
        run = IngestionRun(operation=IngestionOperation.LIVE)
        run.finish(
            status=IngestionStatus.COMPLETED,
            accepted_records=accepted,
            rejected_records=rejected,
        )
        return run

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_returns_200(self, MockService, client):
        """Refresh endpoint should return 200 on success."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(50, 5)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(30, 2)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(20, 0)
        )
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        assert response.status_code == 200

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_has_correct_top_level_keys(self, MockService, client):
        """Refresh response should have status, providers, and summary."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(50, 5)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(30, 2)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(20, 0)
        )
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        data = response.json()

        assert "status" in data
        assert "providers" in data
        assert "summary" in data

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_summary_has_required_fields(self, MockService, client):
        """Summary should have total_accepted, total_rejected, providers_succeeded, providers_failed."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(50, 5)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(30, 2)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(20, 0)
        )
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        summary = response.json()["summary"]

        assert "total_accepted" in summary
        assert "total_rejected" in summary
        assert "providers_succeeded" in summary
        assert "providers_failed" in summary

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_providers_has_all_three(self, MockService, client):
        """Providers dict should include weather, air_quality, and aqicn_live."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(50, 5)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(30, 2)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(20, 0)
        )
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        providers = response.json()["providers"]

        assert "weather" in providers
        assert "air_quality" in providers
        assert "aqicn_live" in providers

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_calculates_correct_totals(self, MockService, client):
        """Summary totals should be correctly computed."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(accepted=100, rejected=10)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(accepted=50, rejected=5)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(accepted=30, rejected=0)
        )
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        summary = response.json()["summary"]

        assert summary["total_accepted"] == 180
        assert summary["total_rejected"] == 15
        assert summary["providers_succeeded"] == 3
        assert summary["providers_failed"] == 0

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_partial_status_on_failure(self, MockService, client):
        """When one provider fails, status should be 'partial'."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(accepted=50, rejected=5)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(accepted=30, rejected=2)
        )
        # Make AQICN fail
        failed_run = MagicMock()
        failed_run.run_id = "fail-123"
        failed_run.status.value = "failed"
        failed_run.accepted_records = 0
        failed_run.rejected_records = 0
        failed_run.total_records = 0
        mock_service.ingest_live_aqicn = AsyncMock(return_value=failed_run)
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        data = response.json()

        assert data["status"] == "partial"
        assert data["summary"]["providers_failed"] == 1
        assert data["providers"]["aqicn_live"]["status"] == "failed"

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_success_status_when_all_succeed(self, MockService, client):
        """When all providers succeed, status should be 'completed'."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(50, 0)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(30, 0)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(20, 0)
        )
        MockService.return_value = mock_service

        response = client.post("/api/v1/ingestion/refresh")
        data = response.json()

        assert data["status"] == "completed"
        assert data["summary"]["providers_failed"] == 0

    @patch("app.api.v1.ingestion.IngestionService")
    def test_refresh_accepts_query_params(self, MockService, client):
        """Refresh endpoint should accept latitude, longitude, forecast_days."""
        mock_service = AsyncMock()
        mock_service.ingest_current_weather = AsyncMock(
            return_value=self._mock_provider_run(50, 0)
        )
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=self._mock_provider_run(30, 0)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=self._mock_provider_run(20, 0)
        )
        MockService.return_value = mock_service

        response = client.post(
            "/api/v1/ingestion/refresh",
            params={"latitude": 31.55, "longitude": 74.35, "forecast_days": 5},
        )
        assert response.status_code == 200

        # Verify the provider methods were called with the custom params
        mock_service.ingest_current_weather.assert_called_once_with(
            provider=mock_service.ingest_current_weather.call_args[1]["provider"]
            if "provider" in mock_service.ingest_current_weather.call_args[1]
            else mock_service.ingest_current_weather.call_args[0][0],
            latitude=31.55,
            longitude=74.35,
            forecast_days=5,
            past_days=3,
        )


# ═══════════════════════════════════════════════════════════════════
# 3. Forecast Status — Full Response Shape
# ═══════════════════════════════════════════════════════════════════


class TestForecastStatusResponseShape:
    """Verify the complete shape of /forecast/status response."""

    def test_response_is_valid_json(self, client):
        """Response should be valid JSON."""
        response = client.get("/api/v1/forecast/status")
        assert "application/json" in response.headers["content-type"]

    def test_freshness_hours_is_numeric_or_none(self, client):
        """freshness_hours should be a number or None."""
        response = client.get("/api/v1/forecast/status")
        freshness = response.json()["freshness"]
        fh = freshness["freshness_hours"]
        assert fh is None or isinstance(fh, (int, float))

    def test_latest_observation_at_is_string_or_none(self, client):
        """latest_observation_at should be a string or None."""
        response = client.get("/api/v1/forecast/status")
        freshness = response.json()["freshness"]
        loa = freshness["latest_observation_at"]
        assert loa is None or isinstance(loa, str)

    def test_parameters_available_is_non_negative_int(self, client):
        """parameters_available should be a non-negative integer."""
        response = client.get("/api/v1/forecast/status")
        freshness = response.json()["freshness"]
        pa = freshness["parameters_available"]
        assert isinstance(pa, int)
        assert pa >= 0
