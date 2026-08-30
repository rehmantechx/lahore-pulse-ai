"""Historical data collection engine — chunked, resumable, idempotent.

Collects large-scale historical environmental data from Open-Meteo APIs
for Lahore, Pakistan. The engine:

1. Splits date ranges into configurable chunks (default 30 days)
2. Fetches each chunk with retries and backoff
3. Tracks progress via ingestion_runs (resumable on failure)
4. Is idempotent — same chunk re-fetched won't create duplicates
5. Respects Open-Meteo free-tier rate limits (10,000 daily calls)
6. Generates detailed collection reports

Provider Strategy:
- Weather: ECMWF IFS 9km (2017-01-01 to present) — ALL 16 variables
  - Fallback: ERA5 (1940-01-01) for pre-2017 data
- Air Quality: CAMS Global (2022-08-01 to present) — 6 variables
  - NO AQ data available before Aug 2022 for Lahore (non-European location)

Reference: Phase 3 Specification §5, §6, §7
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from loguru import logger

from ..core.config import Settings
from ..core.errors import DataSourceUnavailableError
from ..infrastructure.database import Database
from ..infrastructure.pipeline import (
    assess_quality,
    generate_observation_id,
    normalize_timestamp,
    normalize_unit,
    validate_numerical_sanity,
    validate_observation_fields,
)

# ── Constants ─────────────────────────────────────────────────────────

DEFAULT_CHUNK_DAYS = 30
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 60.0
RATE_LIMIT_DELAY_SECONDS = 0.5  # delay between API calls
SOURCE_RELIABILITY = 5  # ECMWF IFS / CAMS

# Weather variables and their unit strings
WEATHER_UNIT_MAP: dict[str, str] = {
    "temperature_2m": "deg_c",
    "relative_humidity_2m": "pct",
    "dew_point_2m": "deg_c",
    "apparent_temperature": "deg_c",
    "precipitation": "mm",
    "rain": "mm",
    "cloud_cover": "pct",
    "pressure_msl": "hPa",
    "surface_pressure": "hPa",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "deg",
    "wind_gusts_10m": "km/h",
    "shortwave_radiation": "W/m2",
    "vapour_pressure_deficit": "kPa",
    "soil_temperature_0_to_7cm": "deg_c",
    "soil_moisture_0_to_7cm": "m3/m3",
}

AQ_UNIT_MAP: dict[str, str] = {
    "pm10": "ug/m3",
    "pm2_5": "ug/m3",
    "nitrogen_dioxide": "ug/m3",
    "sulphur_dioxide": "ug/m3",
    "ozone": "ug/m3",
    "carbon_monoxide": "ug/m3",
}

# Default weather variables (all 16)
DEFAULT_WEATHER_VARIABLES: list[str] = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "vapour_pressure_deficit",
    "soil_temperature_0_to_7cm",
    "soil_moisture_0_to_7cm",
]

# Default AQ variables
DEFAULT_AQ_VARIABLES: list[str] = [
    "pm10",
    "pm2_5",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "carbon_monoxide",
]

# Provider availability limits (verified via API testing)
WEATHER_ECMWF_IFS_START = date(2017, 1, 1)
WEATHER_ERA5_START = date(1940, 1, 1)
AQ_CAMS_GLOBAL_START = date(2022, 8, 1)


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class ChunkResult:
    """Result of collecting a single time chunk."""

    chunk_id: str
    start_date: str
    end_date: str
    status: str  # "success", "partial", "failed"
    observations_fetched: int = 0
    observations_persisted: int = 0
    observations_skipped: int = 0
    observations_rejected: int = 0
    error_message: str | None = None
    duration_seconds: float = 0.0
    retries_used: int = 0


@dataclass
class CollectionReport:
    """Complete report of a historical data collection run."""

    run_id: str
    data_type: str  # "weather" or "aq"
    provider_model: str
    start_date: str
    end_date: str
    chunk_days: int
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0
    total_observations_fetched: int = 0
    total_observations_persisted: int = 0
    total_observations_skipped: int = 0
    total_observations_rejected: int = 0
    chunk_results: list[ChunkResult] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    total_duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Fraction of chunks that completed successfully."""
        if self.total_chunks == 0:
            return 0.0
        return self.completed_chunks / self.total_chunks

    @property
    def overall_persistence_rate(self) -> float:
        """Fraction of fetched observations that were persisted."""
        if self.total_observations_fetched == 0:
            return 0.0
        return self.total_observations_persisted / self.total_observations_fetched

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a dictionary for JSON storage."""
        return {
            "run_id": self.run_id,
            "data_type": self.data_type,
            "provider_model": self.provider_model,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "chunk_days": self.chunk_days,
            "total_chunks": self.total_chunks,
            "completed_chunks": self.completed_chunks,
            "failed_chunks": self.failed_chunks,
            "total_observations_fetched": self.total_observations_fetched,
            "total_observations_persisted": self.total_observations_persisted,
            "total_observations_skipped": self.total_observations_skipped,
            "total_observations_rejected": self.total_observations_rejected,
            "success_rate": self.success_rate,
            "persistence_rate": self.overall_persistence_rate,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration_seconds": self.total_duration_seconds,
            "errors": self.errors,
        }


# ── Chunk Generator ───────────────────────────────────────────────────


def generate_chunks(
    start: date,
    end: date,
    chunk_days: int = DEFAULT_CHUNK_DAYS,
) -> list[tuple[date, date]]:
    """Split a date range into non-overlapping chunks.

    Args:
        start: Start date (inclusive).
        end: End date (inclusive).
        chunk_days: Maximum days per chunk.

    Returns:
        List of (chunk_start, chunk_end) tuples, each <= chunk_days apart.
    """
    chunks: list[tuple[date, date]] = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


# ── Fetching with Retries ─────────────────────────────────────────────


def _fetch_weather_chunk_sync(
    client: httpx.Client,
    base_url: str,
    lat: float,
    lon: float,
    start: date,
    end: date,
    variables: list[str],
    model: str = "ecmwf_ifs",
) -> dict[str, Any]:
    """Fetch a single weather chunk with retries.

    Uses synchronous httpx for reliability in long-running collection.
    """
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(variables),
        "timezone": "UTC",
        "models": model,
    }

    last_error: Exception | None = None
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(f"{base_url}/v1/archive", params=params, timeout=60.0)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                # Rate limited — back off more aggressively
                logger.warning(
                    "Rate limited on weather API, backing off",
                    attempt=attempt,
                    backoff=backoff,
                )
                time.sleep(min(backoff * 2, MAX_BACKOFF_SECONDS))
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                continue
            # Other HTTP errors — retry
            last_error = DataSourceUnavailableError(
                "openmeteo_weather",
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
            logger.warning(
                "Weather fetch HTTP error, retrying",
                attempt=attempt,
                status=resp.status_code,
            )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            logger.warning(
                "Weather fetch network error, retrying",
                attempt=attempt,
                error=str(e),
            )

        time.sleep(min(backoff, MAX_BACKOFF_SECONDS))
        backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

    raise last_error or DataSourceUnavailableError(
        "openmeteo_weather",
        f"Failed after {MAX_RETRIES} retries",
    )


def _fetch_aq_chunk_sync(
    client: httpx.Client,
    base_url: str,
    lat: float,
    lon: float,
    start: date,
    end: date,
    variables: list[str],
    domain: str = "cams_global",
) -> dict[str, Any]:
    """Fetch a single AQ chunk with retries.

    Uses synchronous httpx for reliability in long-running collection.
    """
    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(variables),
        "timezone": "UTC",
        "domains": domain,
    }

    last_error: Exception | None = None
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(
                f"{base_url}/v1/air-quality",
                params=params,
                timeout=60.0,
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                logger.warning(
                    "Rate limited on AQ API, backing off",
                    attempt=attempt,
                    backoff=backoff,
                )
                time.sleep(min(backoff * 2, MAX_BACKOFF_SECONDS))
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                continue
            last_error = DataSourceUnavailableError(
                "openmeteo_aq",
                f"HTTP {resp.status_code}: {resp.text[:200]}",
            )
            logger.warning(
                "AQ fetch HTTP error, retrying",
                attempt=attempt,
                status=resp.status_code,
            )
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            logger.warning(
                "AQ fetch network error, retrying",
                attempt=attempt,
                error=str(e),
            )

        time.sleep(min(backoff, MAX_BACKOFF_SECONDS))
        backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

    raise last_error or DataSourceUnavailableError(
        "openmeteo_aq",
        f"Failed after {MAX_RETRIES} retries",
    )


# ── Persistence Helpers ───────────────────────────────────────────────


def _persist_weather_chunk(
    db: Database,
    data: dict[str, Any],
    lat: float,
    lon: float,
    unit_map: dict[str, str],
) -> tuple[int, int]:
    """Persist a weather API response into the observations table.

    Returns:
        Tuple of (persisted_count, skipped_count).
    """
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return 0, 0

    persisted = 0
    skipped = 0
    retrieved = datetime.now(UTC).isoformat()

    rows_to_insert: list[tuple] = []

    for i, time_str in enumerate(times):
        for variable in hourly:
            if variable in ("time", "units"):
                continue
            values = hourly[variable]
            if i >= len(values) or values[i] is None:
                skipped += 1
                continue

            value = float(values[i])
            unit_str = unit_map.get(variable, "")

            # Validate fields
            valid, _ = validate_observation_fields(
                parameter=variable,
                value=value,
                unit=unit_str,
                observed_at=time_str,
                latitude=lat,
                longitude=lon,
                station_id=None,
            )
            if not valid:
                skipped += 1
                continue

            # Numerical sanity
            sane, _ = validate_numerical_sanity(
                parameter=variable,
                value=value,
            )
            if not sane:
                skipped += 1
                continue

            obs_id = generate_observation_id(
                source_id="openmeteo",
                station_id=None,
                parameter=variable,
                observed_at=time_str,
            )

            try:
                unit_enum = normalize_unit(unit_str)
            except Exception:
                skipped += 1
                continue

            quality = assess_quality(
                parameter=variable,
                value=value,
                source_reliability=SOURCE_RELIABILITY,
            )

            rows_to_insert.append((
                obs_id,
                "openmeteo",
                variable,
                value,
                unit_enum.value,
                time_str,
                retrieved,
                lat,
                lon,
                quality.value,
                f"openmeteo|{variable}|{time_str}",
                retrieved,
            ))

    if rows_to_insert:
        db.executemany(
            """INSERT OR IGNORE INTO observations
            (observation_id, source_id, station_id, parameter, value, unit,
             observed_at, retrieved_at, latitude, longitude, quality_status,
             source_identifier, raw_response, created_at)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)""",
            rows_to_insert,
        )
        db.commit()
        persisted = len(rows_to_insert)

    return persisted, skipped


def _persist_aq_chunk(
    db: Database,
    data: dict[str, Any],
    lat: float,
    lon: float,
    unit_map: dict[str, str],
) -> tuple[int, int]:
    """Persist an AQ API response into the observations table.

    Returns:
        Tuple of (persisted_count, skipped_count).
    """
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return 0, 0

    persisted = 0
    skipped = 0
    retrieved = datetime.now(UTC).isoformat()

    rows_to_insert: list[tuple] = []

    for i, time_str in enumerate(times):
        for variable in hourly:
            if variable in ("time", "units"):
                continue
            values = hourly[variable]
            if i >= len(values) or values[i] is None:
                skipped += 1
                continue

            value = float(values[i])
            unit_str = unit_map.get(variable, "ug/m3")

            valid, _ = validate_observation_fields(
                parameter=variable,
                value=value,
                unit=unit_str,
                observed_at=time_str,
                latitude=lat,
                longitude=lon,
                station_id=None,
            )
            if not valid:
                skipped += 1
                continue

            sane, _ = validate_numerical_sanity(
                parameter=variable,
                value=value,
            )
            if not sane:
                skipped += 1
                continue

            obs_id = generate_observation_id(
                source_id="openmeteo",
                station_id=None,
                parameter=variable,
                observed_at=time_str,
            )

            try:
                unit_enum = normalize_unit(unit_str)
            except Exception:
                skipped += 1
                continue

            quality = assess_quality(
                parameter=variable,
                value=value,
                source_reliability=SOURCE_RELIABILITY,
            )

            rows_to_insert.append((
                obs_id,
                "openmeteo",
                variable,
                value,
                unit_enum.value,
                time_str,
                retrieved,
                lat,
                lon,
                quality.value,
                f"openmeteo_aq|{variable}|{time_str}",
                retrieved,
            ))

    if rows_to_insert:
        db.executemany(
            """INSERT OR IGNORE INTO observations
            (observation_id, source_id, station_id, parameter, value, unit,
             observed_at, retrieved_at, latitude, longitude, quality_status,
             source_identifier, raw_response, created_at)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)""",
            rows_to_insert,
        )
        db.commit()
        persisted = len(rows_to_insert)

    return persisted, skipped


# ── Ingestion Run Tracking ────────────────────────────────────────────


def _start_ingestion_run(
    db: Database,
    run_id: str,
    provider: str,
    operation: str,
    metadata: str = "",
) -> None:
    """Record the start of an ingestion run."""
    started = datetime.now(UTC).isoformat()
    db.execute(
        """INSERT INTO ingestion_runs
        (run_id, provider, operation, started_at, status, metadata)
        VALUES (?, ?, ?, ?, 'running', ?)""",
        (run_id, provider, operation, started, metadata),
    )
    db.commit()


def _finish_ingestion_run(
    db: Database,
    run_id: str,
    *,
    status: str = "completed",
    records_received: int = 0,
    records_accepted: int = 0,
    records_rejected: int = 0,
    records_duplicated: int = 0,
    error_message: str = "",
) -> None:
    """Record the completion of an ingestion run."""
    finished = datetime.now(UTC).isoformat()
    db.execute(
        """UPDATE ingestion_runs
        SET finished_at = ?, status = ?,
            records_received = ?, records_accepted = ?,
            records_rejected = ?, records_duplicated = ?,
            error_message = ?
        WHERE run_id = ?""",
        (
            finished,
            status,
            records_received,
            records_accepted,
            records_rejected,
            records_duplicated,
            error_message,
            run_id,
        ),
    )
    db.commit()


def _get_completed_chunks(
    db: Database,
    run_id: str,
) -> set[str]:
    """Get set of chunk IDs already completed in a given run.

    Used for resumability — skips chunks already processed.
    """
    rows = db.fetch_all(
        """SELECT source_identifier FROM ingestion_records
        WHERE run_id = ? AND status = 'accepted'""",
        (run_id,),
    )
    # Extract chunk IDs from source_identifier
    # source_identifier format: "chunk:<chunk_idx>|<variable>|<time>"
    chunks: set[str] = set()
    for row in rows:
        si = row.get("source_identifier", "")
        if si.startswith("chunk:"):
            parts = si.split("|")
            if parts:
                chunk_id_str = parts[0].replace("chunk:", "")
                chunks.add(chunk_id_str)
    return chunks


# ── HistoricalCollector ───────────────────────────────────────────────


class HistoricalCollector:
    """Collects historical environmental data using chunked, resumable,
    idempotent collection patterns.

    This is the main engine for Phase 3 historical data acquisition.
    It coordinates with the database's ingestion_runs and
    ingestion_records tables for tracking and resumability.

    Usage:
        settings = Settings()
        db = Database("data/lahore_pulse.db")
        db.initialize()
        collector = HistoricalCollector(settings, db)

        # Collect weather data from 2017-01-01 to today
        weather_report = collector.collect_weather(
            start=date(2017, 1, 1),
            end=date.today(),
        )

        # Collect AQ data from 2022-08-01 to today
        aq_report = collector.collect_aq(
            start=date(2022, 8, 1),
            end=date.today(),
        )
    """

    def __init__(
        self,
        settings: Settings,
        db: Database,
        chunk_days: int = DEFAULT_CHUNK_DAYS,
    ) -> None:
        """Initialize the historical collector.

        Args:
            settings: Application settings.
            db: Database instance.
            chunk_days: Number of days per collection chunk.
        """
        self._settings = settings
        self._db = db
        self._chunk_days = chunk_days
        self._lat = settings.lahore_latitude
        self._lon = settings.lahore_longitude

        # Ensure data sources are registered (required by FK constraints)
        self._ensure_data_sources()

    def _ensure_data_sources(self) -> None:
        """Ensure required data sources exist in the database.

        Registers Open-Meteo weather and AQ sources if they don't exist.
        Required because observations have a foreign key to data_sources.
        """
        sources = [
            (
                "openmeteo",
                "Open-Meteo",
                "Open-Meteo GmbH",
                "weather",
                "https://open-meteo.com",
                "CC-BY 4.0",
                "https://open-meteo.com/en/docs",
            ),
            (
                "openmeteo_aq",
                "Open-Meteo Air Quality",
                "Open-Meteo GmbH / Copernicus CAMS",
                "air_quality",
                "https://air-quality-api.open-meteo.com",
                "CC-BY 4.0",
                "https://open-meteo.com/en/docs/air-quality-api",
            ),
        ]
        for src in sources:
            existing = self._db.fetch_one(
                "SELECT source_id FROM data_sources WHERE source_id = ?",
                (src[0],),
            )
            if not existing:
                self._db.execute(
                    """INSERT OR IGNORE INTO data_sources
                    (source_id, name, provider, source_type, base_url, license, documentation_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    src,
                )
        self._db.commit()

    def collect_weather(
        self,
        start: date,
        end: date,
        variables: list[str] | None = None,
        model: str = "ecmwf_ifs",
        run_id: str | None = None,
    ) -> CollectionReport:
        """Collect historical weather data in chunks.

        Args:
            start: Start date (inclusive). Must be >= 2017-01-01 for ECMWF IFS.
            end: End date (inclusive). Must be <= today.
            variables: Weather variables to fetch (defaults to all 16).
            model: Open-Meteo model to use (ecmwf_ifs or era5).
            run_id: Optional run ID for resumability. If None, generates new.

        Returns:
            CollectionReport with detailed results.
        """
        if variables is None:
            variables = list(DEFAULT_WEATHER_VARIABLES)

        if run_id is None:
            run_id = f"weather_{model}_{uuid.uuid4().hex[:12]}"

        # Clamp dates to provider availability
        if model == "ecmwf_ifs":
            effective_start = max(start, WEATHER_ECMWF_IFS_START)
        elif model == "era5":
            effective_start = max(start, WEATHER_ERA5_START)
        else:
            effective_start = start

        # Don't fetch future data
        today = date.today()
        effective_end = min(end, today)

        if effective_start > effective_end:
            logger.warning(
                "Weather collection range is empty",
                requested_start=start.isoformat(),
                requested_end=end.isoformat(),
                effective_start=effective_start.isoformat(),
                effective_end=effective_end.isoformat(),
            )
            return CollectionReport(
                run_id=run_id,
                data_type="weather",
                provider_model=model,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                chunk_days=self._chunk_days,
            )

        chunks = generate_chunks(effective_start, effective_end, self._chunk_days)

        logger.info(
            "Starting weather collection",
            run_id=run_id,
            model=model,
            start=effective_start.isoformat(),
            end=effective_end.isoformat(),
            total_chunks=len(chunks),
            chunk_days=self._chunk_days,
            variables=len(variables),
        )

        report = CollectionReport(
            run_id=run_id,
            data_type="weather",
            provider_model=model,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            chunk_days=self._chunk_days,
            total_chunks=len(chunks),
            started_at=datetime.now(UTC).isoformat(),
        )

        # Track ingestion run in DB
        _start_ingestion_run(
            self._db,
            run_id,
            provider=f"openmeteo_{model}",
            operation=f"historical_weather_{len(variables)}vars",
            metadata=f"chunk_days={self._chunk_days},model={model}",
        )

        # Check for previously completed chunks (resumability)
        completed_chunk_ids = _get_completed_chunks(self._db, run_id)
        if completed_chunk_ids:
            logger.info(
                "Resuming weather collection",
                previously_completed=len(completed_chunk_ids),
                total_chunks=len(chunks),
            )

        t_start = time.monotonic()

        with httpx.Client(timeout=60.0) as client:
            for idx, (chunk_start, chunk_end) in enumerate(chunks):
                chunk_id = f"{idx:04d}"

                # Skip if already completed
                if chunk_id in completed_chunk_ids:
                    report.completed_chunks += 1
                    continue

                t_chunk = time.monotonic()
                result = ChunkResult(
                    chunk_id=chunk_id,
                    start_date=chunk_start.isoformat(),
                    end_date=chunk_end.isoformat(),
                    status="failed",
                )

                try:
                    data = _fetch_weather_chunk_sync(
                        client=client,
                        base_url=self._settings.open_meteo_base_url,
                        lat=self._lat,
                        lon=self._lon,
                        start=chunk_start,
                        end=chunk_end,
                        variables=variables,
                        model=model,
                    )

                    persisted, skipped = _persist_weather_chunk(
                        self._db,
                        data,
                        self._lat,
                        self._lon,
                        WEATHER_UNIT_MAP,
                    )

                    result.status = "success"
                    result.observations_persisted = persisted
                    result.observations_skipped = skipped
                    result.observations_fetched = persisted + skipped

                    report.completed_chunks += 1
                    report.total_observations_persisted += persisted
                    report.total_observations_skipped += skipped
                    report.total_observations_fetched += result.observations_fetched

                    logger.info(
                        "Weather chunk completed",
                        chunk_id=chunk_id,
                        period=f"{chunk_start} to {chunk_end}",
                        persisted=persisted,
                        skipped=skipped,
                    )

                except Exception as e:
                    result.status = "failed"
                    result.error_message = str(e)[:500]
                    report.failed_chunks += 1
                    report.errors.append(
                        f"Chunk {chunk_id} ({chunk_start} to {chunk_end}): {e!s}"
                    )
                    logger.error(
                        "Weather chunk failed",
                        chunk_id=chunk_id,
                        period=f"{chunk_start} to {chunk_end}",
                        error=str(e),
                    )

                result.duration_seconds = time.monotonic() - t_chunk
                report.chunk_results.append(result)

                # Rate limit delay
                time.sleep(RATE_LIMIT_DELAY_SECONDS)

        # Finalize ingestion run
        _finish_ingestion_run(
            self._db,
            run_id,
            status="completed" if report.failed_chunks == 0 else "partial",
            records_received=report.total_observations_fetched,
            records_accepted=report.total_observations_persisted,
            records_rejected=report.total_observations_skipped,
            records_duplicated=0,
            error_message="; ".join(report.errors[:5]) if report.errors else "",
        )

        report.finished_at = datetime.now(UTC).isoformat()
        report.total_duration_seconds = time.monotonic() - t_start

        logger.info(
            "Weather collection complete",
            run_id=run_id,
            model=model,
            total_chunks=report.total_chunks,
            completed=report.completed_chunks,
            failed=report.failed_chunks,
            total_persisted=report.total_observations_persisted,
            duration=f"{report.total_duration_seconds:.1f}s",
        )

        return report

    def collect_aq(
        self,
        start: date,
        end: date,
        variables: list[str] | None = None,
        domain: str = "cams_global",
        run_id: str | None = None,
    ) -> CollectionReport:
        """Collect historical air quality data in chunks.

        Args:
            start: Start date (inclusive). Must be >= 2022-08-01 for CAMS Global.
            end: End date (inclusive). Must be <= today.
            variables: AQ variables to fetch (defaults to all 6).
            domain: Open-Meteo AQ domain (cams_global for Lahore).
            run_id: Optional run ID for resumability. If None, generates new.

        Returns:
            CollectionReport with detailed results.
        """
        if variables is None:
            variables = list(DEFAULT_AQ_VARIABLES)

        if run_id is None:
            run_id = f"aq_{domain}_{uuid.uuid4().hex[:12]}"

        # Clamp to CAMS Global availability
        effective_start = max(start, AQ_CAMS_GLOBAL_START)
        today = date.today()
        effective_end = min(end, today)

        if effective_start > effective_end:
            logger.warning(
                "AQ collection range is empty",
                requested_start=start.isoformat(),
                requested_end=end.isoformat(),
                effective_start=effective_start.isoformat(),
                effective_end=effective_end.isoformat(),
            )
            return CollectionReport(
                run_id=run_id,
                data_type="aq",
                provider_model=domain,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                chunk_days=self._chunk_days,
            )

        chunks = generate_chunks(effective_start, effective_end, self._chunk_days)

        logger.info(
            "Starting AQ collection",
            run_id=run_id,
            domain=domain,
            start=effective_start.isoformat(),
            end=effective_end.isoformat(),
            total_chunks=len(chunks),
            chunk_days=self._chunk_days,
            variables=len(variables),
        )

        report = CollectionReport(
            run_id=run_id,
            data_type="aq",
            provider_model=domain,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            chunk_days=self._chunk_days,
            total_chunks=len(chunks),
            started_at=datetime.now(UTC).isoformat(),
        )

        _start_ingestion_run(
            self._db,
            run_id,
            provider=f"openmeteo_aq_{domain}",
            operation=f"historical_aq_{len(variables)}vars",
            metadata=f"chunk_days={self._chunk_days},domain={domain}",
        )

        completed_chunk_ids = _get_completed_chunks(self._db, run_id)
        if completed_chunk_ids:
            logger.info(
                "Resuming AQ collection",
                previously_completed=len(completed_chunk_ids),
                total_chunks=len(chunks),
            )

        t_start = time.monotonic()

        with httpx.Client(timeout=60.0) as client:
            for idx, (chunk_start, chunk_end) in enumerate(chunks):
                chunk_id = f"{idx:04d}"

                if chunk_id in completed_chunk_ids:
                    report.completed_chunks += 1
                    continue

                t_chunk = time.monotonic()
                result = ChunkResult(
                    chunk_id=chunk_id,
                    start_date=chunk_start.isoformat(),
                    end_date=chunk_end.isoformat(),
                    status="failed",
                )

                try:
                    data = _fetch_aq_chunk_sync(
                        client=client,
                        base_url=self._settings.open_meteo_aq_url,
                        lat=self._lat,
                        lon=self._lon,
                        start=chunk_start,
                        end=chunk_end,
                        variables=variables,
                        domain=domain,
                    )

                    persisted, skipped = _persist_aq_chunk(
                        self._db,
                        data,
                        self._lat,
                        self._lon,
                        AQ_UNIT_MAP,
                    )

                    result.status = "success"
                    result.observations_persisted = persisted
                    result.observations_skipped = skipped
                    result.observations_fetched = persisted + skipped

                    report.completed_chunks += 1
                    report.total_observations_persisted += persisted
                    report.total_observations_skipped += skipped
                    report.total_observations_fetched += result.observations_fetched

                    logger.info(
                        "AQ chunk completed",
                        chunk_id=chunk_id,
                        period=f"{chunk_start} to {chunk_end}",
                        persisted=persisted,
                        skipped=skipped,
                    )

                except Exception as e:
                    result.status = "failed"
                    result.error_message = str(e)[:500]
                    report.failed_chunks += 1
                    report.errors.append(
                        f"Chunk {chunk_id} ({chunk_start} to {chunk_end}): {e!s}"
                    )
                    logger.error(
                        "AQ chunk failed",
                        chunk_id=chunk_id,
                        period=f"{chunk_start} to {chunk_end}",
                        error=str(e),
                    )

                result.duration_seconds = time.monotonic() - t_chunk
                report.chunk_results.append(result)

                time.sleep(RATE_LIMIT_DELAY_SECONDS)

        _finish_ingestion_run(
            self._db,
            run_id,
            status="completed" if report.failed_chunks == 0 else "partial",
            records_received=report.total_observations_fetched,
            records_accepted=report.total_observations_persisted,
            records_rejected=report.total_observations_skipped,
            records_duplicated=0,
            error_message="; ".join(report.errors[:5]) if report.errors else "",
        )

        report.finished_at = datetime.now(UTC).isoformat()
        report.total_duration_seconds = time.monotonic() - t_start

        logger.info(
            "AQ collection complete",
            run_id=run_id,
            domain=domain,
            total_chunks=report.total_chunks,
            completed=report.completed_chunks,
            failed=report.failed_chunks,
            total_persisted=report.total_observations_persisted,
            duration=f"{report.total_duration_seconds:.1f}s",
        )

        return report

    def get_database_stats(self) -> dict[str, Any]:
        """Get current database statistics for monitoring progress."""
        total_obs = self._db.table_row_count("observations")
        total_runs = self._db.table_row_count("ingestion_runs")

        # Count by parameter
        param_counts = self._db.fetch_all(
            """SELECT parameter, COUNT(*) as cnt
            FROM observations
            GROUP BY parameter
            ORDER BY cnt DESC"""
        )

        # Date range
        date_range = self._db.fetch_one(
            """SELECT MIN(observed_at) as earliest, MAX(observed_at) as latest
            FROM observations"""
        )

        # Count by source
        source_counts = self._db.fetch_all(
            """SELECT source_id, COUNT(*) as cnt
            FROM observations
            GROUP BY source_id
            ORDER BY cnt DESC"""
        )

        # Recent ingestion runs
        recent_runs = self._db.fetch_all(
            """SELECT run_id, provider, operation, status,
                      records_accepted, records_rejected,
                      started_at, finished_at
            FROM ingestion_runs
            ORDER BY started_at DESC
            LIMIT 10"""
        )

        return {
            "total_observations": total_obs,
            "total_ingestion_runs": total_runs,
            "parameter_counts": {r["parameter"]: r["cnt"] for r in param_counts},
            "date_range": dict(date_range) if date_range else {},
            "source_counts": {r["source_id"]: r["cnt"] for r in source_counts},
            "recent_runs": recent_runs,
        }
