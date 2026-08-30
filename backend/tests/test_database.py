"""Tests for the SQLite database layer.

Tests schema creation, CRUD operations, idempotency,
and data integrity constraints.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.database import Database


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def seeded_db(temp_db: Database) -> Database:
    """Database with required data_sources pre-inserted for FK compliance."""
    for source_id, name, provider, stype in [
        ("openmeteo", "Open-Meteo", "Open-Meteo GmbH", "weather"),
        ("openaq", "OpenAQ", "OpenAQ", "air_quality"),
        ("aqicn", "WAQI", "WAQI Project", "air_quality"),
    ]:
        temp_db.execute(
            """INSERT INTO data_sources (source_id, name, provider, source_type)
               VALUES (?, ?, ?, ?)""",
            (source_id, name, provider, stype),
        )
    temp_db.commit()
    return temp_db


class TestDatabaseSchema:
    """Tests for schema creation and table structure."""

    def test_initialize_creates_tables(self, temp_db: Database) -> None:
        """initialize() creates all required tables."""
        tables = temp_db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        )
        table_names = [t["name"] for t in tables]
        assert "data_sources" in table_names
        assert "stations" in table_names
        assert "observations" in table_names
        assert "ingestion_runs" in table_names
        assert "ingestion_records" in table_names

    def test_idempotent_initialize(self, temp_db: Database) -> None:
        """Calling initialize() twice doesn't error."""
        temp_db.initialize()
        temp_db.initialize()

    def test_table_row_count_empty(self, temp_db: Database) -> None:
        """New database has zero rows in all tables."""
        assert temp_db.table_row_count("observations") == 0
        assert temp_db.table_row_count("ingestion_runs") == 0


class TestDatabaseOperations:
    """Tests for CRUD operations."""

    def test_execute_and_fetch(self, temp_db: Database) -> None:
        """Basic INSERT and SELECT works."""
        temp_db.execute(
            """INSERT INTO data_sources (source_id, name, provider, source_type)
               VALUES (?, ?, ?, ?)""",
            ("test", "Test Source", "Test Provider", "weather"),
        )
        temp_db.commit()

        rows = temp_db.fetch_all("SELECT * FROM data_sources WHERE source_id = ?", ("test",))
        assert len(rows) == 1
        assert rows[0]["name"] == "Test Source"

    def test_fetch_one_returns_dict(self, temp_db: Database) -> None:
        """fetch_one returns a single dict or None."""
        temp_db.execute(
            """INSERT INTO data_sources (source_id, name, provider, source_type)
               VALUES (?, ?, ?, ?)""",
            ("test", "Test", "Provider", "weather"),
        )
        temp_db.commit()

        result = temp_db.fetch_one("SELECT * FROM data_sources WHERE source_id = ?", ("test",))
        assert result is not None
        assert result["source_id"] == "test"

    def test_fetch_one_no_match(self, temp_db: Database) -> None:
        """fetch_one returns None when no match."""
        result = temp_db.fetch_one(
            "SELECT * FROM data_sources WHERE source_id = ?", ("nonexistent",)
        )
        assert result is None

    def test_fetch_all_empty(self, temp_db: Database) -> None:
        """fetch_all returns empty list when no rows."""
        result = temp_db.fetch_all("SELECT * FROM data_sources")
        assert result == []

    def test_execute_many(self, temp_db: Database) -> None:
        """executemany inserts multiple rows."""
        data = [
            ("openmeteo", "Open-Meteo", "Open-Meteo GmbH", "weather"),
            ("openaq", "OpenAQ", "OpenAQ", "air_quality"),
            ("aqicn", "WAQI", "WAQI Project", "air_quality"),
        ]
        temp_db.executemany(
            """INSERT INTO data_sources (source_id, name, provider, source_type)
               VALUES (?, ?, ?, ?)""",
            data,
        )
        temp_db.commit()

        count = temp_db.table_row_count("data_sources")
        assert count == 3

    def test_rollback(self, temp_db: Database) -> None:
        """Rollback undoes uncommitted changes."""
        temp_db.execute(
            """INSERT INTO data_sources (source_id, name, provider, source_type)
               VALUES (?, ?, ?, ?)""",
            ("test", "Test", "Provider", "weather"),
        )
        temp_db.rollback()

        count = temp_db.table_row_count("data_sources")
        assert count == 0


class TestObservationIdempotency:
    """Tests for idempotent observation inserts."""

    def test_duplicate_observation_ignored(self, seeded_db: Database) -> None:
        """Duplicate (source_id, station_id, parameter, observed_at) is ignored.

        NOTE: SQLite NULL != NULL in unique constraints, so station_id must
        be non-NULL for idempotency to work via the UNIQUE index.
        """
        # First insert
        seeded_db.execute(
            """INSERT INTO observations
               (observation_id, source_id, station_id, parameter, value, unit,
                observed_at, retrieved_at, latitude, longitude, quality_status,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?,
                datetime('now'))""",
            (
                "obs-1",
                "openmeteo",
                "station-a",
                "pm25",
                45.2,
                "ug/m3",
                "2024-01-01T00:00",
                31.5,
                74.3,
                "valid",
            ),
        )
        seeded_db.commit()

        # Second insert with same natural key but different ID
        seeded_db.execute(
            """INSERT OR IGNORE INTO observations
               (observation_id, source_id, station_id, parameter, value, unit,
                observed_at, retrieved_at, latitude, longitude, quality_status,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?,
                datetime('now'))""",
            (
                "obs-2",
                "openmeteo",
                "station-a",
                "pm25",
                50.0,
                "ug/m3",
                "2024-01-01T00:00",
                31.5,
                74.3,
                "valid",
            ),
        )
        seeded_db.commit()

        # Should still have only one row
        count = seeded_db.table_row_count("observations")
        assert count == 1

    def test_different_parameter_not_duplicate(self, seeded_db: Database) -> None:
        """Different parameter is NOT a duplicate."""
        for param, value in [("pm25", 45.2), ("pm10", 85.0)]:
            seeded_db.execute(
                """INSERT INTO observations
                   (observation_id, source_id, station_id, parameter, value, unit,
                    observed_at, retrieved_at, latitude, longitude, quality_status,
                    created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?,
                    datetime('now'))""",
                (
                    f"obs-{param}",
                    "openmeteo",
                    None,
                    param,
                    value,
                    "ug/m3",
                    "2024-01-01T00:00",
                    31.5,
                    74.3,
                    "valid",
                ),
            )
        seeded_db.commit()

        count = seeded_db.table_row_count("observations")
        assert count == 2

    def test_different_time_not_duplicate(self, seeded_db: Database) -> None:
        """Different timestamp is NOT a duplicate."""
        for time_str in ["2024-01-01T00:00", "2024-01-01T01:00"]:
            seeded_db.execute(
                """INSERT INTO observations
                   (observation_id, source_id, station_id, parameter, value, unit,
                    observed_at, retrieved_at, latitude, longitude, quality_status,
                    created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?,
                    datetime('now'))""",
                (
                    f"obs-{time_str}",
                    "openmeteo",
                    None,
                    "pm25",
                    45.2,
                    "ug/m3",
                    time_str,
                    31.5,
                    74.3,
                    "valid",
                ),
            )
        seeded_db.commit()

        count = seeded_db.table_row_count("observations")
        assert count == 2


class TestIngestionRunTracking:
    """Tests for ingestion run records."""

    def test_insert_and_fetch_run(self, temp_db: Database) -> None:
        """Ingestion run can be inserted and fetched."""
        from datetime import UTC, datetime

        temp_db.execute(
            """INSERT INTO ingestion_runs
               (run_id, operation, provider, status, started_at, records_received)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("run-123", "historical", "openmeteo", "running", datetime.now(UTC).isoformat(), 0),
        )
        temp_db.commit()

        result = temp_db.fetch_one("SELECT * FROM ingestion_runs WHERE run_id = ?", ("run-123",))
        assert result is not None
        assert result["provider"] == "openmeteo"
        assert result["status"] == "running"

    def test_update_run_status(self, temp_db: Database) -> None:
        """Run status can be updated to completed."""
        from datetime import UTC, datetime

        temp_db.execute(
            """INSERT INTO ingestion_runs
               (run_id, operation, provider, status, started_at)
               VALUES (?, ?, ?, ?, ?)""",
            ("run-456", "live", "aqicn", "running", datetime.now(UTC).isoformat()),
        )
        temp_db.commit()

        temp_db.execute(
            """UPDATE ingestion_runs
               SET status = ?, records_accepted = ?, records_rejected = ?
               WHERE run_id = ?""",
            ("completed", 10, 2, "run-456"),
        )
        temp_db.commit()

        result = temp_db.fetch_one("SELECT * FROM ingestion_runs WHERE run_id = ?", ("run-456",))
        assert result["status"] == "completed"
        assert result["records_accepted"] == 10

    def test_multiple_runs_ordering(self, temp_db: Database) -> None:
        """Multiple runs can be listed in reverse chronological order."""

        for i in range(3):
            temp_db.execute(
                """INSERT INTO ingestion_runs
                   (run_id, operation, provider, status, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    f"run-{i}",
                    "historical",
                    "openmeteo",
                    "completed",
                    f"2024-01-0{i + 1}T00:00:00+00:00",
                ),
            )
        temp_db.commit()

        results = temp_db.fetch_all(
            "SELECT * FROM ingestion_runs ORDER BY started_at DESC",
        )
        assert len(results) == 3
        assert results[0]["run_id"] == "run-2"  # Most recent in DESC order


class TestObservationQueries:
    """Tests for observation query patterns."""

    def _insert_test_observations(self, db: Database) -> None:
        """Insert test observations for querying."""
        observations = [
            (
                "obs-1",
                "openmeteo",
                None,
                "temperature_2m",
                25.0,
                "°C",
                "2024-01-01T00:00",
                31.5,
                74.3,
                "valid",
                "openmeteo|temp|2024-01-01T00:00",
            ),
            (
                "obs-2",
                "openmeteo",
                None,
                "temperature_2m",
                26.0,
                "°C",
                "2024-01-01T01:00",
                31.5,
                74.3,
                "valid",
                "openmeteo|temp|2024-01-01T01:00",
            ),
            (
                "obs-3",
                "openaq",
                "station-1",
                "pm25",
                45.2,
                "ug/m3",
                "2024-01-01T00:00",
                31.53,
                74.36,
                "unverified",
                "openaq|pm25|2024-01-01T00:00",
            ),
            (
                "obs-4",
                "aqicn",
                "station-2",
                "pm25",
                89.0,
                "ug/m3",
                "2024-01-01T00:00",
                31.52,
                74.37,
                "unverified",
                "aqicn|pm25|2024-01-01T00:00",
            ),
        ]
        for obs in observations:
            db.execute(
                """INSERT INTO observations
                   (observation_id, source_id, station_id, parameter, value,
                    unit, observed_at, retrieved_at, latitude, longitude,
                    quality_status, source_identifier, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?,
                    ?, datetime('now'))""",
                obs,
            )
        db.commit()

    def test_query_by_source(self, seeded_db: Database) -> None:
        """Can filter observations by source."""
        self._insert_test_observations(seeded_db)

        results = seeded_db.fetch_all(
            "SELECT * FROM observations WHERE source_id = ?",
            ("openmeteo",),
        )
        assert len(results) == 2
        assert all(r["source_id"] == "openmeteo" for r in results)

    def test_query_by_parameter(self, seeded_db: Database) -> None:
        """Can filter observations by parameter."""
        self._insert_test_observations(seeded_db)

        results = seeded_db.fetch_all(
            "SELECT * FROM observations WHERE parameter = ?",
            ("pm25",),
        )
        assert len(results) == 2

    def test_count_by_source(self, seeded_db: Database) -> None:
        """Can count observations grouped by source."""
        self._insert_test_observations(seeded_db)

        results = seeded_db.fetch_all(
            "SELECT source_id, COUNT(*) as count FROM observations GROUP BY source_id",
        )
        counts = {r["source_id"]: r["count"] for r in results}
        assert counts["openmeteo"] == 2
        assert counts["openaq"] == 1
        assert counts["aqicn"] == 1

    def test_query_stats(self, seeded_db: Database) -> None:
        """Can compute statistics for a parameter."""
        self._insert_test_observations(seeded_db)

        result = seeded_db.fetch_one(
            """SELECT MIN(value) as min_val, MAX(value) as max_val,
                      AVG(value) as avg_val
               FROM observations WHERE parameter = 'pm25'""",
        )
        assert result is not None
        assert result["min_val"] == 45.2
        assert result["max_val"] == 89.0
