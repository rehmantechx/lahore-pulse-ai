"""Tests for health and readiness endpoints.

Verifies that:
- Health endpoint returns correct status
- Readiness endpoint reports actual component states
- No endpoint falsely claims unconfigured components are operational
- Database path resolution respects LPA_DATABASE_URL configuration
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.api.v1.health import _resolve_db_path


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


class TestDatabasePathResolution:
    """Tests for _resolve_db_path() — verifies LPA_DATABASE_URL is respected."""

    def test_default_relative_path_resolves_to_backend_dir(self) -> None:
        """Default sqlite:///data/lahore_pulse.db resolves against backend/."""
        with patch("app.api.v1.health.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "sqlite:///data/lahore_pulse.db"
            result = _resolve_db_path()
            assert result.name == "lahore_pulse.db"
            assert "backend" in str(result)
            # Must NOT be the bare relative path
            assert result.is_absolute()

    def test_absolute_path_passes_through(self) -> None:
        """Absolute path like /data/lahore_pulse.db is not modified.

        On Windows, Path('/data/...') resolves to C:/data/... — that's fine.
        The key assertion is that the path is NOT prepended with backend/.
        """
        with patch("app.api.v1.health.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "sqlite:////data/lahore_pulse.db"
            result = _resolve_db_path()
            # Must NOT contain 'backend' in the path (relative resolution not applied)
            assert "backend" not in str(result)
            assert result.name == "lahore_pulse.db"

    def test_readiness_uses_configured_absolute_path(self, client) -> None:
        """Readiness must not report 'not_configured' for an existing absolute DB."""
        import sqlite3
        import tempfile
        import os

        # Create a temporary SQLite database with the expected schema
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            conn = sqlite3.connect(tmp_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    station_id TEXT,
                    parameter TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    quality_status TEXT NOT NULL DEFAULT 'unverified',
                    observation_type TEXT NOT NULL DEFAULT 'observation',
                    source_identifier TEXT,
                    raw_response TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_records (
                    prediction_id TEXT PRIMARY KEY,
                    model_version TEXT,
                    horizon_hours INTEGER,
                    predicted_at TEXT,
                    target_at TEXT,
                    predicted_value REAL,
                    actual_value REAL,
                    error REAL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.commit()
            conn.close()

            # Patch settings to point to the temp database
            with patch("app.api.v1.health.get_settings") as mock_settings:
                mock_settings.return_value.database_url = f"sqlite:///{tmp_path}"

                from app.api.v1.health import _refresh_readiness_cache
                # Clear cache to force fresh computation
                import app.api.v1.health as health_mod
                health_mod._READINESS_CACHE = None

                result = _refresh_readiness_cache()
                db_status = result["components"]["database"]["status"]
                assert db_status == "available", (
                    f"Expected 'available' for existing temp DB at {tmp_path}, "
                    f"got '{db_status}'"
                )
        finally:
            os.unlink(tmp_path)

    def test_readinessReportsNotConfigured_for_missing_path(self) -> None:
        """Readiness correctly reports not_configured when DB file does not exist."""
        with patch("app.api.v1.health.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "sqlite:///nonexistent/path/test.db"

            import app.api.v1.health as health_mod
            health_mod._READINESS_CACHE = None

            from app.api.v1.health import _refresh_readiness_cache
            result = _refresh_readiness_cache()
            db_status = result["components"]["database"]["status"]
            assert db_status == "not_configured"
