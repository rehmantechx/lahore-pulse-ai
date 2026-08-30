"""Tests for the data ingestion pipeline stages.

Tests each pipeline stage independently:
1. Parse: JSON parsing
2. Validate: Field presence, numerical sanity
3. Normalize: Unit mapping, timestamp normalization
4. Quality: Quality assessment
5. Provenance: Observation creation

Uses captured real response structures (not fabricated data).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.core.errors import ErrorCode, InvalidExternalDataError
from app.domain.models.common import DataQuality, DataSourceType, MeasurementUnit
from app.domain.models.location import Coordinates
from app.domain.models.observation import DataSource
from app.infrastructure.pipeline import (
    UNIT_MAP,
    assess_quality,
    create_observation,
    generate_observation_id,
    normalize_timestamp,
    normalize_unit,
    parse_json_response,
    safe_json_dumps,
    validate_numerical_sanity,
    validate_observation_fields,
)

# ── Captured real API response structures ──────────────────────────────

OPENMETEO_HOURLY_RESPONSE = {
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
        "precipitation": "mm",
        "pressure_msl": "hPa",
        "wind_speed_10m": "km/h",
    },
    "hourly": {
        "time": [
            "2024-01-01T00:00",
            "2024-01-01T01:00",
            "2024-01-01T02:00",
        ],
        "temperature_2m": [8.5, 8.2, 7.9],
        "relative_humidity_2m": [72.0, 74.0, 76.0],
        "precipitation": [0.0, 0.0, 0.0],
        "pressure_msl": [1015.2, 1015.0, 1014.8],
        "wind_speed_10m": [12.5, 13.0, 11.8],
    },
}

OPENAQ_MEASUREMENTS_RESPONSE = {
    "meta": {
        "name": "openaq-api",
        "license": "CC BY 4.0",
        "website": "https://openaq.org",
        "page": 1,
        "limit": 10,
        "found": 3,
    },
    "results": [
        {
            "locationId": 1234,
            "location": "Lahore US Consulate",
            "parameter": "pm25",
            "value": 45.2,
            "unit": "µg/m³",
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
                    "local": "2024-01-01T06:00:00+05:00",
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


# ── Stage 1: Parse Tests ──────────────────────────────────────────────


class TestParseJsonResponse:
    """Tests for JSON parsing stage."""

    def test_parse_valid_json(self) -> None:
        """Valid JSON string parses to dict."""
        raw = json.dumps({"key": "value"})
        result = parse_json_response(raw)
        assert result == {"key": "value"}

    def test_parse_empty_object(self) -> None:
        """Empty JSON object parses correctly."""
        result = parse_json_response("{}")
        assert result == {}

    def test_parse_nested_json(self) -> None:
        """Nested JSON parses correctly."""
        result = parse_json_response(json.dumps(OPENMETEO_HOURLY_RESPONSE))
        assert "hourly" in result
        assert len(result["hourly"]["time"]) == 3

    def test_parse_array_json(self) -> None:
        """JSON array parses to list."""
        result = parse_json_response("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_parse_malformed_json_raises_error(self) -> None:
        """Malformed JSON raises InvalidExternalDataError."""
        with pytest.raises(InvalidExternalDataError) as exc_info:
            parse_json_response("{invalid json")
        assert exc_info.value.code == ErrorCode.INVALID_EXTERNAL_DATA

    def test_parse_empty_string_raises_error(self) -> None:
        """Empty string raises InvalidExternalDataError."""
        with pytest.raises(InvalidExternalDataError):
            parse_json_response("")

    def test_parse_json_with_unicode(self) -> None:
        """JSON with unicode characters parses correctly."""
        raw = json.dumps({"city": "Lahore", "unit": "μg/m³"})
        result = parse_json_response(raw)
        assert result["unit"] == "μg/m³"


# ── Stage 2: Validation Tests ─────────────────────────────────────────


class TestValidateObservationFields:
    """Tests for field validation stage."""

    def test_valid_observation_fields(self) -> None:
        """Complete observation passes validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=45.2,
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5204,
            longitude=74.3587,
            station_id="1234",
        )
        assert is_valid is True
        assert error is None

    def test_grid_cell_data_without_station(self) -> None:
        """Grid-cell data without station_id passes validation."""
        is_valid, error = validate_observation_fields(
            parameter="temperature_2m",
            value=8.5,
            unit="°C",
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5,
            longitude=74.35,
            station_id=None,
        )
        assert is_valid is True
        assert error is None

    def test_missing_parameter(self) -> None:
        """Missing parameter fails validation."""
        is_valid, error = validate_observation_fields(
            parameter=None,
            value=45.2,
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5204,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False
        assert "parameter" in error  # type: ignore[operator]

    def test_missing_value(self) -> None:
        """Missing value fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=None,
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5204,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False
        assert "value" in error  # type: ignore[operator]

    def test_missing_unit(self) -> None:
        """Missing unit fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=45.2,
            unit=None,
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5204,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False
        assert "unit" in error  # type: ignore[operator]

    def test_missing_timestamp(self) -> None:
        """Missing observed_at fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=45.2,
            unit="μg/m³",
            observed_at=None,
            latitude=31.5204,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False
        assert "observed_at" in error  # type: ignore[operator]

    def test_missing_latitude(self) -> None:
        """Missing latitude fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=45.2,
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=None,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False
        assert "latitude" in error  # type: ignore[operator]

    def test_latitude_out_of_range(self) -> None:
        """Latitude outside [-90, 90] fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=45.2,
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=95.0,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False
        assert "latitude" in error  # type: ignore[operator]

    def test_longitude_out_of_range(self) -> None:
        """Longitude outside [-180, 180] fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value=45.2,
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5204,
            longitude=200.0,
            station_id=None,
        )
        assert is_valid is False
        assert "longitude" in error  # type: ignore[operator]

    def test_non_numeric_value_fails(self) -> None:
        """Non-numeric value fails validation."""
        is_valid, error = validate_observation_fields(
            parameter="pm25",
            value="not_a_number",  # type: ignore[arg-type]
            unit="μg/m³",
            observed_at="2024-01-01T00:00:00Z",
            latitude=31.5204,
            longitude=74.3587,
            station_id=None,
        )
        assert is_valid is False


class TestValidateNumericalSanity:
    """Tests for numerical sanity validation."""

    def test_pm25_within_bounds(self) -> None:
        """PM2.5 within 0-1000 passes."""
        is_valid, error = validate_numerical_sanity(parameter="pm25", value=45.2)
        assert is_valid is True

    def test_pm25_zero(self) -> None:
        """PM2.5 at zero passes (clean air)."""
        is_valid, error = validate_numerical_sanity(parameter="pm25", value=0.0)
        assert is_valid is True

    def test_pm25_extreme_value_fails(self) -> None:
        """PM2.5 above 1000 fails (physically implausible)."""
        is_valid, error = validate_numerical_sanity(parameter="pm25", value=1500.0)
        assert is_valid is False
        assert "1000" in error  # type: ignore[operator]

    def test_pm25_negative_fails(self) -> None:
        """PM2.5 below 0 fails."""
        is_valid, error = validate_numerical_sanity(parameter="pm25", value=-5.0)
        assert is_valid is False

    def test_temperature_within_bounds(self) -> None:
        """Temperature within -60 to 60 passes."""
        is_valid, error = validate_numerical_sanity(parameter="temperature_2m", value=35.0)
        assert is_valid is True

    def test_temperature_extreme_fails(self) -> None:
        """Temperature above 60 fails."""
        is_valid, error = validate_numerical_sanity(parameter="temperature_2m", value=70.0)
        assert is_valid is False

    def test_humidity_within_bounds(self) -> None:
        """Humidity within 0-100 passes."""
        is_valid, error = validate_numerical_sanity(parameter="relative_humidity_2m", value=75.0)
        assert is_valid is True

    def test_humidity_over_100_fails(self) -> None:
        """Humidity above 100% fails."""
        is_valid, error = validate_numerical_sanity(parameter="relative_humidity_2m", value=105.0)
        assert is_valid is False

    def test_pressure_within_bounds(self) -> None:
        """Pressure within 870-1084 hPa passes."""
        is_valid, error = validate_numerical_sanity(parameter="pressure_msl", value=1013.25)
        assert is_valid is True

    def test_wind_speed_within_bounds(self) -> None:
        """Wind speed within 0-400 km/h passes."""
        is_valid, error = validate_numerical_sanity(parameter="wind_speed_10m", value=25.0)
        assert is_valid is True

    def test_unknown_parameter_passes(self) -> None:
        """Unknown parameter is not rejected (no bounds defined)."""
        is_valid, error = validate_numerical_sanity(parameter="unknown_param", value=42.0)
        assert is_valid is True

    def test_no2_within_bounds(self) -> None:
        """NO2 within 0-1000 passes."""
        is_valid, error = validate_numerical_sanity(parameter="nitrogen_dioxide", value=28.0)
        assert is_valid is True

    def test_co_within_bounds(self) -> None:
        """CO within 0-50000 passes."""
        is_valid, error = validate_numerical_sanity(parameter="carbon_monoxide", value=500.0)
        assert is_valid is True


# ── Stage 3: Normalization Tests ──────────────────────────────────────


class TestNormalizeUnit:
    """Tests for unit normalization."""

    def test_celsius_to_measurement_unit(self) -> None:
        """°C maps to DEGREES_CELSIUS."""
        assert normalize_unit("°C") == MeasurementUnit.DEGREES_CELSIUS

    def test_percentage(self) -> None:
        """% maps to PERCENTAGE."""
        assert normalize_unit("%") == MeasurementUnit.PERCENTAGE

    def test_hectopascals(self) -> None:
        """hPa maps to HECTOPASCALS."""
        assert normalize_unit("hPa") == MeasurementUnit.HECTOPASCALS

    def test_ug_m3(self) -> None:
        """μg/m3 maps to UG_M3."""
        assert normalize_unit("ug/m3") == MeasurementUnit.UG_M3

    def test_millimeters(self) -> None:
        """mm maps to MILLIMETERS."""
        assert normalize_unit("mm") == MeasurementUnit.MILLIMETERS

    def test_unknown_unit_raises_error(self) -> None:
        """Unrecognized unit raises InvalidExternalDataError."""
        with pytest.raises(InvalidExternalDataError):
            normalize_unit("banana_unit")

    def test_all_unit_map_keys_recognized(self) -> None:
        """Every key in UNIT_MAP can be normalized without error."""
        for unit_str in UNIT_MAP:
            result = normalize_unit(unit_str)
            assert isinstance(result, MeasurementUnit)


class TestNormalizeTimestamp:
    """Tests for timestamp normalization."""

    def test_utc_timestamp(self) -> None:
        """UTC timestamp is parsed correctly."""
        result = normalize_timestamp("2024-01-01T12:00:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.tzinfo is not None

    def test_offset_timestamp_normalized_to_utc(self) -> None:
        """Timestamp with +05:00 offset is converted to UTC."""
        result = normalize_timestamp("2024-01-01T12:00:00+05:00")
        assert result.hour == 7  # 12 - 5 = 7 UTC

    def test_naive_timestamp_assumed_utc(self) -> None:
        """Naive timestamp (no tz) is assumed UTC."""
        result = normalize_timestamp("2024-01-01T12:00:00")
        assert result.hour == 12
        assert result.tzinfo is not None

    def test_malformed_timestamp_raises_error(self) -> None:
        """Malformed timestamp raises InvalidExternalDataError."""
        with pytest.raises(InvalidExternalDataError):
            normalize_timestamp("not-a-date")

    def test_empty_timestamp_raises_error(self) -> None:
        """Empty string raises InvalidExternalDataError."""
        with pytest.raises(InvalidExternalDataError):
            normalize_timestamp("")


# ── Stage 4: Quality Assessment Tests ─────────────────────────────────


class TestAssessQuality:
    """Tests for data quality assessment."""

    def test_high_reliability_source_valid(self) -> None:
        """Source with reliability >= 4 → VALID."""
        result = assess_quality(
            parameter="pm25",
            value=45.2,
            source_reliability=5,
        )
        assert result == DataQuality.VALID

    def test_medium_reliability_source_unverified(self) -> None:
        """Source with reliability 3 → UNVERIFIED."""
        result = assess_quality(
            parameter="pm25",
            value=45.2,
            source_reliability=3,
        )
        assert result == DataQuality.UNVERIFIED

    def test_low_reliability_source_suspect(self) -> None:
        """Source with reliability < 3 → SUSPECT."""
        result = assess_quality(
            parameter="pm25",
            value=45.2,
            source_reliability=2,
        )
        assert result == DataQuality.SUSPECT

    def test_out_of_range_value_suspect(self) -> None:
        """Value out of numerical bounds → SUSPECT regardless of reliability."""
        result = assess_quality(
            parameter="pm25",
            value=1500.0,
            source_reliability=5,
        )
        assert result == DataQuality.SUSPECT

    def test_known_parameters_assessed(self) -> None:
        """Known parameters with valid values are assessed correctly."""
        for param, value in [
            ("temperature_2m", 25.0),
            ("relative_humidity_2m", 65.0),
            ("pressure_msl", 1013.0),
            ("wind_speed_10m", 15.0),
        ]:
            result = assess_quality(parameter=param, value=value, source_reliability=4)
            assert result == DataQuality.VALID


# ── Stage 5: Provenance Tests ─────────────────────────────────────────


class TestCreateObservation:
    """Tests for observation creation with provenance."""

    def _make_source(self) -> DataSource:
        return DataSource(
            source_id="test",
            name="Test Source",
            provider="Test",
            source_type=DataSourceType.WEATHER,
        )

    def test_observation_creation(self) -> None:
        """Observation can be created with all required fields."""
        obs = create_observation(
            source=self._make_source(),
            station_id=None,
            location=Coordinates(latitude=31.5204, longitude=74.3587),
            parameter="pm25",
            value=45.2,
            unit=MeasurementUnit.UG_M3,
            observed_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert obs.parameter == "pm25"
        assert obs.value == 45.2
        assert obs.quality == DataQuality.UNVERIFIED

    def test_observation_with_station(self) -> None:
        """Observation with station_id is stored correctly."""
        obs = create_observation(
            source=self._make_source(),
            station_id="station-123",
            location=Coordinates(latitude=31.5204, longitude=74.3587),
            parameter="pm10",
            value=85.0,
            unit=MeasurementUnit.UG_M3,
            observed_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        assert obs.station_id == "station-123"

    def test_observation_quality_override(self) -> None:
        """Quality can be set explicitly."""
        obs = create_observation(
            source=self._make_source(),
            station_id=None,
            location=Coordinates(latitude=31.5204, longitude=74.3587),
            parameter="temperature_2m",
            value=25.0,
            unit=MeasurementUnit.DEGREES_CELSIUS,
            observed_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            quality=DataQuality.VALID,
        )
        assert obs.quality == DataQuality.VALID

    def test_observation_deterministic_id(self) -> None:
        """Same inputs produce the same observation ID."""
        args = dict(
            source=self._make_source(),
            station_id=None,
            location=Coordinates(latitude=31.5204, longitude=74.3587),
            parameter="pm25",
            value=45.2,
            unit=MeasurementUnit.UG_M3,
            observed_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
        obs1 = create_observation(**args)
        obs2 = create_observation(**args)
        assert obs1.observation_id == obs2.observation_id


# ── Utility Tests ──────────────────────────────────────────────────────


class TestSafeJsonDumps:
    """Tests for JSON serialization utility."""

    def test_serialize_dict(self) -> None:
        """Dict serializes to valid JSON."""
        result = safe_json_dumps({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_serialize_list(self) -> None:
        """List serializes to valid JSON."""
        result = safe_json_dumps([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert safe_json_dumps(None) is None

    def test_serialize_datetime(self) -> None:
        """Datetime objects serialize via default=str."""
        result = safe_json_dumps({"time": datetime(2024, 1, 1, tzinfo=UTC)})
        assert "2024-01-01" in result

    def test_serialize_unicode(self) -> None:
        """Unicode characters are preserved."""
        result = safe_json_dumps({"unit": "μg/m³"})
        assert "μg/m³" in result


class TestGenerateObservationId:
    """Tests for deterministic ID generation."""

    def test_same_input_same_id(self) -> None:
        """Same inputs always produce the same ID."""
        id1 = generate_observation_id("openmeteo", "123", "pm25", "2024-01-01T00:00")
        id2 = generate_observation_id("openmeteo", "123", "pm25", "2024-01-01T00:00")
        assert id1 == id2

    def test_different_source_different_id(self) -> None:
        """Different source_id produces different ID."""
        id1 = generate_observation_id("openmeteo", "123", "pm25", "2024-01-01T00:00")
        id2 = generate_observation_id("openaq", "123", "pm25", "2024-01-01T00:00")
        assert id1 != id2

    def test_different_parameter_different_id(self) -> None:
        """Different parameter produces different ID."""
        id1 = generate_observation_id("openmeteo", "123", "pm25", "2024-01-01T00:00")
        id2 = generate_observation_id("openmeteo", "123", "pm10", "2024-01-01T00:00")
        assert id1 != id2

    def test_different_time_different_id(self) -> None:
        """Different timestamp produces different ID."""
        id1 = generate_observation_id("openmeteo", "123", "pm25", "2024-01-01T00:00")
        id2 = generate_observation_id("openmeteo", "123", "pm25", "2024-01-01T01:00")
        assert id1 != id2

    def test_none_station_id_treated_as_empty(self) -> None:
        """None station_id is treated as empty string."""
        id1 = generate_observation_id("src", None, "p", "t")
        id2 = generate_observation_id("src", "", "p", "t")
        assert id1 == id2

    def test_valid_uuid_format(self) -> None:
        """Generated ID is a valid UUID."""
        result = generate_observation_id("src", "station", "pm25", "2024-01-01T00:00")
        parts = result.split("-")
        assert len(parts) == 5
        assert len(result) == 36  # Standard UUID format with dashes
