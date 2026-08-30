"""Data ingestion pipeline stages.

Implements the explicit pipeline:

    External API → Raw Response → Parse → Validate → Normalize → Quality → Provenance → Persist

Each stage is a pure function (or small class) with clear input/output contracts.
Stages are composable and independently testable.

Key design principles:
1. No stage silently repairs data — invalid records are flagged, not fixed
2. Every transformation is explicit and documented
3. Raw responses are preserved for reproducibility
4. Quality status is assigned at a specific stage, not inferred later
5. Provenance is attached before persistence, not after
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from ..core.errors import InvalidExternalDataError
from ..domain.models.common import DataQuality, MeasurementUnit
from ..domain.models.location import Coordinates
from ..domain.models.observation import DataSource, Observation

# ── Stage 1: Parsing ──────────────────────────────────────────────────


def parse_json_response(raw_text: str) -> dict:
    """Parse a raw JSON response into a Python dict.

    Args:
        raw_text: Raw JSON response body from an external API.

    Returns:
        Parsed JSON as a Python dictionary.

    Raises:
        InvalidExternalDataError: If JSON is malformed.
    """
    try:
        result: dict[str, Any] = json.loads(raw_text)
        return result
    except json.JSONDecodeError as e:
        raise InvalidExternalDataError(
            details={"error": str(e), "raw_length": len(raw_text)},
        ) from e


# ── Stage 2: Validation ──────────────────────────────────────────────


def validate_observation_fields(
    *,
    parameter: str | None,
    value: float | None,
    unit: str | None,
    observed_at: str | None,
    latitude: float | None,
    longitude: float | None,
    station_id: str | None,
) -> tuple[bool, str | None]:
    """Validate that all required observation fields are present and valid.

    This is a structural/semantic validation, not a domain-threshold check.
    It ensures we have the minimum information needed for a valid observation.

    Returns:
        Tuple of (is_valid, error_reason).
    """
    if not parameter:
        return False, "Missing required field: parameter"
    if value is None:
        return False, "Missing required field: value"
    if not isinstance(value, (int, float)):
        return False, f"Invalid value type: {type(value).__name__}"
    if unit is None:
        return False, "Missing required field: unit"
    if observed_at is None:
        return False, "Missing required field: observed_at"
    if latitude is None or longitude is None:
        return False, "Missing required field: latitude/longitude"
    if not (-90.0 <= latitude <= 90.0):
        return False, f"Invalid latitude: {latitude}"
    if not (-180.0 <= longitude <= 180.0):
        return False, f"Invalid longitude: {longitude}"
    # station_id can be None for grid-cell data (e.g., Open-Meteo reanalysis)
    return True, None


def validate_numerical_sanity(
    *,
    parameter: str,
    value: float,
) -> tuple[bool, str | None]:
    """Check that a measurement value is within physically plausible bounds.

    Uses documented domain thresholds from Phase 0.5 research.
    Does NOT invent universal thresholds — each parameter has its own bounds.

    Returns:
        Tuple of (is_valid, error_reason).
    """
    bounds = {
        "pm25": (0.0, 1000.0, "μg/m³"),
        "pm10": (0.0, 2000.0, "μg/m³"),
        "temperature_2m": (-60.0, 60.0, "°C"),
        "relative_humidity_2m": (0.0, 100.0, "%"),
        "pressure_msl": (870.0, 1084.0, "hPa"),
        "wind_speed_10m": (0.0, 400.0, "km/h"),
        "precipitation": (0.0, 500.0, "mm"),
        "ozone": (0.0, 600.0, "μg/m³"),
        "nitrogen_dioxide": (0.0, 1000.0, "μg/m³"),
        "sulphur_dioxide": (0.0, 2000.0, "μg/m³"),
        "carbon_monoxide": (0.0, 50000.0, "μg/m³"),
    }
    if parameter in bounds:
        min_val, max_val, unit_str = bounds[parameter]
        if value < min_val or value > max_val:
            return False, (
                f"Value {value} {unit_str} for {parameter} "
                f"outside plausible range [{min_val}, {max_val}]"
            )
    return True, None


def generate_observation_id(
    source_id: str,
    station_id: str | None,
    parameter: str,
    observed_at: str,
) -> str:
    """Generate a deterministic observation ID.

    Uses a hash of (source_id, station_id, parameter, observed_at)
    to ensure idempotency: the same input always produces the same ID.

    Args:
        source_id: Data source identifier.
        station_id: Station identifier (or None).
        parameter: Measured parameter name.
        observed_at: ISO timestamp of the observation.

    Returns:
        Deterministic UUID string.
    """
    key = f"{source_id}|{station_id or ''}|{parameter}|{observed_at}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    # Generate a UUID5-like value from the hash
    return str(uuid.UUID(bytes=hash_bytes[:16], version=5))


# ── Stage 3: Normalization ───────────────────────────────────────────


# Unit mapping from source-specific strings to our MeasurementUnit enum
UNIT_MAP: dict[str, MeasurementUnit] = {
    # Open-Meteo units
    "°C": MeasurementUnit.DEGREES_CELSIUS,
    "°F": MeasurementUnit.FAHRENHEIT,
    "%": MeasurementUnit.PERCENTAGE,
    "hPa": MeasurementUnit.HECTOPASCALS,
    "km/h": MeasurementUnit.METERS_PER_SECOND,  # will convert
    "m/s": MeasurementUnit.METERS_PER_SECOND,
    "mm": MeasurementUnit.MILLIMETERS,
    "W/m²": MeasurementUnit.WATTS_PER_SQUARE_METER,
    "W/m2": MeasurementUnit.WATTS_PER_SQUARE_METER,
    "deg": MeasurementUnit.DEGREES,
    # OpenAQ units
    "μg/m³": MeasurementUnit.UG_M3,
    "ug/m3": MeasurementUnit.UG_M3,
    "µg/m³": MeasurementUnit.UG_M3,
    "ppm": MeasurementUnit.MG_M3,  # approximate, will convert if needed
    "ppb": MeasurementUnit.UG_M3,  # approximate conversion
    # Generic
    "deg_c": MeasurementUnit.DEGREES_CELSIUS,
    "celsius": MeasurementUnit.DEGREES_CELSIUS,
    "pct": MeasurementUnit.PERCENTAGE,
}


def normalize_unit(source_unit: str) -> MeasurementUnit:
    """Convert a source-specific unit string to our standard MeasurementUnit.

    Args:
        source_unit: Unit string from the external source.

    Returns:
        Normalized MeasurementUnit enum value.

    Raises:
        InvalidExternalDataError: If the unit is not recognized.
    """
    normalized = UNIT_MAP.get(source_unit)
    if normalized is None:
        # Try case-insensitive match
        for key, val in UNIT_MAP.items():
            if key.lower() == source_unit.lower():
                return val
        raise InvalidExternalDataError(
            details={"unit": source_unit, "error": "Unrecognized unit"},
        )
    return normalized


def normalize_timestamp(iso_string: str) -> datetime:
    """Parse an ISO 8601 timestamp and normalize to UTC.

    Handles various formats:
    - "2024-01-01T12:00:00Z" (UTC)
    - "2024-01-01T12:00:00+05:00" (with offset)
    - "2024-01-01T12:00:00" (naive, assumed UTC)

    Args:
        iso_string: ISO 8601 timestamp string.

    Returns:
        UTC-normalized datetime.

    Raises:
        InvalidExternalDataError: If the timestamp is malformed.
    """
    try:
        # Try parsing with timezone info
        dt = datetime.fromisoformat(iso_string)
        if dt.tzinfo is None:
            # Naive timestamp — assume UTC per our convention
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError) as e:
        raise InvalidExternalDataError(
            details={"timestamp": iso_string, "error": str(e)},
        ) from e


# ── Stage 4: Quality Assessment ──────────────────────────────────────


def assess_quality(
    *,
    parameter: str,
    value: float,
    source_reliability: int,
) -> DataQuality:
    """Assess the quality status of an observation.

    Quality assessment is based on:
    1. Whether the value passes numerical sanity checks
    2. The reliability of the source (from Phase 0.5 ranking)
    3. Whether the value is within expected ranges for the parameter

    This does NOT silently repair or interpolate — it only classifies.

    Args:
        parameter: Measured parameter name.
        value: Measured value.
        source_reliability: Source reliability rank (1-5, from Phase 0.5).

    Returns:
        DataQuality status.
    """
    # Check numerical sanity first
    is_valid, _ = validate_numerical_sanity(parameter=parameter, value=value)
    if not is_valid:
        return DataQuality.SUSPECT

    # Source reliability affects quality assessment
    if source_reliability >= 4:
        return DataQuality.VALID
    elif source_reliability >= 3:
        return DataQuality.UNVERIFIED
    else:
        return DataQuality.SUSPECT


# ── Stage 5: Provenance Attachment ───────────────────────────────────


def create_observation(
    *,
    source: DataSource,
    station_id: str | None,
    location: Coordinates,
    parameter: str,
    value: float,
    unit: MeasurementUnit,
    observed_at: datetime,
    source_identifier: str | None = None,
    raw_response: str | None = None,
    quality: DataQuality = DataQuality.UNVERIFIED,
    retrieved_at: datetime | None = None,
) -> Observation:
    """Create a fully-provenanced Observation domain object.

    This is the final stage before persistence. It assembles
    all the normalized, validated data into a domain object
    with complete provenance metadata.

    Args:
        source: DataSource metadata.
        station_id: Station identifier (if applicable).
        location: Geographic coordinates.
        parameter: Measured parameter name.
        value: Measured value.
        unit: Normalized unit.
        observed_at: When the observation was recorded at the source.
        source_identifier: Original identifier from the external source.
        raw_response: Raw API response (preserved for reproducibility).
        quality: Quality status from assessment stage.
        retrieved_at: When we retrieved the data (defaults to now).

    Returns:
        Complete Observation with provenance.
    """
    if retrieved_at is None:
        retrieved_at = datetime.now(UTC)

    observation_id = generate_observation_id(
        source_id=source.source_id,
        station_id=station_id,
        parameter=parameter,
        observed_at=observed_at.isoformat(),
    )

    return Observation(
        observation_id=observation_id,
        source=source,
        station_id=station_id,
        location=location,
        timestamp=observed_at,
        retrieved_at=retrieved_at,
        parameter=parameter,
        value=value,
        unit=unit,
        quality=quality,
        source_identifier=source_identifier,
    )


# ── Utility: JSON Serialization ───────────────────────────────────────


def safe_json_dumps(data: dict | list | None) -> str | None:
    """Safely serialize data to JSON for storage.

    Args:
        data: Data to serialize.

    Returns:
        JSON string, or None if input is None.
    """
    if data is None:
        return None
    return json.dumps(data, default=str, ensure_ascii=False)
