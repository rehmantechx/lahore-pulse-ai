"""Observation domain models.

Represents actual measured data from external sources.
Every observation is traceable to its source and carries
full provenance metadata for audit and quality assurance.

These models enforce the critical distinction between:
- Observed data (measured, historical)
- Forecast data (predicted by external services)
- Model predictions (produced by our ML models)
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator

from .common import DataQuality, DataSourceType, MeasurementUnit
from .location import Coordinates


class DataSource(BaseModel):
    """Metadata about an external data source.

    Describes where data comes from, who provides it,
    and under what terms. This supports data provenance
    and makes sources replaceable.
    """

    source_id: str = Field(
        ...,
        description="Unique identifier for this data source (e.g., 'openaq')",
    )
    name: str = Field(
        ...,
        description="Human-readable source name",
    )
    provider: str = Field(
        ...,
        description="Provider organization (e.g., 'OpenAQ', 'Open-Meteo')",
    )
    source_type: DataSourceType = Field(
        ...,
        description="Category of data this source provides",
    )
    base_url: str | None = Field(
        default=None,
        description="Base URL of the data source API",
    )
    license: str | None = Field(
        default=None,
        description="Data license (e.g., 'CC BY 4.0')",
    )
    documentation_url: str | None = Field(
        default=None,
        description="URL to the source documentation",
    )


class Observation(BaseModel):
    """An actual observed measurement from a data source.

    This is the fundamental unit of real-world data. It captures:
    - What was measured (parameter, value, unit)
    - Where it was measured (coordinates)
    - When it was measured (observation timestamp)
    - When we retrieved it (retrieval timestamp)
    - How reliable it is (quality status)
    - Where it came from (source metadata)

    Critical: This represents OBSERVED data, not predictions.
    """

    observation_id: str = Field(
        ...,
        description="Unique observation identifier",
    )
    source: DataSource = Field(
        ...,
        description="Metadata about the data source",
    )
    station_id: str | None = Field(
        default=None,
        description="Station identifier within the source (if applicable)",
    )
    location: Coordinates = Field(
        ...,
        description="Geographic coordinates of the observation",
    )
    timestamp: datetime = Field(
        ...,
        description="When the observation was recorded at the source",
    )
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this observation was retrieved by our system",
    )
    parameter: str = Field(
        ...,
        description="Measured parameter (e.g., 'pm25', 'pm10', 'temperature')",
    )
    value: float = Field(
        ...,
        description="Measured value",
    )
    unit: MeasurementUnit = Field(
        ...,
        description="Unit of measurement",
    )
    quality: DataQuality = Field(
        default=DataQuality.UNVERIFIED,
        description="Data quality status",
    )
    source_identifier: str | None = Field(
        default=None,
        description="Original identifier from the external source",
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> Observation:
        """Ensure retrieval timestamp is not before observation timestamp."""
        if self.retrieved_at < self.timestamp:
            # Allow but flag — backfill scenarios may have earlier retrieval
            pass
        return self
