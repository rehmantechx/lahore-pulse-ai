"""AI Investigation Reasoning — structured output schemas.

Pydantic models that enforce the strict output contract for the
AI investigation reasoning layer.  Every field is validated:
- Confidence bounds [0.30, 0.85]
- Required evidence references on hypotheses
- Uncertainties section required
- No invented statistics or locations
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# ── Sub-sections ───────────────────────────────────────────────


class ObservedFact(BaseModel):
    """A directly measured or retrieved data point."""

    statement: str = Field(..., min_length=1, description="Factual statement based on observed data")
    evidence_references: list[str] = Field(
        default_factory=list,
        description="Paths into the evidence package that support this fact",
    )


class ModelInference(BaseModel):
    """A conclusion from deterministic models or statistical analysis."""

    statement: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def cap_confidence(cls, v: float) -> float:
        return min(v, 0.85)


class InvestigationHypothesis(BaseModel):
    """A possible explanation requiring human field verification."""

    factor: str = Field(..., min_length=1, description="What factor is hypothesized")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., min_length=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    verification_needed: str = Field(..., min_length=1, description="What field check would confirm/refute")

    @field_validator("confidence")
    @classmethod
    def cap_confidence(cls, v: float) -> float:
        return min(v, 0.85)


class InvestigationPriority(BaseModel):
    """Where to investigate first."""

    area: str = Field(..., min_length=1)
    priority: str = Field(..., pattern=r"^(HIGH|MEDIUM|LOW)$")
    rationale: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def cap_confidence(cls, v: float) -> float:
        return min(v, 0.85)


class ExposureDirection(BaseModel):
    """Likely direction of pollutant exposure."""

    description: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def cap_confidence(cls, v: float) -> float:
        return min(v, 0.85)


class RecommendedAction(BaseModel):
    """A concrete recommended investigation action."""

    priority: int = Field(..., ge=1, le=10)
    action: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    verification_goal: str = Field(..., min_length=1)


# ── Top-level response ─────────────────────────────────────────


class AIInvestigationResult(BaseModel):
    """Structured output from the AI investigation reasoning layer.

    Every confidence value is bounded to [0.30, 0.85] post-processing.
    Every hypothesis must have supporting evidence references.
    Uncertainties section is always required.
    """

    analysis_status: str = Field(
        ...,
        pattern=r"^(complete|limited|unavailable)$",
        description="Whether the analysis completed fully or with limitations",
    )
    event_summary: str = Field(..., min_length=1)
    severity_assessment: str = Field(default="")
    observed_facts: list[ObservedFact] = Field(default_factory=list)
    model_inferences: list[ModelInference] = Field(default_factory=list)
    investigation_hypotheses: list[InvestigationHypothesis] = Field(default_factory=list)
    investigation_priority: InvestigationPriority | None = None
    likely_exposure_direction: ExposureDirection | None = None
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    uncertainties: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="At least 3 uncertainties when sufficient output is possible",
    )
    data_gaps: list[str] = Field(default_factory=list)


# ── Wrapper response for the endpoint ──────────────────────────


class InvestigationAnalysisResponse(BaseModel):
    """Full response from GET /api/v1/investigation/analyze."""

    evidence: dict = Field(description="The full evidence package")
    analysis: AIInvestigationResult = Field(description="AI investigation analysis")
    analysis_metadata: dict = Field(description="Mode, provider, timestamp, fallback status")
