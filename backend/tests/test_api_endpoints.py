"""Tests for the v1 API endpoints.

Tests all REST endpoints using FastAPI's TestClient
and mocked database responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    def test_health(self, client: TestClient) -> None:
        """GET /api/v1/health returns status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_status_is_healthy(self, client: TestClient) -> None:
        """Health endpoint reports healthy status."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"


class TestDataSourcesEndpoints:
    """Tests for data sources listing endpoints."""

    def test_list_data_sources(self, client: TestClient) -> None:
        """GET /api/v1/data-sources returns all registered sources."""
        response = client.get("/api/v1/data-sources")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert data["count"] >= 3

    def test_data_source_has_required_fields(self, client: TestClient) -> None:
        """Each data source has required metadata fields."""
        response = client.get("/api/v1/data-sources")
        for source in response.json()["sources"]:
            assert "source_id" in source
            assert "name" in source
            assert "provider" in source
            assert "type" in source

    def test_get_data_source_found(self, client: TestClient) -> None:
        """GET /api/v1/data-sources/openmeteo returns the source."""
        response = client.get("/api/v1/data-sources/openmeteo")
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert data["source"]["source_id"] == "openmeteo"

    def test_get_data_source_not_found(self, client: TestClient) -> None:
        """GET /api/v1/data-sources/nonexistent returns error info."""
        response = client.get("/api/v1/data-sources/nonexistent")
        assert response.status_code == 200  # Returns error dict, not 404
        data = response.json()
        assert "error" in data


class TestObservationsEndpoints:
    """Tests for observations query endpoints."""

    @patch("app.api.v1.observations.get_database", new_callable=AsyncMock)
    def test_list_observations_empty(self, mock_get_db: MagicMock, client: TestClient) -> None:
        """GET /api/v1/observations returns empty list when no data."""
        mock_db = MagicMock()
        mock_db.fetch_one.return_value = {"count": 0}
        mock_db.fetch_all.return_value = []
        mock_get_db.return_value = mock_db

        response = client.get("/api/v1/observations")
        assert response.status_code == 200

    @patch("app.api.v1.observations.get_database", new_callable=AsyncMock)
    def test_observations_with_filters(self, mock_get_db: MagicMock, client: TestClient) -> None:
        """GET /api/v1/observations accepts query parameters."""
        mock_db = MagicMock()
        mock_db.fetch_one.return_value = {"count": 0}
        mock_db.fetch_all.return_value = []
        mock_get_db.return_value = mock_db

        response = client.get(
            "/api/v1/observations",
            params={"source_id": "openmeteo", "parameter": "temperature_2m"},
        )
        assert response.status_code == 200

    @patch("app.api.v1.observations.get_database", new_callable=AsyncMock)
    def test_observation_stats(self, mock_get_db: MagicMock, client: TestClient) -> None:
        """GET /api/v1/observations/stats returns aggregated stats."""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = [
            {"parameter": "pm25", "source_id": "openaq", "count": 100},
        ]
        mock_get_db.return_value = mock_db

        response = client.get("/api/v1/observations/stats")
        assert response.status_code == 200

    @patch("app.api.v1.observations.get_database", new_callable=AsyncMock)
    def test_get_observation_not_found(self, mock_get_db: MagicMock, client: TestClient) -> None:
        """GET /api/v1/observations/{id} returns 404 when not found."""
        mock_db = MagicMock()
        mock_db.fetch_one.return_value = None
        mock_get_db.return_value = mock_db

        response = client.get("/api/v1/observations/nonexistent-id")
        assert response.status_code == 404


class TestIngestionEndpoints:
    """Tests for ingestion trigger and run listing endpoints."""

    @patch("app.api.v1.ingestion.get_database", new_callable=AsyncMock)
    def test_list_ingestion_runs_empty(self, mock_get_db: MagicMock, client: TestClient) -> None:
        """GET /api/v1/ingestion/runs returns empty list when no runs."""
        mock_db = MagicMock()
        mock_db.fetch_all.return_value = []
        mock_get_db.return_value = mock_db

        response = client.get("/api/v1/ingestion/runs")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert data["runs"] == []

    @patch("app.api.v1.ingestion.get_database", new_callable=AsyncMock)
    def test_get_ingestion_run_not_found(
        self,
        mock_get_db: MagicMock,
        client: TestClient,
    ) -> None:
        """GET /api/v1/ingestion/runs/{id} returns 404 when not found."""
        mock_db = MagicMock()
        mock_db.fetch_one.return_value = None
        mock_get_db.return_value = mock_db

        response = client.get("/api/v1/ingestion/runs/nonexistent")
        assert response.status_code == 404

    @patch("app.api.v1.ingestion.IngestionService")
    @patch("app.api.v1.ingestion.get_database", new_callable=AsyncMock)
    @patch("app.api.v1.ingestion.get_settings")
    def test_trigger_weather_ingestion(
        self,
        mock_settings: MagicMock,
        mock_get_db: MagicMock,
        mock_service_cls: MagicMock,
        client: TestClient,
    ) -> None:
        """POST /api/v1/ingestion/runs/weather/historical triggers weather ingestion."""
        from app.domain.models.ingestion import IngestionOperation, IngestionRun, IngestionStatus

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # The endpoint creates IngestionService internally and calls its methods
        mock_service = AsyncMock()
        mock_run = IngestionRun(operation=IngestionOperation.HISTORICAL)
        mock_run.finish(status=IngestionStatus.COMPLETED, accepted_records=0, rejected_records=0)
        mock_service.ingest_historical_weather.return_value = mock_run
        mock_service_cls.return_value = mock_service

        response = client.post(
            "/api/v1/ingestion/runs/weather/historical",
            params={"start_date": "2024-01-01", "end_date": "2024-01-02"},
        )
        assert response.status_code == 200

    @patch("app.api.v1.ingestion.IngestionService")
    @patch("app.api.v1.ingestion.get_database", new_callable=AsyncMock)
    @patch("app.api.v1.ingestion.get_settings")
    def test_trigger_aq_ingestion(
        self,
        mock_settings: MagicMock,
        mock_get_db: MagicMock,
        mock_service_cls: MagicMock,
        client: TestClient,
    ) -> None:
        """POST /api/v1/ingestion/runs/aq/historical triggers AQ ingestion."""
        from app.domain.models.ingestion import IngestionOperation, IngestionRun, IngestionStatus

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_service = AsyncMock()
        mock_run = IngestionRun(operation=IngestionOperation.HISTORICAL)
        mock_run.finish(status=IngestionStatus.COMPLETED, accepted_records=0, rejected_records=0)
        mock_service.ingest_historical_aq.return_value = mock_run
        mock_service_cls.return_value = mock_service

        response = client.post(
            "/api/v1/ingestion/runs/aq/historical",
            params={"start_date": "2024-01-01", "end_date": "2024-01-02"},
        )
        assert response.status_code == 200

    @patch("app.api.v1.ingestion.IngestionService")
    @patch("app.api.v1.ingestion.get_database", new_callable=AsyncMock)
    @patch("app.api.v1.ingestion.get_settings")
    def test_trigger_aqicn_live_ingestion(
        self,
        mock_settings: MagicMock,
        mock_get_db: MagicMock,
        mock_service_cls: MagicMock,
        client: TestClient,
    ) -> None:
        """POST /api/v1/ingestion/runs/aq/live triggers live AQICN ingestion."""
        from app.domain.models.ingestion import IngestionOperation, IngestionRun, IngestionStatus

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_service = AsyncMock()
        mock_run = IngestionRun(operation=IngestionOperation.LIVE)
        mock_run.finish(status=IngestionStatus.COMPLETED, accepted_records=0, rejected_records=0)
        mock_service.ingest_live_aqicn.return_value = mock_run
        mock_service_cls.return_value = mock_service

        response = client.post("/api/v1/ingestion/runs/aq/live")
        assert response.status_code == 200


class TestAPIErrorHandling:
    """Tests for API error handling patterns."""

    def test_404_for_nonexistent_route(self, client: TestClient) -> None:
        """Non-existent routes return 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
