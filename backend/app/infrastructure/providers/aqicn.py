"""AQICN/WAQI real-time air quality provider.

Implements the DataProvider interface for WAQI (World Air Quality Index) API.

Research findings (Phase 0.5):
- API: api.waqi.info
- Auth: ?token=<api_token> (free registration at aqicn.org)
- Real-time only: no historical archive
- 1,000 requests/day (free tier)
- Data includes: AQI, PM2.5, PM10, O3, NO2, SO2, CO, T, H, P
- Station-level data only (no city-averages)
- Lahore stations: 5+ (both government and private)

Use case: Supplementary real-time PM2.5 for live ingestion pipeline.
Not suitable for historical training data.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

import httpx
from loguru import logger

from ...core.config import Settings
from ...core.errors import DataSourceUnavailableError, InvalidExternalDataError
from ...domain.models.common import DataSourceType
from ...domain.models.observation import DataSource

# ── AQICN Data Source Definition ─────────────────────────────────────

AQICN_SOURCE = DataSource(
    source_id="aqicn",
    name="WAQI / AQICN",
    provider="World Air Quality Index Project",
    source_type=DataSourceType.AIR_QUALITY,
    base_url="https://api.waqi.info",
    license="CC BY-NC-SA 2.5",
    documentation_url="https://aqicn.org/data-platform/register/",
)

# Source reliability: 3 — real-time feed, variable station quality
SOURCE_RELIABILITY = 3

# WAQI station IDs for Lahore (verified from aqicn.org/map)
LAHORE_STATIONS = {
    "lahore-us-consulate": "lahore/us-consulate",
    "lahore-punjab-uet": "lahore/punjab-uet",
    "lahore-tahir-villa": "lahore/tahir-villa",
    "lahore-dha": "lahore/dha",
    "lahore-mall-road": "lahore/mall-road",
}

# AQI sub-measurement keys in WAQI response
AQ_KEYS = [
    "pm25",
    "pm10",
    "o3",
    "no2",
    "so2",
    "co",
    "t",
    "h",
    "p",  # temperature, humidity, pressure
]


class AQICNProvider:
    """AQICN/WAQI real-time air quality provider.

    Fetches real-time AQI and pollutant data from WAQI API.
    Limited to current readings — no historical data available.

    Usage:
        provider = AQICNProvider(settings)
        station_data = await provider.fetch_station("lahore/us-consulate")
        feed = await provider.fetch_feed("lahore")
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.aqicn_base_url
        self._token = settings.aqicn_api_token

    @property
    def source(self) -> DataSource:
        return AQICN_SOURCE

    def _build_url(self, path: str) -> str:
        """Build API URL with token."""
        return f"{self._base_url}/{path}/?token={self._token}"

    async def health_check(self) -> bool:
        """Check if WAQI API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self._build_url("feed/here"),
                )
                return resp.status_code == 200
        except (httpx.HTTPError, TimeoutError):
            return False

    async def fetch_station(
        self,
        station_id: str,
    ) -> dict:
        """Fetch real-time data from a specific WAQI station.

        Args:
            station_id: WAQI station ID (e.g., "lahore/us-consulate").

        Returns:
            Raw API response dict.

        Raises:
            DataSourceUnavailableError: If the API is unreachable.
            InvalidExternalDataError: If the response is invalid.
        """
        url = self._build_url(f"feed/{station_id}")

        logger.info("Fetching AQICN station data", station_id=station_id)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                start_time = time.monotonic()
                resp = await client.get(url)
                elapsed_ms = (time.monotonic() - start_time) * 1000

                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "aqicn",
                        f"HTTP {resp.status_code}",
                        details={"station_id": station_id},
                    )

                data: dict[str, Any] = resp.json()

                if data.get("status") != "ok":
                    raise InvalidExternalDataError(
                        details={
                            "error": "WAQI returned non-ok status",
                            "status": data.get("status"),
                            "data": str(data.get("data", ""))[:200],
                        },
                    )

                logger.info(
                    "AQICN station data fetched",
                    station_id=station_id,
                    elapsed_ms=f"{elapsed_ms:.0f}",
                )
                return data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "aqicn",
                f"HTTP error: {e}",
                details={"station_id": station_id},
            ) from e

    async def fetch_feed(
        self,
        search_term: str,
    ) -> dict:
        """Search and fetch AQI data for a location keyword.

        Uses WAQI's search endpoint to find stations matching
        a keyword (e.g., "lahore").

        Args:
            search_term: Location search term.

        Returns:
            Raw API response dict with matching stations.

        Raises:
            DataSourceUnavailableError: If the API is unreachable.
        """
        url = self._build_url(f"search/{search_term}")

        logger.info("Searching AQICN feed", search_term=search_term)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)

                if resp.status_code != 200:
                    raise DataSourceUnavailableError(
                        "aqicn",
                        f"Search HTTP {resp.status_code}",
                    )

                data: dict[str, Any] = resp.json()
                if data.get("status") != "ok":
                    raise InvalidExternalDataError(
                        details={
                            "error": "WAQI search returned non-ok status",
                            "status": data.get("status"),
                        },
                    )

                logger.info(
                    "AQICN search results",
                    search_term=search_term,
                    results=data.get("data", {}).get("count", 0)
                    if isinstance(data.get("data"), dict)
                    else len(data.get("data", [])),
                )
                return data

        except httpx.HTTPError as e:
            raise DataSourceUnavailableError(
                "aqicn",
                f"Search HTTP error: {e}",
            ) from e

    async def fetch_lahore_stations(self) -> list[dict]:
        """Fetch data from all known Lahore WAQI stations.

        Iterates through verified Lahore station IDs and fetches
        current data from each.

        Returns:
            List of raw station response dicts.
        """
        results = []
        for name, station_id in LAHORE_STATIONS.items():
            try:
                data = await self.fetch_station(station_id)
                results.append(data)
            except DataSourceUnavailableError as e:
                logger.warning(
                    "Failed to fetch Lahore station",
                    station=name,
                    error=str(e),
                )
        return results

    def parse_station_response(
        self,
        response: dict,
    ) -> list[dict]:
        """Parse WAQI station response into observation dicts.

        WAQI response structure:
        {
            "status": "ok",
            "data": {
                "aqi": 85,
                "idx": 1234,
                "city": {"name": "...", "geo": [lat, lon]},
                "time": {"iso": "2024-01-01T12:00:00+05:00"},
                "iaqi": {
                    "pm25": {"v": 85.0},
                    "pm10": {"v": 120.0},
                    "t": {"v": 22.5},
                    ...
                }
            }
        }

        Args:
            response: Raw WAQI API response.

        Returns:
            List of observation dicts ready for validation.
        """
        data = response.get("data", {})
        if not isinstance(data, dict):
            return []

        city = data.get("city", {})
        geo = city.get("geo", [None, None])
        time_info = data.get("time", {})
        observed_at = time_info.get("iso") or time_info.get("s")

        if not geo or len(geo) < 2 or geo[0] is None:
            return []

        latitude = float(geo[0])
        longitude = float(geo[1])
        station_idx = str(data.get("idx", ""))

        if not observed_at:
            return []

        observations = []

        # AQI composite value
        aqi_value = data.get("aqi")
        if aqi_value is not None:
            with contextlib.suppress(ValueError, TypeError):
                observations.append(
                    {
                        "parameter": "us_aqi",
                        "value": float(aqi_value),
                        "unit": "aqi_index",
                        "observed_at": observed_at,
                        "latitude": latitude,
                        "longitude": longitude,
                        "station_id": station_idx,
                        "station_name": city.get("name", ""),
                        "source_identifier": f"aqicn|us_aqi|{observed_at}|{station_idx}",
                    }
                )

        # Sub-measurements
        iaqi = data.get("iaqi", {})
        unit_map = {
            "pm25": "μg/m³",
            "pm10": "μg/m³",
            "o3": "μg/m³",
            "no2": "μg/m³",
            "so2": "μg/m³",
            "co": "mg/m³",
            "t": "°C",
            "h": "%",
            "p": "hPa",
        }

        for key in AQ_KEYS:
            if key in iaqi:
                value = iaqi[key].get("v")
                if value is not None:
                    try:
                        observations.append(
                            {
                                "parameter": key,
                                "value": float(value),
                                "unit": unit_map.get(key, ""),
                                "observed_at": observed_at,
                                "latitude": latitude,
                                "longitude": longitude,
                                "station_id": station_idx,
                                "station_name": city.get("name", ""),
                                "source_identifier": f"aqicn|{key}|{observed_at}|{station_idx}",
                            }
                        )
                    except (ValueError, TypeError):
                        continue

        return observations
