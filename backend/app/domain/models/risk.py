"""Risk assessment domain models.

Represents risk calculations that combine observations,
forecasts, and predictions into actionable risk levels.

A risk assessment answers: "How serious is the situation,
and should we act?"

Risk models are established as architectural contracts now.
Risk calculation logic belongs to Phase 3+.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from .common import Confidence


class RiskType(StrEnum):
    """Categories of environmental risk."""

    AIR_QUALITY = "air_quality"
    HEAT = "heat"
    FLOOD = "flood"
    COMBINED = "combined"


class Severity(StrEnum):
    """Risk severity levels."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(BaseModel):
    """A risk assessment for a specific location and time.

    Combines multiple data sources and model outputs into
    a single actionable risk level. Every assessment must
    include confidence and contributing factors for
    explainability.

    Attributes:
        assessment_id: Unique identifier.
        risk_type: What kind of risk.
        location: Where the risk applies.
        assessed_at: When the assessment was made.
        target_time: What time the risk is for.
        severity: Human-readable severity level.
        score: Normalized risk score [0.0, 1.0].
        confidence: Confidence in the assessment.
        contributing_factors: What inputs influenced the assessment.
        explanation: Human-readable explanation.
    """

    assessment_id: str = Field(
        ...,
        description="Unique assessment identifier",
    )
    risk_type: RiskType = Field(
        ...,
        description="Type of environmental risk",
    )
    location_lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Assessment location latitude",
    )
    location_lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Assessment location longitude",
    )
    assessed_at: datetime = Field(
        ...,
        description="When the assessment was generated",
    )
    target_time: datetime = Field(
        ...,
        description="What time the risk assessment is for",
    )
    severity: Severity = Field(
        ...,
        description="Human-readable severity classification",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized risk score from 0.0 (no risk) to 1.0 (maximum risk)",
    )
    confidence: Confidence | None = Field(
        default=None,
        description="Confidence in the risk assessment",
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="List of factors that contributed to this assessment",
    )
    explanation: str | None = Field(
        default=None,
        description="Human-readable explanation of the risk assessment",
    )
