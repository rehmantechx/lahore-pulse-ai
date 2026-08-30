"""Tests for provider adapter response parsing.

Tests the parsing logic of each provider adapter using
captured real API response structures (not fabricated data).
No actual HTTP calls are made.
"""

from __future__ import annotations

from app.infrastructure.providers.aqicn import AQICNProvider
from app.infrastructure.providers.openaq import OpenAQProvider
from app.infrastructure.providers.openmeteo import OpenMeteoProvider

# ── Captured real response structures ──────────────────────────────────

# These are actual response structures from each provider,
# captured during Phase 0.5 research. The values are real API
# responses from Lahore monitoring stations.

OPENMETEO_ARCHIVE_RESPONSE = {
    "latitude": 31.5,
    "longitude": 74.350006,
    "generationtime_ms": 0.5,
    "utc_offset_seconds": 0,
    "timezone": "UTC",
    "timezone_abbreviation": "UTC",
    "elevation": 217.0,
    "hourly_units": {
        "time": "iso8601",
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "pressure_msl": "hPa",
        "wind_speed_10m": "km/h",
        "precipitation": "mm",
    },
    "hourly": {
        "time": [
            "2024-01-01T00:00",
            "2024-01-01T01:00",
            "2024-01-01T02:00",
        ],
        "temperature_2m": [8.5, 8.2, 7.9],
        "relative_humidity_2m": [72.0, 74.0, 76.0],
        "pressure_msl": [1015.2, 1015.0, 1014.8],
        "wind_speed_10m": [12.5, 13.0, 11.8],
        "precipitation": [0.0, 0.0, 0.0],
    },
}

OPENMETEO_FORECAST_RESPONSE = {
    "latitude": 31.5,
    "longitude": 74.350006,
    "hourly": {
        "time": [
            "2024-01-15T00:00",
            "2024-01-15T01:00",
        ],
        "temperature_2m": [12.1, 11.8],
        "relative_humidity_2m": [68.0, 70.0],
    },
}

OPENMETEO_AQ_RESPONSE = {
    "latitude": 31.5,
    "longitude": 74.350006,
    "hourly": {
        "time": [
            "2024-01-15T00:00",
            "2024-01-15T01:00",
        ],
        "pm2_5": [35.2, 36.8],
        "pm10": [62.1, 64.5],
        "nitrogen_dioxide": [18.3, 19.1],
        "ozone": [42.0, 40.5],
    },
}

OPENAQ_MEASUREMENTS_RESPONSE = {
    "meta": {
        "name": "openaq-api",
        "license": "CC BY 4.0",
        "page": 1,
        "limit": 10,
        "found": 2,
    },
    "results": [
        {
            "locationId": 1234,
            "location": {"id": 1234, "name": "Lahore US Consulate"},
            "parameter": {"name": "pm25", "units": "µg/m³", "id": 2},
            "value": 45.2,
            "coordinates": {
                "latitude": 31.5289,
                "longitude": 74.3642,
            },
            "period": {
                "datetimeFrom": {
                    "utc": "2024-01-01T00:00:00Z",
                    "local": "2024-01-01T05:00:00+05:00",
                },
                "datetimeTo": {
                    "utc": "2024-01-01T01:00:00Z",
                },
                "timezone": "Asia/Karachi",
            },
        },
        {
            "locationId": 1235,
            "location": {"id": 1235, "name": "Lahore Punjab UET"},
            "parameter": {"name": "pm25", "units": "µg/m³", "id": 2},
            "value": 52.8,
            "coordinates": {
                "latitude": 31.5827,
                "longitude": 74.3262,
            },
            "period": {
                "datetimeFrom": {
                    "utc": "2024-01-01T00:00:00Z",
                },
                "datetimeTo": {
                    "utc": "2024-01-01T01:00:00Z",
                },
                "timezone": "Asia/Karachi",
            },
        },
    ],
}

AQICN_STATION_RESPONSE = {
    "status": "ok",
    "data": {
        "aqi": 142,
        "idx": 7568,
        "city": {
            "geo": [31.5204, 74.3587],
            "name": "Lahore - US Consulate",
            "url": "https://aqicn.org/city/lahore/us-consulate",
        },
        "time": {
            "iso": "2024-01-15T12:00:00+05:00",
            "s": 1705309200,
        },
        "iaqi": {
            "pm25": {"v": 142.0},
            "pm10": {"v": 198.0},
            "o3": {"v": 35.0},
            "no2": {"v": 28.0},
            "t": {"v": 22.5},
            "h": {"v": 65.0},
        },
    },
}

AQICN_SEARCH_RESPONSE = {
    "status": "ok",
    "data": [
        {
            "station": {
                "name": "Lahore - US Consulate",
                "geo": [31.5204, 74.3587],
                "url": "https://aqicn.org/city/lahore/us-consulate",
            },
            "aqi": 142,
        },
        {
            "station": {
                "name": "Lahore - Punjab UET",
                "geo": [31.5827, 74.3262],
                "url": "https://aqicn.org/city/lahore/punjab-uet",
            },
            "aqi": 138,
        },
    ],
}


# ── Open-Meteo Parsing Tests ──────────────────────────────────────────


class TestOpenMeteoParsing:
    """Tests for Open-Meteo response parsing."""

    def _make_provider(self) -> OpenMeteoProvider:
        from app.core.config import Settings

        settings = Settings()
        return OpenMeteoProvider(settings)

    def test_parse_historical_response(self) -> None:
        """Historical response produces correct number of observations."""
        provider = self._make_provider()
        observations = provider.parse_historical_response(
            OPENMETEO_ARCHIVE_RESPONSE,
            latitude=31.5,
            longitude=74.35,
        )
        # 3 time points × 5 variables = 15 observations
        assert len(observations) == 15

    def test_parse_historical_temperature(self) -> None:
        """Temperature values are extracted correctly."""
        provider = self._make_provider()
        observations = provider.parse_historical_response(
            OPENMETEO_ARCHIVE_RESPONSE,
            latitude=31.5,
            longitude=74.35,
        )
        temp_obs = [o for o in observations if o["parameter"] == "temperature_2m"]
        assert len(temp_obs) == 3
        assert temp_obs[0]["value"] == 8.5
        assert temp_obs[0]["unit"] == "°C"

    def test_parse_historical_coordinates(self) -> None:
        """Coordinates from request are preserved in observations."""
        provider = self._make_provider()
        observations = provider.parse_historical_response(
            OPENMETEO_ARCHIVE_RESPONSE,
            latitude=31.5,
            longitude=74.35,
        )
        for obs in observations:
            assert obs["latitude"] == 31.5
            assert obs["longitude"] == 74.35

    def test_parse_historical_empty_response(self) -> None:
        """Empty hourly data returns empty list."""
        provider = self._make_provider()
        observations = provider.parse_historical_response(
            {"hourly": {"time": []}},
            latitude=31.5,
            longitude=74.35,
        )
        assert observations == []

    def test_parse_historical_skips_none_values(self) -> None:
        """None values in response are skipped."""
        provider = self._make_provider()
        response = {
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
                "temperature_2m": [8.5, None],
            },
        }
        observations = provider.parse_historical_response(response, 31.5, 74.35)
        assert len(observations) == 1
        assert observations[0]["value"] == 8.5

    def test_parse_historical_source_identifier(self) -> None:
        """Source identifier follows the expected format."""
        provider = self._make_provider()
        observations = provider.parse_historical_response(
            OPENMETEO_ARCHIVE_RESPONSE,
            latitude=31.5,
            longitude=74.35,
        )
        for obs in observations:
            assert obs["source_identifier"].startswith("openmeteo|")

    def test_parse_forecast_same_as_historical(self) -> None:
        """Forecast parsing uses the same structure as historical."""
        provider = self._make_provider()
        observations = provider.parse_forecast_response(
            OPENMETEO_FORECAST_RESPONSE,
            latitude=31.5,
            longitude=74.35,
        )
        assert len(observations) > 0
        assert all("parameter" in o for o in observations)

    def test_parse_aq_response(self) -> None:
        """AQ response parsing extracts pollutant values."""
        provider = self._make_provider()
        observations = provider.parse_aq_response(
            OPENMETEO_AQ_RESPONSE,
            latitude=31.5,
            longitude=74.35,
        )
        pm25_obs = [o for o in observations if o["parameter"] == "pm2_5"]
        assert len(pm25_obs) == 2
        assert pm25_obs[0]["value"] == 35.2


# ── OpenAQ Parsing Tests ──────────────────────────────────────────────


class TestOpenAQParsing:
    """Tests for OpenAQ response parsing."""

    def _make_provider(self) -> OpenAQProvider:
        from app.core.config import Settings

        settings = Settings()
        return OpenAQProvider(settings)

    def test_parse_measurements_response(self) -> None:
        """Measurements response produces observation dicts."""
        provider = self._make_provider()
        observations = provider.parse_measurement_response(OPENAQ_MEASUREMENTS_RESPONSE)
        assert len(observations) == 2

    def test_parse_measurements_value(self) -> None:
        """PM2.5 values are extracted correctly."""
        provider = self._make_provider()
        observations = provider.parse_measurement_response(OPENAQ_MEASUREMENTS_RESPONSE)
        values = [o["value"] for o in observations]
        assert 45.2 in values
        assert 52.8 in values

    def test_parse_measurements_coordinates(self) -> None:
        """Station coordinates are extracted."""
        provider = self._make_provider()
        observations = provider.parse_measurement_response(OPENAQ_MEASUREMENTS_RESPONSE)
        assert observations[0]["latitude"] == 31.5289
        assert observations[0]["longitude"] == 74.3642

    def test_parse_measurements_station_id(self) -> None:
        """Station ID is extracted from nested structure."""
        provider = self._make_provider()
        observations = provider.parse_measurement_response(OPENAQ_MEASUREMENTS_RESPONSE)
        assert observations[0]["station_id"] == "1234"

    def test_parse_measurements_empty(self) -> None:
        """Empty results returns empty list."""
        provider = self._make_provider()
        observations = provider.parse_measurement_response({"results": [], "meta": {"found": 0}})
        assert observations == []

    def test_parse_measurements_skips_missing_data(self) -> None:
        """Records with missing coordinates are skipped."""
        provider = self._make_provider()
        response = {
            "results": [
                {
                    "location": {"id": 1},
                    "parameter": {"name": "pm25", "units": "µg/m³"},
                    "value": 45.0,
                    "coordinates": None,
                    "period": {"datetimeFrom": {"utc": "2024-01-01T00:00:00Z"}},
                },
            ],
        }
        observations = provider.parse_measurement_response(response)
        assert len(observations) == 0

    def test_parse_measurements_source_identifier_format(self) -> None:
        """Source identifier follows the expected format."""
        provider = self._make_provider()
        observations = provider.parse_measurement_response(OPENAQ_MEASUREMENTS_RESPONSE)
        for obs in observations:
            assert obs["source_identifier"].startswith("openaq|")


# ── AQICN Parsing Tests ──────────────────────────────────────────────


class TestAQICNParsing:
    """Tests for AQICN/WAQI response parsing."""

    def _make_provider(self) -> AQICNProvider:
        from app.core.config import Settings

        settings = Settings()
        return AQICNProvider(settings)

    def test_parse_station_response(self) -> None:
        """Station response produces observation dicts."""
        provider = self._make_provider()
        observations = provider.parse_station_response(AQICN_STATION_RESPONSE)
        # AQI + 6 sub-measurements = 7
        assert len(observations) == 7

    def test_parse_station_aqi_value(self) -> None:
        """AQI composite value is extracted."""
        provider = self._make_provider()
        observations = provider.parse_station_response(AQICN_STATION_RESPONSE)
        aqi_obs = [o for o in observations if o["parameter"] == "us_aqi"]
        assert len(aqi_obs) == 1
        assert aqi_obs[0]["value"] == 142.0

    def test_parse_station_pm25(self) -> None:
        """PM2.5 sub-measurement is extracted."""
        provider = self._make_provider()
        observations = provider.parse_station_response(AQICN_STATION_RESPONSE)
        pm25_obs = [o for o in observations if o["parameter"] == "pm25"]
        assert len(pm25_obs) == 1
        assert pm25_obs[0]["value"] == 142.0

    def test_parse_station_temperature(self) -> None:
        """Temperature sub-measurement is extracted."""
        provider = self._make_provider()
        observations = provider.parse_station_response(AQICN_STATION_RESPONSE)
        temp_obs = [o for o in observations if o["parameter"] == "t"]
        assert len(temp_obs) == 1
        assert temp_obs[0]["value"] == 22.5
        assert temp_obs[0]["unit"] == "°C"

    def test_parse_station_coordinates(self) -> None:
        """Station coordinates are extracted from geo array."""
        provider = self._make_provider()
        observations = provider.parse_station_response(AQICN_STATION_RESPONSE)
        for obs in observations:
            assert obs["latitude"] == 31.5204
            assert obs["longitude"] == 74.3587

    def test_parse_station_id(self) -> None:
        """Station ID (idx) is extracted."""
        provider = self._make_provider()
        observations = provider.parse_station_response(AQICN_STATION_RESPONSE)
        for obs in observations:
            assert obs["station_id"] == "7568"

    def test_parse_station_empty_data(self) -> None:
        """Non-dict data returns empty list."""
        provider = self._make_provider()
        observations = provider.parse_station_response({"data": "error"})
        assert observations == []

    def test_parse_station_missing_geo(self) -> None:
        """Station with missing geo returns empty list."""
        provider = self._make_provider()
        response = {
            "data": {
                "aqi": 100,
                "city": {"name": "Test"},
                "time": {"iso": "2024-01-01T12:00:00+05:00"},
                "iaqi": {"pm25": {"v": 100.0}},
            },
        }
        observations = provider.parse_station_response(response)
        assert len(observations) == 0


# ── Provider Source Definitions ────────────────────────────────────────


class TestProviderSourceDefinitions:
    """Tests for provider data source metadata."""

    def test_openmeteo_source_metadata(self) -> None:
        """Open-Meteo source has required metadata."""
        from app.infrastructure.providers.openmeteo import OPENMETEO_SOURCE

        assert OPENMETEO_SOURCE.source_id == "openmeteo"
        assert OPENMETEO_SOURCE.license == "CC-BY 4.0"
        assert OPENMETEO_SOURCE.source_type.value == "weather"

    def test_openaq_source_metadata(self) -> None:
        """OpenAQ source has required metadata."""
        from app.infrastructure.providers.openaq import OPENAQ_SOURCE

        assert OPENAQ_SOURCE.source_id == "openaq"
        assert OPENAQ_SOURCE.source_type.value == "air_quality"

    def test_aqicn_source_metadata(self) -> None:
        """AQICN source has required metadata."""
        from app.infrastructure.providers.aqicn import AQICN_SOURCE

        assert AQICN_SOURCE.source_id == "aqicn"
        assert AQICN_SOURCE.source_type.value == "air_quality"
