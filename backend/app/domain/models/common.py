"""Shared domain types.

Defines foundational types used across all domain models:
measurement units, data quality indicators, and confidence representations.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MeasurementUnit(StrEnum):
    """Standard units of measurement for environmental data.

    Using an enum ensures that unit types are consistent and
    prevents accidental use of arbitrary unit strings.
    """

    AQI_INDEX = "aqi_index"
    UG_M3 = "ug/m3"  # micrograms per cubic meter (PM2.5, PM10, etc.)
    MG_M3 = "mg/m3"  # milligrams per cubic meter
    DEGREES_CELSIUS = "deg_c"
    FAHRENHEIT = "deg_f"
    PERCENTAGE = "pct"
    MILLIMETERS = "mm"
    METERS_PER_SECOND = "m/s"
    DEGREES = "deg"  # angular degrees (wind direction)
    HECTOPASCALS = "hPa"
    WATTS_PER_SQUARE_METER = "W/m2"
    UV_INDEX = "uv_index"


class DataQuality(StrEnum):
    """Quality status of a data point.

    Distinguishes between verified, suspect, and missing data
    to prevent treating uncertain observations as ground truth.
    """

    VALID = "valid"
    SUSPECT = "suspect"
    MISSING = "missing"
    INTERPOLATED = "interpolated"
    UNVERIFIED = "unverified"


class DataSourceType(StrEnum):
    """Categories of external data sources."""

    AIR_QUALITY = "air_quality"
    WEATHER = "weather"
    SATELLITE = "satellite"
    TRAFFIC = "traffic"
    HEALTH = "health"
    POPULATION = "population"
    GEOSPATIAL = "geospatial"


class Confidence(BaseModel):
    """Confidence and uncertainty representation.

    Ensures that every prediction or assessment carries explicit
    uncertainty information rather than presenting false certainty.

    Attributes:
        level: Confidence score from 0.0 (no confidence) to 1.0 (certain).
        method: How confidence was calculated (e.g., "bootstrap", "cross_validation").
        interval_lower: Lower bound of the confidence interval.
        interval_upper: Upper bound of the confidence interval.
    """

    level: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level from 0.0 (no confidence) to 1.0 (certain)",
    )
    method: str | None = Field(
        default=None,
        description="Method used to calculate confidence",
    )
    interval_lower: float | None = Field(
        default=None,
        description="Lower bound of confidence interval",
    )
    interval_upper: float | None = Field(
        default=None,
        description="Upper bound of confidence interval",
    )
