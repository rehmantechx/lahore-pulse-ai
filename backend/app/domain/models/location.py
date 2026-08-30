"""Geographic domain models.

Represents locations, monitoring stations, and spatial areas
within Lahore. These models provide the geographic foundation
for all observations, predictions, and risk assessments.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Geographic coordinates (WGS 84).

    Latitude and longitude in decimal degrees.
    Validated to prevent out-of-range values.
    """

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees",
    )
    altitude_meters: float | None = Field(
        default=None,
        description="Altitude above sea level in meters",
    )


# Well-known Lahore reference coordinates
LAHORE_CENTER = Coordinates(latitude=31.5204, longitude=74.3587)


class Station(BaseModel):
    """A monitoring station.

    Represents a physical or virtual data collection point
    belonging to an external data source.
    """

    station_id: str = Field(
        ...,
        description="Unique station identifier (may include source prefix)",
    )
    name: str = Field(
        ...,
        description="Human-readable station name",
    )
    location: Coordinates = Field(
        ...,
        description="Station geographic coordinates",
    )
    source_id: str = Field(
        ...,
        description="Identifier of the data source this station belongs to",
    )
    active: bool = Field(
        default=True,
        description="Whether the station is currently operational",
    )
    description: str | None = Field(
        default=None,
        description="Optional station description or notes",
    )


class Area(BaseModel):
    """A geographic area within Lahore.

    Represents an administrative or analysis zone.
    Future versions will include boundary polygons.
    """

    area_id: str = Field(
        ...,
        description="Unique area identifier",
    )
    name: str = Field(
        ...,
        description="Human-readable area name",
    )
    center: Coordinates = Field(
        ...,
        description="Approximate center of the area",
    )
    area_type: str = Field(
        default="neighbourhood",
        description="Type of area (neighbourhood, district, zone, etc.)",
    )
