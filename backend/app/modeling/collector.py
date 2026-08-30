"""Real data collection from Open-Meteo APIs.

Fetches genuine historical observations from Open-Meteo's Weather
Archive API and Air Quality API.  No synthetic data is ever produced.
Each data point comes directly from ECMWF IFS reanalysis or CAMS.

Usage (synchronous wrapper for the existing async providers):

    collector = DataCollector(settings, db)
    weather_count = await collector.collect_weather_data(start, end)
    aq_count = await collector.collect_aq_data(start, end)
"""

from __future__ import annotations

from datetime import UTC, date, datetime
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

# ── AQ variable metadata ─────────────────────────────────────────────

AQ_UNIT_MAP: dict[str, str] = {
    "pm10": "ug/m3",
    "pm2_5": "ug/m3",
    "nitrogen_dioxide": "ug/m3",
    "sulphur_dioxide": "ug/m3",
    "ozone": "ug/m3",
    "carbon_monoxide": "ug/m3",
}

# Source reliability for quality assessment
SOURCE_RELIABILITY = 5  # ECMWF IFS / CAMS


class DataCollector:
    """Collects real environmental data from Open-Meteo APIs and persists
    it to the SQLite database using the full 6-stage pipeline.

    This class bridges the existing provider infrastructure with the
    database, ensuring every observation passes through validation,
    normalization, and quality assessment before storage.

    Attributes:
        settings: Application settings (API URLs, coordinates).
        db: Database instance for persistence.
    """

    def __init__(self, settings: Settings, db: Database) -> None:
        self._settings = settings
        self._db = db

    async def collect_weather_data(
        self,
        start: date,
        end: date,
        variables: list[str] | None = None,
    ) -> int:
        """Fetch historical weather data from Open-Meteo Archive API
        and persist validated observations to the database.

        Uses the ECMWF IFS 9km reanalysis (2017–present) for
        highest-resolution weather data.

        Args:
            start: Start date (inclusive).
            end: End date (inclusive).
            variables: Weather variables to fetch.

        Returns:
            Number of observations persisted.
        """
        if variables is None:
            variables = [
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

        unit_map: dict[str, str] = {
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

        params: dict[str, str | int | float] = {
            "latitude": self._settings.lahore_latitude,
            "longitude": self._settings.lahore_longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(variables),
            "timezone": "UTC",
        }

        logger.info(
            "Collecting weather data from Open-Meteo",
            start=start.isoformat(),
            end=end.isoformat(),
            variables=len(variables),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{self._settings.open_meteo_base_url}/v1/archive",
                params=params,
            )
            if resp.status_code != 200:
                raise DataSourceUnavailableError(
                    "openmeteo",
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
            data: dict[str, Any] = resp.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            logger.warning("No time points in weather response")
            return 0

        count = 0
        for i, time_str in enumerate(times):
            for variable in hourly:
                if variable == "time" or variable == "units":
                    continue
                values = hourly[variable]
                if i >= len(values) or values[i] is None:
                    continue

                unit_str = unit_map.get(variable, "")
                if not unit_str:
                    continue

                # Stage 2: Validate
                valid, err = validate_observation_fields(
                    parameter=variable,
                    value=float(values[i]),
                    unit=unit_str,
                    observed_at=time_str,
                    latitude=self._settings.lahore_latitude,
                    longitude=self._settings.lahore_longitude,
                    station_id=None,
                )
                if not valid:
                    continue

                # Stage 3: Sanity check
                sane, err = validate_numerical_sanity(
                    parameter=variable,
                    value=float(values[i]),
                )
                if not sane:
                    continue

                # Generate deterministic ID
                obs_id = generate_observation_id(
                    source_id="openmeteo",
                    station_id=None,
                    parameter=variable,
                    observed_at=time_str,
                )

                # Stage 4: Normalize unit
                try:
                    unit_enum = normalize_unit(unit_str)
                except Exception:
                    continue

                # Stage 5: Quality
                quality = assess_quality(
                    parameter=variable,
                    value=float(values[i]),
                    source_reliability=SOURCE_RELIABILITY,
                )

                # Stage 6: Persist
                normalize_timestamp(time_str)
                retrieved = datetime.now(UTC)

                self._db.execute(
                    """INSERT OR IGNORE INTO observations
                    (observation_id, source_id, station_id, parameter, value, unit,
                     observed_at, retrieved_at, latitude, longitude, quality_status,
                     source_identifier, raw_response, created_at)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?)""",
                    (
                        obs_id,
                        "openmeteo",
                        variable,
                        float(values[i]),
                        unit_enum.value,
                        time_str,
                        retrieved.isoformat(),
                        self._settings.lahore_latitude,
                        self._settings.lahore_longitude,
                        quality.value,
                        f"openmeteo|{variable}|{time_str}",
                        retrieved.isoformat(),
                    ),
                )
                count += 1

        self._db.commit()
        logger.info("Weather data collection complete", observations_persisted=count)
        return count

    async def collect_aq_data(
        self,
        start: date,
        end: date,
        variables: list[str] | None = None,
    ) -> int:
        """Fetch air quality data from Open-Meteo Air Quality API
        and persist validated observations to the database.

        Uses CAMS European reanalysis (11km, 2013+) for historical
        air quality composition data.

        Args:
            start: Start date (inclusive).
            end: End date (inclusive).
            variables: AQ variables to fetch.

        Returns:
            Number of observations persisted.
        """
        if variables is None:
            variables = [
                "pm10",
                "pm2_5",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
                "carbon_monoxide",
            ]

        params: dict[str, str | int | float] = {
            "latitude": self._settings.lahore_latitude,
            "longitude": self._settings.lahore_longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(variables),
            "timezone": "UTC",
        }

        logger.info(
            "Collecting AQ data from Open-Meteo",
            start=start.isoformat(),
            end=end.isoformat(),
            variables=len(variables),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{self._settings.open_meteo_aq_url}/v1/air-quality",
                params=params,
            )
            if resp.status_code != 200:
                raise DataSourceUnavailableError(
                    "openmeteo_aq",
                    f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
            data: dict[str, Any] = resp.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            logger.warning("No time points in AQ response")
            return 0

        count = 0
        for i, time_str in enumerate(times):
            for variable in hourly:
                if variable == "time" or variable == "units":
                    continue
                values = hourly[variable]
                if i >= len(values) or values[i] is None:
                    continue

                unit_str = AQ_UNIT_MAP.get(variable, "ug/m3")

                # Stage 2: Validate
                valid, err = validate_observation_fields(
                    parameter=variable,
                    value=float(values[i]),
                    unit=unit_str,
                    observed_at=time_str,
                    latitude=self._settings.lahore_latitude,
                    longitude=self._settings.lahore_longitude,
                    station_id=None,
                )
                if not valid:
                    continue

                # Stage 3: Sanity check
                sane, err = validate_numerical_sanity(
                    parameter=variable,
                    value=float(values[i]),
                )
                if not sane:
                    continue

                # Generate deterministic ID
                obs_id = generate_observation_id(
                    source_id="openmeteo",
                    station_id=None,
                    parameter=variable,
                    observed_at=time_str,
                )

                # Stage 4: Normalize unit
                try:
                    unit_enum = normalize_unit(unit_str)
                except Exception:
                    continue

                # Stage 5: Quality
                quality = assess_quality(
                    parameter=variable,
                    value=float(values[i]),
                    source_reliability=SOURCE_RELIABILITY,
                )

                # Stage 6: Persist
                normalize_timestamp(time_str)
                retrieved = datetime.now(UTC)

                self._db.execute(
                    """INSERT OR IGNORE INTO observations
                    (observation_id, source_id, station_id, parameter, value, unit,
                     observed_at, retrieved_at, latitude, longitude, quality_status,
                     source_identifier, raw_response, created_at)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?)""",
                    (
                        obs_id,
                        "openmeteo",
                        variable,
                        float(values[i]),
                        unit_enum.value,
                        time_str,
                        retrieved.isoformat(),
                        self._settings.lahore_latitude,
                        self._settings.lahore_longitude,
                        quality.value,
                        f"openmeteo_aq|{variable}|{time_str}",
                        retrieved.isoformat(),
                    ),
                )
                count += 1

        self._db.commit()
        logger.info("AQ data collection complete", observations_persisted=count)
        return count

    def load_observations(
        self,
        parameter: str | None = None,
    ) -> list[dict]:
        """Load observations from the database as a list of dicts.

        Used by the dataset builder to create the modeling DataFrame.

        Args:
            parameter: Optional filter by parameter name.

        Returns:
            List of observation dicts with keys matching the DB schema.
        """
        if parameter:
            rows = self._db.fetch_all(
                "SELECT * FROM observations WHERE parameter = ? ORDER BY observed_at",
                (parameter,),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM observations ORDER BY observed_at",
            )

        return [dict(row) for row in rows] if rows else []
