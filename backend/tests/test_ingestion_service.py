"""Tests for the data ingestion orchestration service.

Tests the IngestionService pipeline orchestration with mocked
providers and database. Tests the full flow from provider fetch
through pipeline processing to database storage.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.ingestion import IngestionService
from app.core.config import Settings
from app.domain.models.ingestion import IngestionOperation, IngestionStatus
from app.infrastructure.database import Database


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock database."""
    db = MagicMock(spec=Database)
    db.execute = MagicMock()
    db.commit = MagicMock()
    db.fetch_all = MagicMock(return_value=[])
    db.fetch_one = MagicMock(return_value=None)
    db.table_row_count = MagicMock(return_value=0)
    return db


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        database_url="sqlite:///:memory:",
        openaq_api_key="test-key",
        aqicn_api_token="test-token",
    )


@pytest.fixture
def ingestion_service(settings: Settings, mock_db: MagicMock) -> IngestionService:
    """Create IngestionService with mocked dependencies."""
    return IngestionService(settings=settings, db=mock_db)


class TestIngestionServiceInit:
    """Tests for IngestionService initialization."""

    def test_creates_service(self, ingestion_service: IngestionService) -> None:
        """IngestionService can be instantiated."""
        assert ingestion_service is not None

    def test_has_required_methods(self, ingestion_service: IngestionService) -> None:
        """Service exposes all required public methods."""
        assert hasattr(ingestion_service, "ingest_historical_weather")
        assert hasattr(ingestion_service, "ingest_historical_aq")
        assert hasattr(ingestion_service, "ingest_live_aqicn")


class TestIngestionRunCreation:
    """Tests for ingestion run lifecycle."""

    @pytest.mark.asyncio
    async def test_creates_run_record(self, ingestion_service: IngestionService) -> None:
        """Ingestion creates a run record in the database."""
        mock_provider = AsyncMock()
        mock_provider.fetch_historical = AsyncMock(return_value={})
        mock_provider.parse_historical_response = MagicMock(return_value=[])

        run = await ingestion_service.ingest_historical_weather(
            provider=mock_provider,
            latitude=31.5204,
            longitude=74.3587,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )

        # Verify run INSERT was called
        assert ingestion_service._db.execute.call_count >= 1
        first_call_args = ingestion_service._db.execute.call_args_list[0]
        assert "INSERT INTO ingestion_runs" in first_call_args[0][0]
        assert run.operation == IngestionOperation.HISTORICAL

    @pytest.mark.asyncio
    async def test_updates_run_status_on_completion(
        self,
        ingestion_service: IngestionService,
    ) -> None:
        """Run status is updated to completed after processing."""
        mock_provider = AsyncMock()
        mock_provider.fetch_historical = AsyncMock(return_value={})
        mock_provider.parse_historical_response = MagicMock(return_value=[])

        run = await ingestion_service.ingest_historical_weather(
            provider=mock_provider,
            latitude=31.5204,
            longitude=74.3587,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )

        # Verify at least one UPDATE call was made
        update_calls = [
            c
            for c in ingestion_service._db.execute.call_args_list
            if "UPDATE ingestion_runs" in c[0][0]
        ]
        assert len(update_calls) >= 1
        assert run.status in (IngestionStatus.COMPLETED, IngestionStatus.PARTIAL)


class TestIngestionWeatherFlow:
    """Tests for weather data ingestion flow."""

    @pytest.mark.asyncio
    async def test_empty_response_records_zero(
        self,
        ingestion_service: IngestionService,
    ) -> None:
        """Empty provider response records zero accepted."""
        mock_provider = AsyncMock()
        mock_provider.fetch_historical = AsyncMock(return_value={})
        mock_provider.parse_historical_response = MagicMock(return_value=[])

        run = await ingestion_service.ingest_historical_weather(
            provider=mock_provider,
            latitude=31.5204,
            longitude=74.3587,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )

        assert run.total_records == 0

    @pytest.mark.asyncio
    async def test_provider_called_with_correct_args(
        self,
        ingestion_service: IngestionService,
    ) -> None:
        """Provider fetch is called with correct arguments."""
        mock_provider = AsyncMock()
        mock_provider.fetch_historical = AsyncMock(return_value={})
        mock_provider.parse_historical_response = MagicMock(return_value=[])

        await ingestion_service.ingest_historical_weather(
            provider=mock_provider,
            latitude=31.5204,
            longitude=74.3587,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )

        mock_provider.fetch_historical.assert_called_once_with(
            latitude=31.5204,
            longitude=74.3587,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )


class TestIngestionLiveAQFlow:
    """Tests for live AQICN data ingestion flow."""

    @pytest.mark.asyncio
    async def test_live_ingestion_creates_run(
        self,
        ingestion_service: IngestionService,
    ) -> None:
        """Live ingestion creates a run with LIVE operation."""
        mock_provider = AsyncMock()
        mock_provider.fetch_lahore_stations = AsyncMock(return_value=[])
        mock_provider.parse_station_response = MagicMock(return_value=[])

        run = await ingestion_service.ingest_live_aqicn(provider=mock_provider)

        # Verify INSERT INTO ingestion_runs was called with 'live' operation
        insert_calls = [
            c
            for c in ingestion_service._db.execute.call_args_list
            if "INSERT INTO ingestion_runs" in c[0][0]
        ]
        assert len(insert_calls) == 1
        # The values should include 'live' operation
        call_args = insert_calls[0][0][1]
        assert call_args[1] == "live"
        assert run.operation == IngestionOperation.LIVE


class TestErrorHandling:
    """Tests for error handling in ingestion."""

    @pytest.mark.asyncio
    async def test_provider_failure_marks_run_failed(
        self,
        ingestion_service: IngestionService,
    ) -> None:
        """Provider exception marks the run as FAILED in-memory."""
        mock_provider = AsyncMock()
        mock_provider.fetch_historical = AsyncMock(
            side_effect=Exception("Connection timeout"),
        )

        run = await ingestion_service.ingest_historical_weather(
            provider=mock_provider,
            latitude=31.5204,
            longitude=74.3587,
            start_date="2024-01-01",
            end_date="2024-01-02",
        )

        assert run.status == IngestionStatus.FAILED
        # Provider failed before run was inserted into DB,
        # so no UPDATE calls are expected — only in-memory status is set.
        assert run.accepted_records == 0
        assert run.rejected_records == 0
