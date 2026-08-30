"""Data ingestion service.

Orchestrates the flow from provider adapters through the pipeline
to the database. Manages ingestion runs, idempotency, and failure handling.

Phases:
- Historical ingestion: Fetch from Open-Meteo archive + OpenAQ S3 archive
- Live ingestion: Fetch from Open-Meteo forecast + AQICN real-time
- Backfill: Re-fetch specific time ranges to fill gaps

Key guarantees:
- Raw responses stored verbatim (TEXT column)
- Deterministic observation IDs for idempotency
- Per-record failure isolation (one bad record doesn't block others)
- Every ingestion attempt creates a run record
- Acceptance rate tracked for quality monitoring
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from ...core.config import Settings
from ...core.errors import (
    ApplicationError,
    InvalidExternalDataError,
)
from ...domain.models.common import DataQuality
from ...domain.models.ingestion import (
    IngestionOperation,
    IngestionRecord,
    IngestionRun,
    IngestionStatus,
    RecordStatus,
)
from ...infrastructure.database import Database
from ...infrastructure.pipeline import (
    create_observation,
    generate_observation_id,
    normalize_timestamp,
    normalize_unit,
    safe_json_dumps,
    validate_numerical_sanity,
    validate_observation_fields,
)
from ...infrastructure.providers.aqicn import AQICN_SOURCE
from ...infrastructure.providers.openaq import OPENAQ_SOURCE
from ...infrastructure.providers.openmeteo import OPENMETEO_SOURCE


class IngestionService:
    """Data ingestion orchestration service.

    Coordinates:
    1. Creating an ingestion run
    2. Fetching data from providers
    3. Storing raw responses
    4. Running pipeline validation
    5. Persisting valid observations
    6. Recording ingestion metadata

    Usage:
        service = IngestionService(settings, db)
        run = await service.ingest_historical(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    """

    def __init__(self, settings: Settings, db: Database) -> None:
        self._settings = settings
        self._db = db

    async def ingest_historical_weather(
        self,
        provider: Any,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> IngestionRun:
        """Ingest historical weather data from Open-Meteo Archive API.

        Args:
            provider: OpenMeteoProvider instance.
            latitude: Location latitude.
            longitude: Location longitude.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).

        Returns:
            IngestionRun with results.
        """
        run = IngestionRun(operation=IngestionOperation.HISTORICAL)

        try:
            # Fetch raw response
            raw_response = await provider.fetch_historical(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
            )

            # Store run record
            self._db.execute(
                """INSERT INTO ingestion_runs (run_id, operation, provider, status, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.operation.value,
                    "openmeteo",
                    IngestionStatus.RUNNING.value,
                    run.started_at.isoformat(),
                ),
            )
            self._db.commit()

            # Parse response into observation dicts
            observations = provider.parse_historical_response(
                raw_response,
                latitude,
                longitude,
            )

            run.total_records = len(observations)

            # Process through pipeline
            accepted = 0
            rejected = 0

            for obs_dict in observations:
                record = self._process_observation(
                    obs_dict=obs_dict,
                    source_id="openmeteo",
                    raw_response=raw_response,
                )
                if record.status == RecordStatus.ACCEPTED:
                    accepted += 1
                else:
                    rejected += 1

            self._db.commit()

            run.finish(
                status=IngestionStatus.COMPLETED if rejected == 0 else IngestionStatus.PARTIAL,
                accepted_records=accepted,
                rejected_records=rejected,
            )

            # Update run in database
            self._update_run_status(run)

            logger.info(
                "Historical weather ingestion complete",
                run_id=run.run_id,
                accepted=accepted,
                rejected=rejected,
                duration=f"{run.duration_seconds:.1f}s" if run.duration_seconds else "N/A",
            )

        except ApplicationError as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error(
                "Historical weather ingestion failed",
                run_id=run.run_id,
                error=str(e),
            )
        except Exception as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error(
                "Historical weather ingestion failed with unexpected error",
                run_id=run.run_id,
                error=str(e),
            )

        return run

    async def ingest_historical_aq(
        self,
        provider: Any,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        parameter: str = "pm25",
    ) -> IngestionRun:
        """Ingest historical air quality data from OpenAQ.

        Args:
            provider: OpenAQProvider instance.
            latitude: Location latitude.
            longitude: Location longitude.
            start_date: Start date (ISO 8601).
            end_date: End date (ISO 8601).
            parameter: AQ parameter to fetch.

        Returns:
            IngestionRun with results.
        """
        run = IngestionRun(operation=IngestionOperation.HISTORICAL)

        try:
            self._db.execute(
                """INSERT INTO ingestion_runs (run_id, operation, provider, status, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.operation.value,
                    "openaq",
                    IngestionStatus.RUNNING.value,
                    run.started_at.isoformat(),
                ),
            )
            self._db.commit()

            raw_response = await provider.fetch_measurements(
                latitude=latitude,
                longitude=longitude,
                date_from=start_date,
                date_to=end_date,
                parameter=parameter,
                limit=1000,
            )

            observations = provider.parse_measurement_response(raw_response)
            run.total_records = len(observations)

            accepted = 0
            rejected = 0

            for obs_dict in observations:
                record = self._process_observation(
                    obs_dict=obs_dict,
                    source_id="openaq",
                    raw_response=raw_response,
                )
                if record.status == RecordStatus.ACCEPTED:
                    accepted += 1
                else:
                    rejected += 1

            self._db.commit()

            run.finish(
                status=IngestionStatus.COMPLETED if rejected == 0 else IngestionStatus.PARTIAL,
                accepted_records=accepted,
                rejected_records=rejected,
            )

            self._update_run_status(run)

            logger.info(
                "Historical AQ ingestion complete",
                run_id=run.run_id,
                parameter=parameter,
                accepted=accepted,
                rejected=rejected,
            )

        except ApplicationError as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Historical AQ ingestion failed", error=str(e))
        except Exception as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Historical AQ ingestion failed with unexpected error", error=str(e))

        return run

    async def ingest_live_aqicn(
        self,
        provider: Any,
    ) -> IngestionRun:
        """Ingest real-time data from AQICN/WAQI stations.

        Fetches from all known Lahore stations.

        Args:
            provider: AQICNProvider instance.

        Returns:
            IngestionRun with results.
        """
        run = IngestionRun(operation=IngestionOperation.LIVE)

        try:
            self._db.execute(
                """INSERT INTO ingestion_runs (run_id, operation, provider, status, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.operation.value,
                    "aqicn",
                    IngestionStatus.RUNNING.value,
                    run.started_at.isoformat(),
                ),
            )
            self._db.commit()

            station_responses = await provider.fetch_lahore_stations()
            total_observations = []

            for station_resp in station_responses:
                observations = provider.parse_station_response(station_resp)
                total_observations.extend(observations)

            run.total_records = len(total_observations)

            accepted = 0
            rejected = 0

            for obs_dict in total_observations:
                record = self._process_observation(
                    obs_dict=obs_dict,
                    source_id="aqicn",
                    raw_response=station_responses[0] if station_responses else {},
                )
                if record.status == RecordStatus.ACCEPTED:
                    accepted += 1
                else:
                    rejected += 1

            self._db.commit()

            run.finish(
                status=IngestionStatus.COMPLETED if rejected == 0 else IngestionStatus.PARTIAL,
                accepted_records=accepted,
                rejected_records=rejected,
            )

            self._update_run_status(run)

            logger.info(
                "Live AQICN ingestion complete",
                run_id=run.run_id,
                stations_fetched=len(station_responses),
                accepted=accepted,
                rejected=rejected,
            )

        except ApplicationError as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Live AQICN ingestion failed", error=str(e))
        except Exception as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Live AQICN ingestion failed with unexpected error", error=str(e))

        return run

    async def ingest_current_weather(
        self,
        provider: Any,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
        past_days: int = 3,
    ) -> IngestionRun:
        """Ingest recent weather data from the Open-Meteo Forecast API.

        The Forecast API includes past observations in its response
        (typically 2-3 days back), giving us near-current weather data
        without needing the archive API.

        Args:
            provider: OpenMeteoProvider instance.
            latitude: Location latitude.
            longitude: Location longitude.
            forecast_days: Days of forecast to fetch (includes past).
            past_days: Recent past days to include (0-92). Helps bridge
                gaps between historical data and the present.

        Returns:
            IngestionRun with results.
        """
        run = IngestionRun(operation=IngestionOperation.LIVE)

        try:
            # Fetch forecast with past days to bridge any gaps in historical data
            raw_response = await provider.fetch_forecast(
                latitude=latitude,
                longitude=longitude,
                forecast_days=forecast_days,
                past_days=past_days,
            )

            self._db.execute(
                """INSERT INTO ingestion_runs (run_id, operation, provider, status, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.operation.value,
                    "openmeteo",
                    IngestionStatus.RUNNING.value,
                    run.started_at.isoformat(),
                ),
            )
            self._db.commit()

            observations = provider.parse_forecast_response(
                raw_response, latitude, longitude
            )
            run.total_records = len(observations)

            accepted = 0
            rejected = 0

            for obs_dict in observations:
                record = self._process_observation(
                    obs_dict=obs_dict,
                    source_id="openmeteo",
                    raw_response=raw_response,
                )
                if record.status == RecordStatus.ACCEPTED:
                    accepted += 1
                else:
                    rejected += 1

            self._db.commit()

            run.finish(
                status=IngestionStatus.COMPLETED if rejected == 0 else IngestionStatus.PARTIAL,
                accepted_records=accepted,
                rejected_records=rejected,
            )
            self._update_run_status(run)

            logger.info(
                "Current weather ingestion complete",
                run_id=run.run_id,
                accepted=accepted,
                rejected=rejected,
            )

        except ApplicationError as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Current weather ingestion failed", error=str(e))
        except Exception as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Current weather ingestion failed with unexpected error", error=str(e))

        return run

    async def ingest_current_air_quality(
        self,
        provider: Any,
        latitude: float,
        longitude: float,
        forecast_days: int = 3,
        past_days: int = 3,
    ) -> IngestionRun:
        """Ingest recent air quality data from the Open-Meteo AQ API.

        Uses the CAMS European reanalysis forecast, which includes
        recent past observations alongside the forecast.

        Args:
            provider: OpenMeteoProvider instance.
            latitude: Location latitude.
            longitude: Location longitude.
            forecast_days: Days of AQ forecast to fetch.
            past_days: Recent past days to include (0-92). Helps bridge
                gaps between historical data and the present.

        Returns:
            IngestionRun with results.
        """
        run = IngestionRun(operation=IngestionOperation.LIVE)

        try:
            raw_response = await provider.fetch_air_quality(
                latitude=latitude,
                longitude=longitude,
                forecast_days=forecast_days,
                past_days=past_days,
            )

            self._db.execute(
                """INSERT INTO ingestion_runs (run_id, operation, provider, status, started_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    run.operation.value,
                    "openmeteo-aq",
                    IngestionStatus.RUNNING.value,
                    run.started_at.isoformat(),
                ),
            )
            self._db.commit()

            observations = provider.parse_aq_response(
                raw_response, latitude, longitude
            )
            run.total_records = len(observations)

            accepted = 0
            rejected = 0

            for obs_dict in observations:
                record = self._process_observation(
                    obs_dict=obs_dict,
                    source_id="openmeteo",
                    raw_response=raw_response,
                )
                if record.status == RecordStatus.ACCEPTED:
                    accepted += 1
                else:
                    rejected += 1

            self._db.commit()

            run.finish(
                status=IngestionStatus.COMPLETED if rejected == 0 else IngestionStatus.PARTIAL,
                accepted_records=accepted,
                rejected_records=rejected,
            )
            self._update_run_status(run)

            logger.info(
                "Current air quality ingestion complete",
                run_id=run.run_id,
                accepted=accepted,
                rejected=rejected,
            )

        except ApplicationError as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Current AQ ingestion failed", error=str(e))
        except Exception as e:
            run.finish(status=IngestionStatus.FAILED, accepted_records=0, rejected_records=0)
            logger.error("Current AQ ingestion failed with unexpected error", error=str(e))

        return run

    def _process_observation(
        self,
        obs_dict: dict,
        source_id: str,
        raw_response: dict,
    ) -> IngestionRecord:
        """Process a single observation through the pipeline.

        Steps:
        1. Validate required fields
        2. Validate numerical sanity
        3. Generate deterministic ID (idempotency)
        4. Normalize units and timestamps
        5. Assess data quality
        6. Create observation domain object
        7. Persist to database

        Args:
            obs_dict: Parsed observation dict from provider.
            source_id: Source identifier string.
            raw_response: Full raw API response.

        Returns:
            IngestionRecord with status.
        """
        from ...domain.models.location import Coordinates

        # Step 1: Validate required fields
        is_valid, error = validate_observation_fields(
            parameter=obs_dict.get("parameter"),
            value=obs_dict.get("value"),
            unit=obs_dict.get("unit"),
            observed_at=obs_dict.get("observed_at"),
            latitude=obs_dict.get("latitude"),
            longitude=obs_dict.get("longitude"),
            station_id=obs_dict.get("station_id"),
        )
        if not is_valid:
            return IngestionRecord(
                status=RecordStatus.REJECTED,
                error=error,
            )

        # Step 2: Validate numerical sanity
        param = obs_dict["parameter"]
        value = float(obs_dict["value"])
        is_valid, error = validate_numerical_sanity(parameter=param, value=value)
        if not is_valid:
            return IngestionRecord(
                status=RecordStatus.REJECTED,
                error=error,
            )

        # Step 3: Generate deterministic ID (SHA-256 hash → UUID)
        observation_id = generate_observation_id(
            source_id=source_id,
            station_id=obs_dict.get("station_id") or "",
            parameter=param,
            observed_at=obs_dict["observed_at"],
        )

        # Step 4: Normalize units and timestamps
        unit_str = obs_dict.get("unit", "")
        try:
            measurement_unit = normalize_unit(unit_str)
        except InvalidExternalDataError:
            return IngestionRecord(
                status=RecordStatus.REJECTED,
                error=f"Unrecognized unit: {unit_str}",
                observation_id=observation_id,
            )

        try:
            observed_at_utc = normalize_timestamp(obs_dict["observed_at"])
        except InvalidExternalDataError:
            return IngestionRecord(
                status=RecordStatus.REJECTED,
                error=f"Invalid timestamp: {obs_dict['observed_at']}",
                observation_id=observation_id,
            )

        # Step 5: Determine data quality based on source reliability
        source_reliability_map = {
            "openmeteo": 5,
            "openaq": 4,
            "aqicn": 3,
        }
        reliability = source_reliability_map.get(source_id, 3)

        if reliability >= 4:
            quality = DataQuality.VALID
        elif reliability >= 3:
            quality = DataQuality.UNVERIFIED
        else:
            quality = DataQuality.SUSPECT

        # Serialize raw response once for DB storage
        raw_response_str = safe_json_dumps(raw_response)

        # Step 6: Create observation domain object
        try:
            location = Coordinates(
                latitude=float(obs_dict["latitude"]),
                longitude=float(obs_dict["longitude"]),
            )
            observation = create_observation(
                source=OPENMETEO_SOURCE
                if source_id == "openmeteo"
                else OPENAQ_SOURCE
                if source_id == "openaq"
                else AQICN_SOURCE,
                station_id=obs_dict.get("station_id"),
                location=location,
                parameter=param,
                value=value,
                unit=measurement_unit,
                observed_at=observed_at_utc,
                source_identifier=obs_dict.get("source_identifier"),
                raw_response=raw_response_str,
                quality=quality,
            )
        except Exception as e:
            return IngestionRecord(
                status=RecordStatus.REJECTED,
                error=f"Failed to create observation: {e}",
                observation_id=observation_id,
            )

        # Step 7: Persist to database (idempotent via UNIQUE constraint)
        try:
            now_iso = datetime.now(UTC).isoformat()

            # Step 7a: Determine observation type from temporal semantics.
            # If observed_at > retrieved_at, this record was for a future
            # timestamp at ingest time — it is a FORECAST, not an observation.
            # The caller may also pass an explicit override via obs_dict.
            explicit_type = obs_dict.get("observation_type")
            if explicit_type in ("observation", "forecast", "model_prediction"):
                obs_type = explicit_type
            elif observed_at_utc.isoformat() > now_iso:
                obs_type = "forecast"
            else:
                obs_type = "observation"

            # Step 7b: Upsert with forecast→observation lifecycle support.
            # When a previously-future record (forecast) becomes historical,
            # we must UPDATE the existing row rather than silently ignoring it
            # via INSERT OR IGNORE (which would leave it stuck as 'forecast').
            if obs_type == "observation":
                existing = self._db.fetch_one(
                    "SELECT observation_type FROM observations "
                    "WHERE observation_id = ?",
                    (observation.observation_id,),
                )
                if existing is not None and existing["observation_type"] == "forecast":
                    # Forecast→Observation transition: update type + retrieved_at
                    self._db.execute(
                        "UPDATE observations "
                        "SET observation_type = ?, retrieved_at = ? "
                        "WHERE observation_id = ?",
                        (obs_type, now_iso, observation.observation_id),
                    )
                    return IngestionRecord(
                        status=RecordStatus.ACCEPTED,
                        observation_id=observation_id,
                    )

            self._db.execute(
                """INSERT OR IGNORE INTO observations
                   (observation_id, source_id, station_id, parameter, value, unit,
                    observed_at, retrieved_at, latitude, longitude, quality_status,
                    observation_type, source_identifier, raw_response, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    observation.observation_id,
                    observation.source.source_id,
                    observation.station_id,
                    observation.parameter,
                    observation.value,
                    observation.unit.value,
                    observation.timestamp.isoformat(),
                    now_iso,
                    observation.location.latitude,
                    observation.location.longitude,
                    observation.quality.value,
                    obs_type,
                    obs_dict.get("source_identifier", ""),
                    raw_response_str or "",
                    now_iso,
                ),
            )
            return IngestionRecord(
                status=RecordStatus.ACCEPTED,
                observation_id=observation_id,
            )
        except Exception as e:
            return IngestionRecord(
                status=RecordStatus.REJECTED,
                error=f"Database insert failed: {e}",
                observation_id=observation_id,
            )

    def _update_run_status(self, run: IngestionRun) -> None:
        """Update ingestion run status in database."""
        try:
            self._db.execute(
                """UPDATE ingestion_runs
                   SET status = ?, records_received = ?, records_accepted = ?,
                       records_rejected = ?, finished_at = ?
                   WHERE run_id = ?""",
                (
                    run.status.value,
                    run.total_records,
                    run.accepted_records,
                    run.rejected_records,
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.run_id,
                ),
            )
            self._db.commit()
        except Exception as e:
            logger.error("Failed to update run status", run_id=run.run_id, error=str(e))
