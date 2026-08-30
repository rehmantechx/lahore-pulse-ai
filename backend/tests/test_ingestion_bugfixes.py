"""Regression tests for Bug A (stuck forecasts) and Bug B (dead auto-refresh).

Bug A: Forecast records whose observed_at has passed must be reclassified
       to 'observation' both at startup (batch) and during ingestion (live).

Bug B: The auto-refresh background task must use the correct IngestionService
       constructor and call real public methods.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.database import Database


# ── Helpers ──────────────────────────────────────────────────────────────

# Required data_sources rows for FK compliance
_SEED_SOURCES = [
    ("openmeteo", "Open-Meteo", "Open-Meteo GmbH", "weather"),
    ("openaq", "OpenAQ", "OpenAQ", "air_quality"),
    ("aqicn", "WAQI", "WAQI Project", "air_quality"),
]


def _seed_data_sources(db: Database) -> None:
    """Insert required data_sources rows for FK compliance."""
    for source_id, name, provider, stype in _SEED_SOURCES:
        db.execute(
            """INSERT OR IGNORE INTO data_sources (source_id, name, provider, source_type)
               VALUES (?, ?, ?, ?)""",
            (source_id, name, provider, stype),
        )
    db.commit()


def _gen_obs_id(source_id: str, station_id: str | None, parameter: str, observed_at: str) -> str:
    """Generate deterministic observation ID (mirrors pipeline.py)."""
    key = f"{source_id}|{station_id or ''}|{parameter}|{observed_at}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    return str(uuid.UUID(bytes=hash_bytes[:16], version=5))


def _insert_observation(
    db: Database,
    observation_id: str,
    observation_type: str = "observation",
    observed_at: str = "2026-01-01T00:00:00+00:00",
    retrieved_at: str = "2026-01-01T01:00:00+00:00",
    value: float = 50.0,
) -> None:
    """Insert a raw observation row for testing."""
    db.execute(
        """INSERT OR IGNORE INTO observations
           (observation_id, source_id, station_id, parameter, value, unit,
            observed_at, retrieved_at, latitude, longitude, quality_status,
            observation_type, source_identifier, raw_response, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            observation_id,
            "openmeteo",
            None,
            "pm2_5",
            value,
            "ug/m3",
            observed_at,
            retrieved_at,
            31.52,
            74.36,
            "valid",
            observation_type,
            "",
            "",
            retrieved_at,
        ),
    )
    db.commit()


# ══════════════════════════════════════════════════════════════════════════
# FIX 1: Batch Reclassification Tests (database.py _migrate)
# ══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create a temporary database for testing with FK-seeded data_sources."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    db.initialize()
    _seed_data_sources(db)
    yield db
    db.close()


class TestBatchReclassification:
    """Tests for Migration 2: stale forecast -> observation reclassification."""

    def test_stale_forecast_reclassified_on_initialize(self, temp_db: Database) -> None:
        """Forecast with observed_at in the past is reclassified on startup."""
        now = datetime.now(UTC)
        past = (now - timedelta(hours=2)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", past)

        _insert_observation(temp_db, obs_id, "forecast", past, past)
        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "forecast"

        # Re-initialize triggers _migrate which runs reclassification
        temp_db.initialize()

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "observation"

    def test_idempotent_reclassification(self, temp_db: Database) -> None:
        """Running reclassification twice changes nothing the second time."""
        now = datetime.now(UTC)
        past = (now - timedelta(hours=3)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", past)

        _insert_observation(temp_db, obs_id, "forecast", past, past)
        temp_db.initialize()

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "observation"

        # Second initialization — no error, still observation
        temp_db.initialize()
        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "observation"

    def test_future_forecast_not_reclassified(self, temp_db: Database) -> None:
        """Forecast with observed_at still in the future stays as forecast."""
        future = (datetime.now(UTC) + timedelta(days=5)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", future)

        _insert_observation(temp_db, obs_id, "forecast", future, future)
        temp_db.initialize()

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "forecast"

    def test_observation_rows_untouched(self, temp_db: Database) -> None:
        """Existing observation rows are not affected by reclassification."""
        now = datetime.now(UTC)
        past = (now - timedelta(hours=2)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "temperature_2m", past)

        _insert_observation(temp_db, obs_id, "observation", past, past)
        temp_db.initialize()

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "observation"

    def test_reclassification_preserves_fields(self, temp_db: Database) -> None:
        """Reclassification only changes observation_type; all other fields intact."""
        now = datetime.now(UTC)
        past = (now - timedelta(hours=2)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", past)

        _insert_observation(temp_db, obs_id, "forecast", past, past, value=42.7)
        temp_db.initialize()

        row = temp_db.fetch_one(
            "SELECT * FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "observation"
        assert row["observation_id"] == obs_id
        assert row["source_id"] == "openmeteo"
        assert row["parameter"] == "pm2_5"
        assert row["value"] == 42.7
        assert row["unit"] == "ug/m3"
        assert row["observed_at"] == past

    def test_multiple_stale_forecasts_reclassified(self, temp_db: Database) -> None:
        """Multiple eligible forecasts are all reclassified in one batch."""
        now = datetime.now(UTC)
        params = ["pm2_5", "pm10", "nitrogen_dioxide", "ozone"]

        for p in params:
            ts = (now - timedelta(hours=2)).isoformat()
            obs_id = _gen_obs_id("openmeteo", None, p, ts)
            _insert_observation(temp_db, obs_id, "forecast", ts, ts)

        temp_db.initialize()

        for p in params:
            ts = (now - timedelta(hours=2)).isoformat()
            obs_id = _gen_obs_id("openmeteo", None, p, ts)
            row = temp_db.fetch_one(
                "SELECT observation_type FROM observations WHERE observation_id = ?",
                (obs_id,),
            )
            assert row["observation_type"] == "observation", f"{p} not reclassified"

    def test_mixed_eligible_and_ineligible(self, temp_db: Database) -> None:
        """Only eligible rows transition; ineligible rows are untouched."""
        now = datetime.now(UTC)

        # Eligible: past forecast
        past = (now - timedelta(hours=2)).isoformat()
        id_eligible = _gen_obs_id("openmeteo", None, "pm2_5", past)
        _insert_observation(temp_db, id_eligible, "forecast", past, past)

        # Ineligible: future forecast
        future = (now + timedelta(days=2)).isoformat()
        id_future = _gen_obs_id("openmeteo", None, "ozone", future)
        _insert_observation(temp_db, id_future, "forecast", future, future)

        # Ineligible: already observation
        past2 = (now - timedelta(hours=1)).isoformat()
        id_obs = _gen_obs_id("openmeteo", None, "temperature_2m", past2)
        _insert_observation(temp_db, id_obs, "observation", past2, past2)

        temp_db.initialize()

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (id_eligible,),
        )
        assert row["observation_type"] == "observation"

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (id_future,),
        )
        assert row["observation_type"] == "forecast"

        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (id_obs,),
        )
        assert row["observation_type"] == "observation"


# ══════════════════════════════════════════════════════════════════════════
# FIX 2: Ingestion Forecast -> Observation Lifecycle Tests
# ══════════════════════════════════════════════════════════════════════════


class TestIngestionLifecycle:
    """Tests for _process_observation forecast -> observation transition."""

    def test_forecast_becomes_observation_on_reingest(self, temp_db: Database) -> None:
        """When a forecast's time has passed, re-ingestion updates it to observation."""
        from app.application.services.ingestion import IngestionService
        from app.core.config import Settings

        now = datetime.now(UTC)
        past = (now - timedelta(hours=2)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", past)

        # Insert as forecast
        _insert_observation(temp_db, obs_id, "forecast", past, past)
        row = temp_db.fetch_one(
            "SELECT observation_type FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row["observation_type"] == "forecast"

        # Create service and process the same record as observation
        settings = Settings(environment="testing", database_url="sqlite:///unused")
        service = IngestionService(settings, temp_db)

        obs_dict = {
            "station_id": None,
            "parameter": "pm2_5",
            "value": 42.0,
            "unit": "ug/m3",
            "observed_at": past,
            "latitude": 31.52,
            "longitude": 74.36,
            "quality_status": "valid",
            "source_identifier": "",
        }
        record = service._process_observation(
            obs_dict=obs_dict,
            source_id="openmeteo",
            raw_response="{}",
        )

        assert record.status.value == "accepted"

        row = temp_db.fetch_one(
            "SELECT * FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row is not None
        assert row["observation_type"] == "observation"
        assert row["source_id"] == "openmeteo"
        assert row["parameter"] == "pm2_5"
        assert row["observed_at"] == past

    def test_new_observation_inserts_normally(self, temp_db: Database) -> None:
        """A new observation with no existing row is inserted normally."""
        from app.application.services.ingestion import IngestionService
        from app.core.config import Settings

        now = datetime.now(UTC)
        past = (now - timedelta(hours=1)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", past)

        settings = Settings(environment="testing", database_url="sqlite:///unused")
        service = IngestionService(settings, temp_db)

        obs_dict = {
            "station_id": None,
            "parameter": "pm2_5",
            "value": 55.0,
            "unit": "ug/m3",
            "observed_at": past,
            "latitude": 31.52,
            "longitude": 74.36,
            "quality_status": "valid",
            "source_identifier": "",
        }
        record = service._process_observation(
            obs_dict=obs_dict,
            source_id="openmeteo",
            raw_response="{}",
        )
        assert record.status.value == "accepted"

        row = temp_db.fetch_one(
            "SELECT * FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row is not None
        assert row["observation_type"] == "observation"
        assert row["value"] == 55.0

    def test_future_forecast_inserts_as_forecast(self, temp_db: Database) -> None:
        """A future record is inserted as forecast, not observation."""
        from app.application.services.ingestion import IngestionService
        from app.core.config import Settings

        future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", future)

        settings = Settings(environment="testing", database_url="sqlite:///unused")
        service = IngestionService(settings, temp_db)

        obs_dict = {
            "station_id": None,
            "parameter": "pm2_5",
            "value": 30.0,
            "unit": "ug/m3",
            "observed_at": future,
            "latitude": 31.52,
            "longitude": 74.36,
            "quality_status": "valid",
            "source_identifier": "",
        }
        record = service._process_observation(
            obs_dict=obs_dict,
            source_id="openmeteo",
            raw_response="{}",
        )
        assert record.status.value == "accepted"

        row = temp_db.fetch_one(
            "SELECT * FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert row is not None
        assert row["observation_type"] == "forecast"

    def test_duplicate_identical_record_ignored(self, temp_db: Database) -> None:
        """Re-ingesting the same observation (same time) is deduplicated."""
        from app.application.services.ingestion import IngestionService
        from app.core.config import Settings

        now = datetime.now(UTC)
        past = (now - timedelta(hours=1)).isoformat()
        obs_id = _gen_obs_id("openmeteo", None, "pm2_5", past)

        _insert_observation(temp_db, obs_id, "observation", past, past, value=60.0)

        settings = Settings(environment="testing", database_url="sqlite:///unused")
        service = IngestionService(settings, temp_db)

        obs_dict = {
            "station_id": None,
            "parameter": "pm2_5",
            "value": 60.0,
            "unit": "ug/m3",
            "observed_at": past,
            "latitude": 31.52,
            "longitude": 74.36,
            "quality_status": "valid",
            "source_identifier": "",
        }
        record = service._process_observation(
            obs_dict=obs_dict,
            source_id="openmeteo",
            raw_response="{}",
        )
        assert record.status.value == "accepted"

        rows = temp_db.fetch_all(
            "SELECT * FROM observations WHERE observation_id = ?",
            (obs_id,),
        )
        assert len(rows) == 1
        assert rows[0]["observation_type"] == "observation"


# ══════════════════════════════════════════════════════════════════════════
# FIX 3: Auto-Refresh Tests
# ══════════════════════════════════════════════════════════════════════════


class TestAutoRefresh:
    """Tests for the _auto_refresh_loop background task."""

    def test_service_construction_succeeds(self) -> None:
        """IngestionService can be constructed with settings + db."""
        from app.application.services.ingestion import IngestionService
        from app.core.config import Settings

        settings = Settings(environment="testing", database_url="sqlite:///unused")
        db = Database(":memory:")
        db.initialize()
        try:
            service = IngestionService(settings, db)
            assert service._settings is settings
            assert service._db is db
        finally:
            db.close()

    def test_refresh_methods_exist(self) -> None:
        """IngestionService has the expected public ingestion methods."""
        from app.application.services.ingestion import IngestionService

        assert hasattr(IngestionService, "ingest_current_weather")
        assert hasattr(IngestionService, "ingest_current_air_quality")
        assert hasattr(IngestionService, "ingest_live_aqicn")
        assert callable(getattr(IngestionService, "ingest_current_weather"))
        assert callable(getattr(IngestionService, "ingest_current_air_quality"))
        assert callable(getattr(IngestionService, "ingest_live_aqicn"))

    def test_auto_refresh_loop_imports_correctly(self) -> None:
        """The auto-refresh loop is a valid async coroutine."""
        from app.main import _auto_refresh_loop

        assert asyncio.iscoroutinefunction(_auto_refresh_loop)

    def test_auto_refresh_succeeds_with_mock(self) -> None:
        """A refresh cycle completes successfully with mocked providers."""
        from app.main import _auto_refresh_loop

        mock_settings = MagicMock()
        mock_db = AsyncMock()
        mock_service = MagicMock()

        mock_weather_run = MagicMock()
        mock_weather_run.accepted_records = 100
        mock_weather_run.rejected_records = 2
        mock_aq_run = MagicMock()
        mock_aq_run.accepted_records = 50
        mock_aq_run.rejected_records = 1
        mock_live_run = MagicMock()
        mock_live_run.accepted_records = 10
        mock_live_run.rejected_records = 0

        mock_service.ingest_current_weather = AsyncMock(return_value=mock_weather_run)
        mock_service.ingest_current_air_quality = AsyncMock(return_value=mock_aq_run)
        mock_service.ingest_live_aqicn = AsyncMock(return_value=mock_live_run)

        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        async def _run():
            with (
                patch("app.main.get_settings", return_value=mock_settings),
                patch("app.infrastructure.database.get_database",
                       new_callable=AsyncMock, return_value=mock_db),
                patch("app.application.services.ingestion.IngestionService",
                       return_value=mock_service),
                patch("app.infrastructure.providers.openmeteo.OpenMeteoProvider",
                       return_value=MagicMock()),
                patch("app.infrastructure.providers.aqicn.AQICNProvider",
                       return_value=MagicMock()),
                patch("app.main.asyncio.sleep", side_effect=mock_sleep),
                patch("app.modeling.serving.feature_assembly._observation_cache") as mock_cache,
            ):
                await _auto_refresh_loop()
            return mock_cache

        mock_cache = asyncio.run(_run())

        mock_service.ingest_current_weather.assert_called_once()
        mock_service.ingest_current_air_quality.assert_called_once()
        mock_service.ingest_live_aqicn.assert_called_once()
        mock_cache.invalidate.assert_called_once()

    def test_auto_refresh_continues_after_failure(self) -> None:
        """The loop continues running after a provider failure."""
        from app.main import _auto_refresh_loop

        mock_settings = MagicMock()
        mock_db = AsyncMock()
        mock_service = MagicMock()

        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise asyncio.CancelledError()

        mock_service.ingest_current_weather = AsyncMock(
            side_effect=Exception("Network error")
        )
        mock_aq_run = MagicMock()
        mock_aq_run.accepted_records = 50
        mock_aq_run.rejected_records = 0
        mock_live_run = MagicMock()
        mock_live_run.accepted_records = 10
        mock_live_run.rejected_records = 0
        mock_service.ingest_current_air_quality = AsyncMock(return_value=mock_aq_run)
        mock_service.ingest_live_aqicn = AsyncMock(return_value=mock_live_run)

        async def _run():
            with (
                patch("app.main.get_settings", return_value=mock_settings),
                patch("app.infrastructure.database.get_database",
                       new_callable=AsyncMock, return_value=mock_db),
                patch("app.application.services.ingestion.IngestionService",
                       return_value=mock_service),
                patch("app.infrastructure.providers.openmeteo.OpenMeteoProvider",
                       return_value=MagicMock()),
                patch("app.infrastructure.providers.aqicn.AQICNProvider",
                       return_value=MagicMock()),
                patch("app.main.asyncio.sleep", side_effect=mock_sleep),
                patch("app.modeling.serving.feature_assembly._observation_cache"),
            ):
                await _auto_refresh_loop()

        asyncio.run(_run())

        mock_service.ingest_current_air_quality.assert_called_once()
        mock_service.ingest_live_aqicn.assert_called_once()

    def test_auto_refresh_skips_overlapping(self) -> None:
        """When a refresh is still running, the next cycle is skipped."""
        from app.main import _auto_refresh_loop

        mock_settings = MagicMock()
        mock_db = AsyncMock()
        mock_service = MagicMock()

        sleep_count = 0
        refresh_count = 0

        async def mock_sleep(seconds):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count >= 3:
                raise asyncio.CancelledError()

        async def slow_refresh(*args, **kwargs):
            nonlocal refresh_count
            refresh_count += 1
            if refresh_count == 1:
                await asyncio.sleep(100)
            return MagicMock(accepted_records=10, rejected_records=0)

        mock_service.ingest_current_weather = slow_refresh
        mock_service.ingest_current_air_quality = AsyncMock(
            return_value=MagicMock(accepted_records=0, rejected_records=0)
        )
        mock_service.ingest_live_aqicn = AsyncMock(
            return_value=MagicMock(accepted_records=0, rejected_records=0)
        )

        async def _run():
            with (
                patch("app.main.get_settings", return_value=mock_settings),
                patch("app.infrastructure.database.get_database",
                       new_callable=AsyncMock, return_value=mock_db),
                patch("app.application.services.ingestion.IngestionService",
                       return_value=mock_service),
                patch("app.infrastructure.providers.openmeteo.OpenMeteoProvider",
                       return_value=MagicMock()),
                patch("app.infrastructure.providers.aqicn.AQICNProvider",
                       return_value=MagicMock()),
                patch("app.main.asyncio.sleep", side_effect=mock_sleep),
                patch("app.modeling.serving.feature_assembly._observation_cache"),
            ):
                await _auto_refresh_loop()

        asyncio.run(_run())

        assert refresh_count <= 2
