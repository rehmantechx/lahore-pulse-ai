"""Tests for health and readiness endpoints.

Verifies that:
- Health endpoint returns correct status
- Readiness endpoint reports actual component states
- No endpoint falsely claims unconfigured components are operational
"""

from __future__ import annotations


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    def test_health_returns_200(self, client) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_status_is_healthy(self, client) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_service_name(self, client) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["service"] == "lahore-pulse-ai"

    def test_health_includes_version(self, client) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_health_includes_timestamp(self, client) -> None:
        response = client.get("/api/v1/health")
        data = response.json()
        assert "timestamp" in data
        # Timestamp should be an ISO format string
        assert "T" in data["timestamp"]


class TestReadinessEndpoint:
    """Tests for GET /api/v1/readiness."""

    def test_readiness_returns_200(self, client) -> None:
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200

    def test_readiness_status_is_ready(self, client) -> None:
        response = client.get("/api/v1/readiness")
        data = response.json()
        assert data["status"] == "ready"

    def test_readiness_includes_components(self, client) -> None:
        response = client.get("/api/v1/readiness")
        data = response.json()
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_readiness_api_is_operational(self, client) -> None:
        """The API itself should be operational since we're responding."""
        response = client.get("/api/v1/readiness")
        data = response.json()
        assert data["components"]["api"]["status"] == "operational"

    def test_readiness_database_reports_actual_state(self, client) -> None:
        """Database component should report actual state."""
        response = client.get("/api/v1/readiness")
        data = response.json()
        db = data["components"]["database"]
        assert db["status"] in ("not_configured", "available", "degraded")

    def test_readiness_forecast_models_reports_actual_state(self, client) -> None:
        """Forecast models status reflects actual disk state.

        Phase 0-4: models not yet trained → 'not_configured'.
        Phase 5+:  models trained and on disk → 'available'.
        """
        response = client.get("/api/v1/readiness")
        data = response.json()
        forecasts = data["components"]["forecast_models"]
        assert forecasts["status"] in ("not_configured", "available")

    def test_readiness_data_freshness_reports_actual_state(self, client) -> None:
        """Data freshness should report actual state."""
        response = client.get("/api/v1/readiness")
        data = response.json()
        freshness = data["components"]["data_freshness"]
        assert "state" in freshness

    def test_readiness_prediction_accountability_reports_state(self, client) -> None:
        """Prediction accountability should report actual state."""
        response = client.get("/api/v1/readiness")
        data = response.json()
        pred = data["components"]["prediction_accountability"]
        assert "status" in pred


class TestNotFound:
    """Tests for proper 404 handling."""

    def test_nonexistent_endpoint_returns_404(self, client) -> None:
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_404_response_has_error_structure(self, client) -> None:
        response = client.get("/api/v1/nonexistent")
        data = response.json()
        assert "detail" in data
