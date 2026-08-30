"""Investigation Verification Schemas (Phase 5 — Learning Loop).

Pydantic v2 models for the human verification feedback loop.

Design Rules:
- NEVER modify original AI analysis when storing verification
- Use language: "Recommendation supported" NOT "AI was correct"
- Investigation area verification: SUPPORTED/PARTIALLY_SUPPORTED/NOT_SUPPORTED/UNKNOWN
- Overall verification: USEFUL/PARTIALLY_USEFUL/NOT_SUPPORTED/INCONCLUSIVE
- Historical verification is context only, not a guarantee
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────


class OverallVerificationStatus(StrEnum):
    """Overall assessment of investigation usefulness."""

    PENDING = "PENDING"
    USEFUL = "USEFUL"
    PARTIALLY_USEFUL = "PARTIALLY_USEFUL"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class RecommendationVerification(StrEnum):
    """Was the recommended investigation corridor supported by field findings?"""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNKNOWN = "UNKNOWN"


class InvestigationAreaVerification(StrEnum):
    """Was the investigation area (upwind corridor) verified in the field?"""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    UNKNOWN = "UNKNOWN"


# ── Sub-models ─────────────────────────────────────────────────────


class HypothesisVerification(BaseModel):
    """Verification of a single hypothesis from the AI analysis.

    Maps to one InvestigationHypothesis from the AI output.
    """

    factor: str = Field(..., min_length=1, description="The hypothesis factor being verified")
    verified: bool = Field(..., description="Whether this hypothesis was verified in the field")
    notes: str = Field(default="", description="Field notes for this specific hypothesis")


# ── Request/Response Models ────────────────────────────────────────


class VerificationCreateRequest(BaseModel):
    """Request to submit a verification outcome for an investigation.

    The investigation_id links to the AI analysis session.
    The AI analysis itself is NEVER modified — verification is stored separately.
    """

    investigation_id: str = Field(
        ...,
        min_length=1,
        description="Identifier for the investigation session being verified",
    )
    overall_status: OverallVerificationStatus = Field(
        ...,
        description="Overall assessment of investigation usefulness",
    )
    recommendation_verification: RecommendationVerification = Field(
        default=RecommendationVerification.UNKNOWN,
        description="Was the recommended investigation corridor supported by field findings?",
    )
    investigation_area_verification: InvestigationAreaVerification = Field(
        default=InvestigationAreaVerification.UNKNOWN,
        description="Was the investigation area verified in the field?",
    )
    hypothesis_verifications: list[HypothesisVerification] = Field(
        default_factory=list,
        description="Per-hypothesis verification results",
    )
    field_notes: str = Field(
        default="",
        description="Free-text field notes from the investigation",
    )
    verified_by: str = Field(
        default="",
        description="Name or role of the person performing verification",
    )
    investigation_context: dict | None = Field(
        default=None,
        description=(
            "Environmental context snapshot at time of investigation. "
            "Used for similarity matching in the learning system. "
            "Contains PM2.5, wind, temperature, humidity, corridor, domains."
        ),
    )


class VerificationUpdateRequest(BaseModel):
    """Request to update an existing verification outcome.

    All fields are optional — only provided fields are updated.
    """

    overall_status: OverallVerificationStatus | None = Field(
        default=None,
        description="Updated overall assessment",
    )
    recommendation_verification: RecommendationVerification | None = Field(
        default=None,
        description="Updated recommendation verification",
    )
    investigation_area_verification: InvestigationAreaVerification | None = Field(
        default=None,
        description="Updated investigation area verification",
    )
    hypothesis_verifications: list[HypothesisVerification] | None = Field(
        default=None,
        description="Updated hypothesis verifications",
    )
    field_notes: str | None = Field(
        default=None,
        description="Updated field notes",
    )


class VerificationOutcomeResponse(BaseModel):
    """Response model for a stored verification outcome."""

    outcome_id: str = Field(..., description="Unique outcome identifier")
    investigation_id: str = Field(..., description="Investigation session identifier")
    overall_status: OverallVerificationStatus = Field(..., description="Overall verification status")
    recommendation_verification: RecommendationVerification = Field(
        default=RecommendationVerification.UNKNOWN,
        description="Recommendation verification status",
    )
    investigation_area_verification: InvestigationAreaVerification = Field(
        default=InvestigationAreaVerification.UNKNOWN,
        description="Investigation area verification status",
    )
    hypothesis_verifications: list[HypothesisVerification] = Field(
        default_factory=list,
        description="Per-hypothesis verifications",
    )
    field_notes: str = Field(default="", description="Field notes")
    verified_by: str = Field(default="", description="Verifier identity")
    verified_at: str | None = Field(default=None, description="ISO timestamp of verification")
    created_at: str = Field(..., description="ISO timestamp of record creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    investigation_context: dict | None = Field(
        default=None,
        description="Environmental context snapshot (nullable for pre-Phase-6 records)",
    )


class VerificationStats(BaseModel):
    """Aggregated verification statistics across multiple outcomes.

    Only returned when minimum sample threshold (3) is met.
    """

    total_verifications: int = Field(
        ..., ge=0, description="Total number of verified outcomes"
    )
    useful_count: int = Field(default=0, description="Number assessed as USEFUL")
    partially_useful_count: int = Field(default=0, description="Number assessed as PARTIALLY_USEFUL")
    not_supported_count: int = Field(default=0, description="Number assessed as NOT_SUPPORTED")
    inconclusive_count: int = Field(default=0, description="Number assessed as INCONCLUSIVE")
    recommendation_supported_pct: float | None = Field(
        default=None,
        description="Percentage of recommendations SUPPORTED (null if < 3 verifications)",
    )
    area_supported_pct: float | None = Field(
        default=None,
        description="Percentage of investigation areas SUPPORTED (null if < 3 verifications)",
    )
    hypothesis_hit_rate: float | None = Field(
        default=None,
        description="Percentage of individual hypotheses verified as true (null if < 3 verifications)",
    )


class VerificationContextResponse(BaseModel):
    """Complete verification context for a given investigation.

    Includes the verification outcome (if any) and aggregate stats.
    Used to provide transparent feedback to future investigations.
    """

    current_outcome: VerificationOutcomeResponse | None = Field(
        default=None,
        description="Verification outcome for the current investigation (if verified)",
    )
    stats: VerificationStats = Field(
        ...,
        description="Aggregate verification statistics",
    )
    disclaimer: str = Field(
        default=(
            "Historical verification data provides context for ongoing investigations. "
            "It does not guarantee the accuracy of current AI analysis."
        ),
        description="Disclaimer about the nature of verification context",
    )


# ── Constants ──────────────────────────────────────────────────────

MIN_SAMPLE_FOR_STATS = 3
"""Minimum number of verified cases before showing percentage statistics."""
