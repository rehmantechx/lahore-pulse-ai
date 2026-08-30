"""OpenAQ air quality data provider.

Implements the DataProvider interface for OpenAQ v3 API.

Research findings (Phase 0.5):
- API: api.openaq.org/v3
- Auth: X-API-Key header (registration at explore.openaq.org)
- Free tier: 60 requests/min, 2,000/hour
- S3 archive: s3://openaq-data-archive/ (no auth, no rate limits)
- Measured parameters: pm25, pm10, no2, so2, co, o3, bc, temperature, humidity
- Geospatial queries: bbox or point+radius (max 25km)
- Attribution required: OpenAQ + original data sources
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from ...core.config import Settings
from ...core.errors import DataSourceUnavailableError
from ...domain.models.common import DataSourceType
from ...domain.models.observation import DataSource

# ── OpenAQ Data Source Definition ─────────────────────────────────────

OPENAQ_SOURCE = DataSource(
    source_id="openaq",
    name="OpenAQ",
    provider="OpenAQ",
    source_type=DataSourceType.AIR_QUALITY,
    base_url="https://api.openaq.org",
    license="OpenAQ Terms of Use",
    documentation_url="https://docs.openaq.org",
)

# Source reliability: 4 — government/institutional stations
SOURCE_RELIABILITY = 4

# Parameter name mapping from OpenAQ to our standard names
PARAMETER_MAP = {
    "pm25": "pm25",
    "pm10": "pm10",
    "no2": "nitrogen_dioxide",
    "so2": "sulphur_dioxide",
    "co": "carbon_monoxide",
    "o3": "ozone",
    "bc": "black_carbon",
    "temperature": "temperature",
    "relativehumidity": "relative_humidity",
}

# Parameter ID mapping (from OpenAQ v3 API)
PARAMETER_IDS = {
    2: "pm25",
    1: "pm10",
    7: "no2",
    9: "so2",
    8: "co",
    10: "o3",
}


class OpenAQProvider:
    """OpenAQ air quality data provider.

    Fetches ground-truth PM2.5 and other pollutant measurements
    from OpenAQ's v3 API.

    Usage:
        provider = OpenAQProvider(settings)
        locations = await provider.discover_stations(
            latitude=31.5204,
            longitude=74.3587,
            radius_km=25.0,
        )
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.openaq_base_url
        self._api_key = settings.openaq_api_key

    @property
    def source(self) -> DataSource:
        return OPENAQ_SOURCE

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with API key."""
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    async def health_check(self) -> bool:
        """Check if OpenAQ API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v3/locations",
                    headers=self._get_headers(),
                    params={"limit": 1},
                )
                return resp.status_code in (200, 401)  # 401 means key needed but API is up
        except (httpx.HTTPError, TimeoutError):
            return False

    async def discover_stations(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 25.0,
    ) -> list[dict]:
        """Discover monitoring stations near a location.

        Uses OpenAQ's geospatial query with point+radius.

        Args:
            latitude: Center latitude.
            longitude: Center longitude.
            radius_km: Search radius in kilometers (max 25).

        Returns:
            List of station dicts with location metadata.

        Raises:
            DataSourceUnavailableError: If the API is unreachable.
        """
        radius_m = min(radius_km * 1000, 25000)

        params: dict[str, str | int | float] = {
            "coordinates": f"{latitude},{longitude}",
            "radius": radius_m,
            "limit": 100,
            "order_by": "distance",
        }

        logger.info(
            "Discovering OpenAQ stations",
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v3/locations",
                    headers=self._get_headers(),
                    params=params,
                )

                if resp.status_code == 401:
                    logger.warning("OpenAQ API key required but not provided")
                    return []
                if resp.status_code == 429:
                    raise DataSourceUnavailableError(
                        "openaq",
                        "Rate limit exceeded",
                    )
                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "openaq",
                        f"HTTP {resp.status_code}",
                    )

                data: dict[str, Any] = resp.json()
                results: list[dict[str, Any]] = data.get("results", [])

                logger.info("OpenAQ stations discovered", count=len(results))
                return results

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "openaq",
                f"HTTP error: {e}",
            ) from e

    async def fetch_measurements(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 25.0,
        parameter: str = "pm25",
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
        page: int = 1,
    ) -> dict:
        """Fetch air quality measurements from OpenAQ v3 API.

        Uses the geospatial measurements endpoint.

        Args:
            latitude: Center latitude.
            longitude: Center longitude.
            radius_km: Search radius in kilometers.
            parameter: Parameter name (pm25, pm10, no2, etc.).
            date_from: Start date (ISO 8601).
            date_to: End date (ISO 8601).
            limit: Maximum results per page.
            page: Page number.

        Returns:
            Raw API response dict.

        Raises:
            DataSourceUnavailableError: If the API is unreachable.
        """
        radius_m = min(radius_km * 1000, 25000)

        params: dict[str, str | int | float] = {
            "coordinates": f"{latitude},{longitude}",
            "radius": radius_m,
            "parameter": parameter,
            "limit": limit,
            "page": page,
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to

        logger.info(
            "Fetching OpenAQ measurements",
            parameter=parameter,
            latitude=latitude,
            longitude=longitude,
            page=page,
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.monotonic()
                resp = await client.get(
                    f"{self._base_url}/v3/measurements",
                    headers=self._get_headers(),
                    params=params,
                )
                elapsed_ms = (time.monotonic() - start_time) * 1000

                if resp.status_code == 401:
                    logger.warning("OpenAQ API key required")
                    return {"results": [], "meta": {"found": 0}}
                if resp.status_code == 429:
                    raise DataSourceUnavailableError(
                        "openaq",
                        "Rate limit exceeded",
                    )
                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "openaq",
                        f"HTTP {resp.status_code}",
                    )

                data: dict[str, Any] = resp.json()
                logger.info(
                    "OpenAQ measurements fetched",
                    elapsed_ms=f"{elapsed_ms:.0f}",
                    results=len(data.get("results", [])),
                    total=data.get("meta", {}).get("found", 0),
                )
                return data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "openaq",
                f"HTTP error: {e}",
            ) from e

    async def fetch_sensor_hours(
        self,
        sensor_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
        page: int = 1,
    ) -> dict:
        """Fetch hourly averages for a specific sensor.

        Uses the sensor hours endpoint for aggregated data.

        Args:
            sensor_id: OpenAQ sensor ID.
            date_from: Start date (ISO 8601).
            date_to: End date (ISO 8601).
            limit: Maximum results per page.
            page: Page number.

        Returns:
            Raw API response dict.
        """
        params: dict[str, str | int | float] = {
            "limit": limit,
            "page": page,
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self._base_url}/v3/sensors/{sensor_id}/hours",
                    headers=self._get_headers(),
                    params=params,
                )

                if resp.status_code == 401:
                    return {"results": [], "meta": {"found": 0}}
                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "openaq",
                        f"Sensor hours HTTP {resp.status_code}",
                    )
                sensor_data: dict[str, Any] = resp.json()
                return sensor_data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "openaq",
                f"HTTP error: {e}",
            ) from e

    def parse_measurement_response(
        self,
        response: dict,
    ) -> list[dict]:
        """Parse OpenAQ measurement response into observation dicts.

        Transforms OpenAQ v3 response format into normalized observation dicts.

        Args:
            response: Raw API response dict.

        Returns:
            List of observation dicts ready for validation.
        """
        results = response.get("results", [])
        observations = []

        for record in results:
            # Extract coordinates from the record
            coords = record.get("coordinates", {})
            if coords is None:
                coords = {}
            latitude = coords.get("latitude")
            longitude = coords.get("longitude")

            # Extract period/timestamp
            period = record.get("period", {})
            datetime_from = period.get("datetimeFrom", {})
            observed_at_str = datetime_from.get("utc") or datetime_from.get("local")

            if not observed_at_str or latitude is None or longitude is None:
                continue

            # Extract parameter info
            param_info = record.get("parameter", {})
            param_name = param_info.get("name", "")
            unit = param_info.get("units", "μg/m³")

            value = record.get("value")
            if value is None:
                continue

            # Extract location info
            location = record.get("location", {})
            station_id = str(location.get("id", "")) if isinstance(location, dict) else None
            station_name = location.get("name", "") if isinstance(location, dict) else ""

            observations.append(
                {
                    "parameter": param_name,
                    "value": float(value),
                    "unit": unit,
                    "observed_at": observed_at_str,
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "station_id": station_id,
                    "station_name": station_name,
                    "source_identifier": f"openaq|{param_name}|{observed_at_str}|{station_id or 'unknown'}",
                }
            )

        return observations
