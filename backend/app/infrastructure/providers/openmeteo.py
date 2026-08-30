"""Open-Meteo weather data provider.

Implements the DataProvider interface for Open-Meteo's APIs:
- Historical Weather API (archive-api.open-meteo.com)
- Weather Forecast API (api.open-meteo.com)
- Air Quality API (air-quality-api.open-meteo.com)

Research findings (Phase 0.5):
- ECMWF IFS: 9km resolution, 2017+ (recommended for Lahore)
- ERA5: 0.25° resolution, 1940+ (longer history)
- CAMS Global: 45km, 2022+ (AQ forecasts)
- Free tier: 10,000 calls/day, 5,000/hour
- Licence: CC-BY 4.0 (attribution required)
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from ...core.config import Settings
from ...core.errors import DataSourceUnavailableError, InvalidExternalDataError
from ...domain.models.common import DataSourceType
from ...domain.models.observation import DataSource

# ── Open-Meteo Data Source Definition ────────────────────────────────

OPENMETEO_SOURCE = DataSource(
    source_id="openmeteo",
    name="Open-Meteo",
    provider="Open-Meteo GmbH",
    source_type=DataSourceType.WEATHER,
    base_url="https://open-meteo.com",
    license="CC-BY 4.0",
    documentation_url="https://open-meteo.com/en/docs",
)

# Source reliability: 5 (highest) — professional meteorological reanalysis
SOURCE_RELIABILITY = 5

# Key weather variables for PM2.5 prediction (from Phase 0.5 research)
DEFAULT_HOURLY_VARIABLES = [
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

# Unit mapping from Open-Meteo variable names to our units
VARIABLE_UNITS: dict[str, str] = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "dew_point_2m": "°C",
    "apparent_temperature": "°C",
    "precipitation": "mm",
    "rain": "mm",
    "cloud_cover": "%",
    "pressure_msl": "hPa",
    "surface_pressure": "hPa",
    "wind_speed_10m": "km/h",
    "wind_direction_10m": "deg",
    "wind_gusts_10m": "km/h",
    "shortwave_radiation": "W/m2",
    "vapour_pressure_deficit": "kPa",
    "soil_temperature_0_to_7cm": "°C",
    "soil_moisture_0_to_7cm": "m3/m3",
}


class OpenMeteoProvider:
    """Open-Meteo weather data provider.

    Fetches historical weather data and forecasts from Open-Meteo's APIs.
    Handles rate limiting, error responses, and response parsing.

    Usage:
        provider = OpenMeteoProvider(settings)
        historical = await provider.fetch_historical(
            latitude=31.5204,
            longitude=74.3587,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.open_meteo_base_url
        self._forecast_url = settings.open_meteo_forecast_url
        self._aq_url = settings.open_meteo_aq_url

    @property
    def source(self) -> DataSource:
        return OPENMETEO_SOURCE

    async def health_check(self) -> bool:
        """Check if Open-Meteo is reachable."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._forecast_url}/v1/forecast",
                    params={
                        "latitude": 31.5204,
                        "longitude": 74.3587,
                        "current_weather": "true",
                    },
                )
                return resp.status_code == 200
        except (httpx.HTTPError, TimeoutError):
            return False

    async def fetch_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        variables: list[str] | None = None,
        timezone: str = "UTC",
    ) -> dict:
        """Fetch historical weather data from Open-Meteo Archive API.

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            variables: List of hourly variables to fetch.
            timezone: Timezone for response timestamps.

        Returns:
            Raw API response dict with hourly data.

        Raises:
            DataSourceUnavailableError: If the API is unreachable.
            InvalidExternalDataError: If the response is unexpected.
        """
        if variables is None:
            variables = DEFAULT_HOURLY_VARIABLES

        params: dict[str, str | int | float] = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(variables),
            "timezone": timezone,
        }

        logger.info(
            "Fetching Open-Meteo historical weather",
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            variables=len(variables),
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.monotonic()
                resp = await client.get(
                    f"{self._base_url}/v1/archive",
                    params=params,
                )
                elapsed_ms = (time.monotonic() - start_time) * 1000

                if resp.status_code == 429:
                    raise DataSourceUnavailableError(
                        "openmeteo",
                        "Rate limit exceeded",
                        details={"retry_after": resp.headers.get("Retry-After")},
                    )
                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "openmeteo",
                        f"HTTP {resp.status_code}",
                        details={"response": resp.text[:500]},
                    )

                data: dict[str, Any] = resp.json()

                # Validate response structure
                if "hourly" not in data:
                    raise InvalidExternalDataError(
                        details={"error": "Missing 'hourly' key in response"},
                    )
                if "time" not in data["hourly"]:
                    raise InvalidExternalDataError(
                        details={"error": "Missing 'time' key in hourly data"},
                    )

                logger.info(
                    "Open-Meteo historical weather fetched",
                    elapsed_ms=f"{elapsed_ms:.0f}",
                    time_points=len(data["hourly"].get("time", [])),
                )
                return data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "openmeteo",
                f"HTTP error: {e}",
            ) from e
        except TimeoutError as e:
            raise DataSourceUnavailableError(
                "openmeteo",
                "Request timed out",
            ) from e

    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 5,
        past_days: int = 0,
        variables: list[str] | None = None,
    ) -> dict:
        """Fetch weather forecast from Open-Meteo Forecast API.

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            forecast_days: Number of forecast days (1-16).
            past_days: Number of recent past days to include (0-92).
                Useful for filling gaps between historical data and now.
            variables: List of hourly variables to fetch.

        Returns:
            Raw API response dict with hourly forecast data.

        Raises:
            DataSourceUnavailableError: If the API is unreachable.
            InvalidExternalDataError: If the response is unexpected.
        """
        if variables is None:
            variables = DEFAULT_HOURLY_VARIABLES

        params: dict[str, str | int | float] = {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": forecast_days,
            "hourly": ",".join(variables),
            "timezone": "UTC",
        }
        if past_days > 0:
            params["past_days"] = past_days

        logger.info(
            "Fetching Open-Meteo weather forecast",
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            past_days=past_days,
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._forecast_url}/v1/forecast",
                    params=params,
                )

                if resp.status_code == 429:
                    raise DataSourceUnavailableError(
                        "openmeteo",
                        "Rate limit exceeded",
                    )
                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "openmeteo",
                        f"HTTP {resp.status_code}",
                    )

                data: dict[str, Any] = resp.json()
                if "hourly" not in data:
                    raise InvalidExternalDataError(
                        details={"error": "Missing 'hourly' key in forecast response"},
                    )

                logger.info(
                    "Open-Meteo forecast fetched",
                    time_points=len(data["hourly"].get("time", [])),
                )
                return data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "openmeteo",
                f"HTTP error: {e}",
            ) from e

    async def fetch_air_quality(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 5,
        past_days: int = 0,
        variables: list[str] | None = None,
    ) -> dict:
        """Fetch air quality data from Open-Meteo Air Quality API.

        Uses CAMS European (11km, 2013+) or CAMS Global (45km, 2022+).

        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            forecast_days: Number of forecast days.
            past_days: Number of recent past days to include (0-92).
                Useful for filling gaps between historical data and now.
            variables: AQ variables to fetch.

        Returns:
            Raw API response dict with hourly AQ data.
        """
        if variables is None:
            variables = [
                "pm10",
                "pm2_5",
                "nitrogen_dioxide",
                "sulphur_dioxide",
                "ozone",
                "carbon_monoxide",
                "us_aqi",
            ]

        params: dict[str, str | int | float] = {
            "latitude": latitude,
            "longitude": longitude,
            "forecast_days": forecast_days,
            "hourly": ",".join(variables),
            "timezone": "UTC",
        }
        if past_days > 0:
            params["past_days"] = past_days

        logger.info(
            "Fetching Open-Meteo air quality",
            latitude=latitude,
            longitude=longitude,
            past_days=past_days,
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._aq_url}/v1/air-quality",
                    params=params,
                )

                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "openmeteo",
                        f"AQ API HTTP {resp.status_code}",
                    )

                data: dict[str, Any] = resp.json()
                logger.info("Open-Meteo air quality fetched")
                return data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "openmeteo",
                f"AQ HTTP error: {e}",
            ) from e

    def parse_historical_response(
        self,
        response: dict,
        latitude: float,
        longitude: float,
    ) -> list[dict]:
        """Parse Open-Meteo historical weather response into observation dicts.

        Transforms the response from:
            {"hourly": {"time": [...], "temperature_2m": [...], ...}}
        Into a list of individual observation dicts ready for validation.

        Args:
            response: Raw API response dict.
            latitude: Location latitude (from request).
            longitude: Location longitude (from request).

        Returns:
            List of observation dicts.
        """
        hourly = response.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return []

        observations = []
        for i, time_str in enumerate(times):
            for variable in hourly:
                if variable == "time" or variable == "units":
                    continue
                values = hourly[variable]
                if i >= len(values) or values[i] is None:
                    continue

                unit_str = VARIABLE_UNITS.get(variable, "")
                observations.append(
                    {
                        "parameter": variable,
                        "value": float(values[i]),
                        "unit": unit_str,
                        "observed_at": time_str,
                        "latitude": latitude,
                        "longitude": longitude,
                        "station_id": None,  # Grid-cell data, no station
                        "source_identifier": f"openmeteo|{variable}|{time_str}",
                    }
                )

        return observations

    def parse_forecast_response(
        self,
        response: dict,
        latitude: float,
        longitude: float,
    ) -> list[dict]:
        """Parse Open-Meteo forecast response into observation dicts.

        Same structure as historical response.
        """
        return self.parse_historical_response(response, latitude, longitude)

    def parse_aq_response(
        self,
        response: dict,
        latitude: float,
        longitude: float,
    ) -> list[dict]:
        """Parse Open-Meteo air quality response into observation dicts.

        AQ variables use different names and units.
        """
        hourly = response.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return []

        aq_unit_map = {
            "pm10": "μg/m³",
            "pm2_5": "μg/m³",
            "nitrogen_dioxide": "μg/m³",
            "sulphur_dioxide": "μg/m³",
            "ozone": "μg/m³",
            "carbon_monoxide": "μg/m³",
            "us_aqi": "aqi_index",
            "european_aqi": "aqi_index",
        }

        observations = []
        for i, time_str in enumerate(times):
            for variable in hourly:
                if variable == "time" or variable == "units":
                    continue
                values = hourly[variable]
                if i >= len(values) or values[i] is None:
                    continue

                unit_str = aq_unit_map.get(variable, "μg/m³")
                observations.append(
                    {
                        "parameter": variable,
                        "value": float(values[i]),
                        "unit": unit_str,
                        "observed_at": time_str,
                        "latitude": latitude,
                        "longitude": longitude,
                        "station_id": None,
                        "source_identifier": f"openmeteo_aq|{variable}|{time_str}",
                    }
                )

        return observations
