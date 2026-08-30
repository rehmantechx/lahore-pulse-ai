"""Forecast domain models.

Represents data predicted by EXTERNAL forecast services
(e.g., Open-Meteo weather forecasts, AQICN forecasts).

These are forecasts produced by third parties, NOT by our ML models.
Our own model predictions use the Prediction model instead.

This distinction is critical for:
- Provenance: knowing whether data was externally predicted or internally modeled
- Uncertainty: external forecasts and our predictions have different confidence profiles
- Traceability: different error sources require different investigation paths
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from .common import Confidence, MeasurementUnit


class ForecastHorizon(StrEnum):
    """Time horizon categories for forecasts."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Forecast(BaseModel):
    """An external forecast value.

    Represents a forecasted environmental value produced by
    a third-party service. This is NOT an ML model prediction
    from our own system.

    Attributes:
        forecast_id: Unique identifier for this forecast.
        source_id: Which external forecast provider.
        parameter: What is being forecasted.
        location: Where the forecast applies.
        issued_at: When the forecast was issued.
        target_time: What time the forecast is for.
        value: The forecasted value.
        unit: Unit of measurement.
        horizon: Forecast time horizon.
        confidence: Optional confidence estimate from the provider.
    """

    forecast_id: str = Field(
        ...,
        description="Unique forecast identifier",
    )
    source_id: str = Field(
        ...,
        description="Identifier of the external forecast provider",
    )
    parameter: str = Field(
        ...,
        description="Forecasted parameter (e.g., 'temperature', 'pm25')",
    )
    location_lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Forecast location latitude",
    )
    location_lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Forecast location longitude",
    )
    issued_at: datetime = Field(
        ...,
        description="When the forecast was issued",
    )
    target_time: datetime = Field(
        ...,
        description="The time the forecast is predicting for",
    )
    value: float = Field(
        ...,
        description="Forecasted value",
    )
    unit: MeasurementUnit = Field(
        ...,
        description="Unit of measurement",
    )
    horizon: ForecastHorizon = Field(
        ...,
        description="Forecast time horizon category",
    )
    confidence: Confidence | None = Field(
        default=None,
        description="Confidence estimate from the forecast provider",
    )
