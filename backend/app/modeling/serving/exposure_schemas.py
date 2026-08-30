"""Exposure Intelligence — Pydantic schemas for geometry response.

Validates the deterministic exposure geometry output before
returning it through the API.  All geometry is computed deterministically —
no AI is involved in coordinate calculation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EventLocation(BaseModel):
    """Current pollution observation point."""

    lat: float = Field(..., description="Latitude of the observation")
    lng: float = Field(..., description="Longitude of the observation")
    pm25: float | None = Field(None, description="Current PM2.5 reading")
    severity: str | None = Field(None, description="Severity classification")
    trajectory: str | None = Field(None, description="Trend direction")


class InvestigationArea(BaseModel):
    """Upwind investigation corridor geometry."""

    type: str = Field(
        default="upwind_investigation_corridor",
        description="Geometry type",
    )
    coordinates: list[list[float]] = Field(
        default_factory=list,
        description="Polygon coordinates [[lat, lng], ...]",
    )
    center: dict[str, float] = Field(
        default_factory=dict,
        description="Center point {lat, lng}",
    )
    direction_degrees: float = Field(
        ..., description="Direction the corridor points (meteorological FROM-degrees)"
    )
    direction_label: str = Field(
        default="", description="Human-readable direction label"
    )
    distance_km: float = Field(
        default=8.0, description="Length of corridor in km"
    )
    width_degrees: float = Field(
        default=60.0, description="Angular width of corridor"
    )
    priority: str = Field(
        default="HIGH", description="Investigation priority level"
    )
    label: str = Field(
        default="Priority Investigation Area", description="Display label"
    )
    requires_ground_verification: bool = Field(
        default=True,
        description="Whether ground verification is required",
    )
    uncertainty: str = Field(
        default="", description="Uncertainty description for this geometry"
    )


class ExposurePath(BaseModel):
    """Downwind exposure cone geometry."""

    type: str = Field(
        default="approximate_downwind_cone",
        description="Geometry type",
    )
    coordinates: list[list[float]] = Field(
        default_factory=list,
        description="Polygon coordinates [[lat, lng], ...]",
    )
    center: dict[str, float] = Field(
        default_factory=dict,
        description="Start point {lat, lng}",
    )
    direction_degrees: float = Field(
        ..., description="Direction the cone extends (movement bearing)"
    )
    direction_label: str = Field(
        default="", description="Human-readable direction label"
    )
    distance_km: float = Field(
        default=10.0, description="Length of exposure cone in km"
    )
    cone_width_degrees: float = Field(
        default=60.0, description="Total angular width of cone"
    )
    confidence: str = Field(
        default="MODERATE", description="Confidence level for this geometry"
    )
    uncertainty: str = Field(
        default="", description="Uncertainty description for this geometry"
    )


class VulnerableLocation(BaseModel):
    """A single vulnerable location (school or hospital)."""

    name: str = Field(..., description="Location name")
    type: str = Field(..., description="Location type (school/hospital)")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class VulnerableLocationsSummary(BaseModel):
    """Summary of vulnerable locations in the exposure path."""

    schools: list[VulnerableLocation] = Field(default_factory=list)
    hospitals: list[VulnerableLocation] = Field(default_factory=list)
    summary: dict[str, int] = Field(
        default_factory=lambda: {"schools_in_path": 0, "hospitals_in_path": 0},
        description="Count summary",
    )


class ExposureGeometryMetadata(BaseModel):
    """Metadata about the exposure geometry computation."""

    wind_direction_degrees: float | None = Field(None)
    movement_bearing: float | None = Field(None)
    wind_speed_ms: float | None = Field(None)
    corridor_length_km: float = Field(default=8.0)
    cone_length_km: float = Field(default=10.0)
    computed_at: str = Field(default="")


class ExposureGeometryResponse(BaseModel):
    """Full exposure intelligence geometry response.

    This is the deterministic geometry that powers the Exposure Intelligence Map.
    It does NOT depend on AI analysis and must always be available when wind data exists.
    """

    event_location: EventLocation = Field(...)
    investigation_area: InvestigationArea | None = Field(
        None,
        description="Upwind investigation corridor (null if wind data missing)",
    )
    exposure_path: ExposurePath | None = Field(
        None,
        description="Downwind exposure cone (null if wind data missing)",
    )
    vulnerable_locations: VulnerableLocationsSummary = Field(
        default_factory=VulnerableLocationsSummary,
    )
    metadata: ExposureGeometryMetadata = Field(
        default_factory=ExposureGeometryMetadata,
    )
    uncertainty: str = Field(
        default="",
        description="Overall uncertainty description",
    )
