"""SQLite database layer.

Provides schema management and data access for Lahore Pulse AI.

Schema Design:
- data_sources: Registered external data providers
- stations: Monitoring station locations
- observations: Normalized environmental measurements
- ingestion_runs: Ingestion execution tracking
- ingestion_records: Individual record outcomes

Idempotency:
- Observations are uniquely keyed on (source_id, station_id, parameter, observed_at)
- Duplicate detection uses INSERT OR IGNORE with a UNIQUE constraint
- Ingestion runs use deterministic UUIDs based on provider+operation+timestamp

Storage Decision:
SQLite is chosen because:
1. No external dependencies (built into Python)
2. Appropriate for the current scale (millions of rows, not billions)
3. Single-file database is easy to backup and inspect
4. ACID compliance ensures data integrity
5. Can migrate to PostgreSQL later if needed

Raw Response Storage:
Raw API responses are preserved as JSON text in the observations table.
This is justified by the CC-BY 4.0 licensing of Open-Meteo and OpenAQ.
It enables debugging and reproducibility of transformations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from loguru import logger

# ── Schema DDL ────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- Data sources: registered external providers
CREATE TABLE IF NOT EXISTS data_sources (
    source_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    provider    TEXT NOT NULL,
    source_type TEXT NOT NULL,
    base_url    TEXT,
    license     TEXT,
    documentation_url TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Stations: monitoring locations within a data source
CREATE TABLE IF NOT EXISTS stations (
    station_id      TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL REFERENCES data_sources(source_id),
    name            TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    altitude_meters REAL,
    active          INTEGER NOT NULL DEFAULT 1,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_stations_source ON stations(source_id);
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations(latitude, longitude);

-- Observations: normalized environmental measurements
CREATE TABLE IF NOT EXISTS observations (
    observation_id    TEXT PRIMARY KEY,
    source_id         TEXT NOT NULL REFERENCES data_sources(source_id),
    station_id        TEXT,
    parameter         TEXT NOT NULL,
    value             REAL NOT NULL,
    unit              TEXT NOT NULL,
    observed_at       TEXT NOT NULL,
    retrieved_at      TEXT NOT NULL,
    latitude          REAL NOT NULL,
    longitude         REAL NOT NULL,
    quality_status    TEXT NOT NULL DEFAULT 'unverified',
    observation_type  TEXT NOT NULL DEFAULT 'observation'
        CHECK(observation_type IN ('observation', 'forecast', 'model_prediction')),
    source_identifier TEXT,
    raw_response      TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Unique constraint for idempotency: same source+station+parameter+time = same record
CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_unique
    ON observations(source_id, station_id, parameter, observed_at);

CREATE INDEX IF NOT EXISTS idx_obs_source ON observations(source_id);
CREATE INDEX IF NOT EXISTS idx_obs_parameter ON observations(parameter);
CREATE INDEX IF NOT EXISTS idx_obs_observed_at ON observations(observed_at);
CREATE INDEX IF NOT EXISTS idx_obs_quality ON observations(quality_status);
CREATE INDEX IF NOT EXISTS idx_obs_feature_assembly
    ON observations(observed_at, parameter, value);

-- Ingestion runs: execution tracking
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id            TEXT PRIMARY KEY,
    provider          TEXT NOT NULL,
    operation         TEXT NOT NULL,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    status            TEXT NOT NULL DEFAULT 'running',
    records_received  INTEGER DEFAULT 0,
    records_accepted  INTEGER DEFAULT 0,
    records_rejected  INTEGER DEFAULT 0,
    records_duplicated INTEGER DEFAULT 0,
    error_message     TEXT,
    metadata          TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_runs_provider ON ingestion_runs(provider);
CREATE INDEX IF NOT EXISTS idx_runs_status ON ingestion_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started ON ingestion_runs(started_at);

-- Ingestion records: individual record outcomes
CREATE TABLE IF NOT EXISTS ingestion_records (
    record_id         TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL REFERENCES ingestion_runs(run_id),
    source_identifier TEXT,
    status            TEXT NOT NULL,
    observation_id    TEXT,
    error_reason      TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_records_run ON ingestion_records(run_id);
CREATE INDEX IF NOT EXISTS idx_records_status ON ingestion_records(status);

-- Alert preferences: per-user notification thresholds
CREATE TABLE IF NOT EXISTS alert_preferences (
    pref_id     TEXT PRIMARY KEY,
    alert_type  TEXT NOT NULL UNIQUE,
    enabled     INTEGER NOT NULL DEFAULT 0,
    threshold   REAL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Alert history: generated alerts with severity and message
CREATE TABLE IF NOT EXISTS alert_history (
    alert_id    TEXT PRIMARY KEY,
    alert_type  TEXT NOT NULL,
    severity    TEXT NOT NULL,
    aqi_value   REAL,
    level       TEXT NOT NULL,
    message     TEXT NOT NULL,
    read        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alert_history_created ON alert_history(created_at);
CREATE INDEX IF NOT EXISTS idx_alert_history_severity ON alert_history(severity);

-- Report history: generated reports with metadata
CREATE TABLE IF NOT EXISTS report_history (
    report_id   TEXT PRIMARY KEY,
    report_type TEXT NOT NULL,
    name        TEXT NOT NULL,
    range_start TEXT,
    range_end   TEXT,
    format      TEXT NOT NULL DEFAULT 'pdf',
    status      TEXT NOT NULL DEFAULT 'generated',
    file_path   TEXT,
    metadata    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_report_history_type ON report_history(report_type);
CREATE INDEX IF NOT EXISTS idx_report_history_created ON report_history(created_at);

-- Saved locations: user-favorited monitoring stations
CREATE TABLE IF NOT EXISTS saved_locations (
    location_id   TEXT PRIMARY KEY,
    station_id    TEXT,
    name          TEXT NOT NULL,
    label         TEXT,
    latitude      REAL,
    longitude     REAL,
    icon          TEXT NOT NULL DEFAULT 'map-pin',
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_saved_locations_order ON saved_locations(sort_order);
"""


class Database:
    """SQLite database connection and schema management.

    Provides a simple synchronous interface to the database.
    For the current scale (hackathon project), synchronous
    access is appropriate and avoids unnecessary complexity.

    Usage:
        db = Database("data/lahore_pulse.db")
        db.initialize()
        cursor = db.execute("SELECT * FROM observations")
    """

    def __init__(self, database_path: str) -> None:
        """Initialize database with the given file path.

        Args:
            database_path: Path to the SQLite database file.
                          Directories will be created if they don't exist.
        """
        self.database_path = Path(database_path)
        self._connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection.

        Applies read-optimized PRAGMAs on first connection:
        - WAL journal mode (safe for concurrent readers)
        - foreign_keys=ON (referential integrity)
        - cache_size=-64000 (64 MB page cache, default is 2 MB)
        - temp_store=MEMORY (avoids disk spills for ORDER BY / GROUP BY)
        - mmap_size=268435456 (256 MB memory-mapped I/O)
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.database_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA cache_size=-64000")       # 64 MB
            self._connection.execute("PRAGMA temp_store=MEMORY")
            self._connection.execute("PRAGMA mmap_size=268435456")     # 256 MB
        return self._connection

    def initialize(self) -> None:
        """Create the database directory, apply schema, and update statistics."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        # Run schema migrations for existing databases
        self._migrate(conn)
        conn.commit()
        # Refresh query-planner statistics so SQLite chooses optimal indexes.
        # This is safe and idempotent; ANALYZE costs ~10s on first run but
        # the results are persisted in the database file.
        conn.execute("ANALYZE")
        conn.commit()
        logger.info("Database initialized", path=str(self.database_path))

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Run schema migrations for existing databases.

        Idempotent: each migration checks before applying.
        """
        # Migration 1: Add observation_type column (Phase 6.8)
        # Classifies records as 'observation', 'forecast', or 'model_prediction'.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(observations)").fetchall()}
        if "observation_type" not in cols:
            logger.info("Migration: adding observation_type column to observations")
            conn.execute(
                "ALTER TABLE observations "
                "ADD COLUMN observation_type TEXT NOT NULL DEFAULT 'observation'"
            )
            # Classify existing forecast records: observed_at > retrieved_at means
            # the data was for a future timestamp at ingest time.
            conn.execute(
                "UPDATE observations "
                "SET observation_type = 'forecast' "
                "WHERE observed_at > retrieved_at"
            )
            forecast_count = conn.execute(
                "SELECT changes()"
            ).fetchone()[0]
            if forecast_count > 0:
                logger.info(
                    "Migration: classified forecast records",
                    count=forecast_count,
                )
            # Add CHECK constraint via index (SQLite doesn't support ALTER CHECK)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_obs_type "
                "ON observations(observation_type)"
            )
            conn.commit()

        # Migration 2: Reclassify stale forecast records (Bug A fix).
        # Forecasts whose observed_at has passed should become observations.
        # This is idempotent: re-running on already-correct rows changes nothing.
        # NOTE: ISO 8601 timestamps use 'T' separator and '+HH:MM' offset,
        # but SQLite datetime('now') returns 'YYYY-MM-DD HH:MM:SS'.  We
        # normalise to comparable form by replacing 'T' and taking the first
        # 19 characters so string comparison works correctly.
        stale_count = conn.execute(
            "SELECT COUNT(*) FROM observations "
            "WHERE observation_type = 'forecast' "
            "AND substr(replace(observed_at, 'T', ' '), 1, 19) <= datetime('now')"
        ).fetchone()[0]

        if stale_count > 0:
            conn.execute(
                "UPDATE observations "
                "SET observation_type = 'observation' "
                "WHERE observation_type = 'forecast' "
                "AND substr(replace(observed_at, 'T', ' '), 1, 19) <= datetime('now')"
            )
            updated_count = conn.execute("SELECT changes()").fetchone()[0]
            conn.commit()
            logger.info(
                "Migration: reclassified stale forecasts to observations",
                before=stale_count,
                updated=updated_count,
            )

        # Migration 3: Alert preferences, alert history, report history tables
        existing_tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if "alert_preferences" not in existing_tables:
            logger.info("Migration: creating alert_preferences table")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_preferences (
                    pref_id     TEXT PRIMARY KEY,
                    alert_type  TEXT NOT NULL UNIQUE,
                    enabled     INTEGER NOT NULL DEFAULT 0,
                    threshold   REAL,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            # Seed with default preferences (all disabled)
            for atype, threshold in [
                ("fair", 35.0),
                ("moderate", 55.0),
                ("poor", 90.0),
                ("dangerous", 150.0),
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO alert_preferences (pref_id, alert_type, enabled, threshold) "
                    "VALUES (?, ?, 0, ?)",
                    (f"pref-{atype}", atype, threshold),
                )
            conn.commit()

        if "alert_history" not in existing_tables:
            logger.info("Migration: creating alert_history table")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    alert_id    TEXT PRIMARY KEY,
                    alert_type  TEXT NOT NULL,
                    severity    TEXT NOT NULL,
                    aqi_value   REAL,
                    level       TEXT NOT NULL,
                    message     TEXT NOT NULL,
                    read        INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_history_created ON alert_history(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_history_severity ON alert_history(severity)"
            )
            conn.commit()

        if "report_history" not in existing_tables:
            logger.info("Migration: creating report_history table")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS report_history (
                    report_id   TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    name        TEXT NOT NULL,
                    range_start TEXT,
                    range_end   TEXT,
                    format      TEXT NOT NULL DEFAULT 'pdf',
                    status      TEXT NOT NULL DEFAULT 'generated',
                    file_path   TEXT,
                    metadata    TEXT,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_report_history_type ON report_history(report_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_report_history_created ON report_history(created_at)"
            )
            conn.commit()

        # Seed default alert preferences if table is empty
        # (SCHEMA_SQL creates tables but doesn't seed data)
        pref_count = conn.execute("SELECT COUNT(*) FROM alert_preferences").fetchone()[0]
        if pref_count == 0:
            logger.info("Migration: seeding default alert preferences")
            for atype, threshold in [
                ("fair", 35.0),
                ("moderate", 55.0),
                ("poor", 90.0),
                ("dangerous", 150.0),
            ]:
                conn.execute(
                    "INSERT OR IGNORE INTO alert_preferences (pref_id, alert_type, enabled, threshold) "
                    "VALUES (?, ?, 0, ?)",
                    (f"pref-{atype}", atype, threshold),
                )
            conn.commit()

        # Migration 4: Saved locations table for My Lahore page
        if "saved_locations" not in existing_tables:
            logger.info("Migration: creating saved_locations table")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_locations (
                    location_id   TEXT PRIMARY KEY,
                    station_id    TEXT,
                    name          TEXT NOT NULL,
                    label         TEXT,
                    latitude      REAL,
                    longitude     REAL,
                    icon          TEXT NOT NULL DEFAULT 'map-pin',
                    sort_order    INTEGER NOT NULL DEFAULT 0,
                    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_saved_locations_order ON saved_locations(sort_order)"
            )
            conn.commit()

        # Migration 5: Investigation verification outcomes (Phase 5 — Learning Loop)
        # Stores human verification of AI investigation results.
        # The AI analysis itself is NEVER modified — verification is stored separately.
        if "verification_outcomes" not in existing_tables:
            logger.info("Migration: creating verification_outcomes table")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS verification_outcomes (
                    outcome_id                      TEXT PRIMARY KEY,
                    investigation_id                 TEXT NOT NULL,
                    overall_status                  TEXT NOT NULL
                        CHECK(overall_status IN (
                            'PENDING', 'USEFUL', 'PARTIALLY_USEFUL',
                            'NOT_SUPPORTED', 'INCONCLUSIVE'
                        )),
                    recommendation_verification     TEXT
                        CHECK(recommendation_verification IN (
                            'SUPPORTED', 'PARTIALLY_SUPPORTED',
                            'NOT_SUPPORTED', 'UNKNOWN'
                        )),
                    investigation_area_verification  TEXT
                        CHECK(investigation_area_verification IN (
                            'SUPPORTED', 'PARTIALLY_SUPPORTED',
                            'NOT_SUPPORTED', 'UNKNOWN'
                        )),
                    hypothesis_verifications         TEXT,
                    field_notes                      TEXT,
                    verified_by                      TEXT,
                    verified_at                      TEXT,
                    created_at                       TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at                       TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_verification_investigation "
                "ON verification_outcomes(investigation_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_verification_status "
                "ON verification_outcomes(overall_status)"
            )
            conn.commit()

        # Migration 6: Investigation context snapshot for Phase 6 learning
        # Stores the environmental context at time of verification so the
        # learning engine can compute similarity between investigations.
        if "verification_outcomes" in existing_tables:
            ver_cols = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(verification_outcomes)"
                ).fetchall()
            }
            if "investigation_context" not in ver_cols:
                logger.info(
                    "Migration: adding investigation_context column to verification_outcomes"
                )
                conn.execute(
                    "ALTER TABLE verification_outcomes "
                    "ADD COLUMN investigation_context TEXT DEFAULT NULL"
                )
                conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a SQL statement.

        Args:
            sql: SQL statement with ? placeholders.
            params: Tuple of parameter values.

        Returns:
            sqlite3.Cursor with results.
        """
        conn = self._get_connection()
        return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement with many parameter sets.

        Args:
            sql: SQL statement with ? placeholders.
            params_list: List of parameter tuples.

        Returns:
            sqlite3.Cursor.
        """
        conn = self._get_connection()
        return conn.executemany(sql, params_list)

    def commit(self) -> None:
        """Commit the current transaction."""
        self._get_connection().commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self._get_connection().rollback()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def table_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table.

        Args:
            table_name: Name of the table to count.

        Returns:
            Number of rows in the table.
        """
        cursor = self.execute(f"SELECT COUNT(*) FROM {table_name}")  # noqa: S608
        row = cursor.fetchone()
        return row[0] if row else 0

    def fetch_one(self, sql: str, params: tuple | list = ()) -> dict | None:
        """Fetch a single row as a dictionary.

        Args:
            sql: SQL statement with ? placeholders.
            params: Parameter values.

        Returns:
            Dict of column_name → value, or None if no row.
        """
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetch_all(self, sql: str, params: tuple | list = ()) -> list[dict]:
        """Fetch all matching rows as a list of dictionaries.

        Args:
            sql: SQL statement with ? placeholders.
            params: Parameter values.

        Returns:
            List of dicts, one per row.
        """
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


# ── Database Singleton ────────────────────────────────────────────────

_database: Database | None = None


async def get_database() -> Database:
    """Get or create the singleton Database instance.

    Initializes the database on first call. Subsequent calls
    return the same instance.

    Returns:
        Database instance.
    """
    global _database  # noqa: PLW0603
    if _database is None:
        from ..core.config import get_settings

        settings = get_settings()
        # Extract path from sqlite:/// URLs
        db_path = settings.database_url.replace("sqlite:///", "")
        # Resolve relative paths against the backend/ directory so that
        # `data/lahore_pulse.db` always points to backend/data/ regardless
        # of the working directory used to launch uvicorn.
        db_path_obj = Path(db_path)
        if not db_path_obj.is_absolute():
            backend_root = Path(__file__).resolve().parent.parent.parent  # infrastructure → app → backend
            db_path_obj = backend_root / db_path_obj
        _database = Database(str(db_path_obj))
        _database.initialize()
    return _database


def reset_database() -> None:
    """Reset the singleton database instance.

    Used in testing to get a fresh database.
    """
    global _database  # noqa: PLW0603
    if _database is not None:
        _database.close()
    _database = None
