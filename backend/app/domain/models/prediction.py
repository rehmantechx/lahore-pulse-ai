"""Prediction domain models.

Represents predictions produced by OUR OWN ML models.

This is distinct from:
- Observations (real measured data)
- Forecasts (predictions from external services)

Every prediction must carry:
- Model identification (which model, which version)
- Input traceability (which features were used)
- Confidence/uncertainty
- Explanation (for explainable AI requirements)

These models are established as architectural contracts now.
ML model implementation belongs to Phase 2+.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import Confidence, MeasurementUnit


class Prediction(BaseModel):
    """An ML model prediction.

    Represents a value predicted by one of our trained models.
    Every prediction is traceable to its model, version, and inputs.

    Attributes:
        prediction_id: Unique prediction identifier.
        model_id: Which model produced this prediction.
        model_version: Version of the model.
        parameter: What is being predicted.
        location_lat/lon: Where the prediction applies.
        created_at: When the prediction was generated.
        target_time: What time the prediction is for.
        value: The predicted value.
        unit: Unit of measurement.
        confidence: Confidence/uncertainty estimate.
        features_used: List of input features used.
        explanation: Human-readable explanation of the prediction.
    """

    prediction_id: str = Field(
        ...,
        description="Unique prediction identifier",
    )
    model_id: str = Field(
        ...,
        description="Identifier of the ML model that produced this prediction",
    )
    model_version: str = Field(
        ...,
        description="Version of the model (e.g., 'v1.0.0', 'abc123')",
    )
    parameter: str = Field(
        ...,
        description="Predicted parameter (e.g., 'aqi', 'pm25_risk')",
    )
    location_lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Prediction location latitude",
    )
    location_lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Prediction location longitude",
    )
    created_at: datetime = Field(
        ...,
        description="When the prediction was generated",
    )
    target_time: datetime = Field(
        ...,
        description="What time the prediction is for",
    )
    value: float = Field(
        ...,
        description="Predicted value",
    )
    unit: MeasurementUnit = Field(
        ...,
        description="Unit of measurement",
    )
    confidence: Confidence | None = Field(
        default=None,
        description="Confidence and uncertainty estimate",
    )
    features_used: list[str] = Field(
        default_factory=list,
        description="List of input feature names used by the model",
    )
    explanation: str | None = Field(
        default=None,
        description="Human-readable explanation of how the prediction was made",
    )
