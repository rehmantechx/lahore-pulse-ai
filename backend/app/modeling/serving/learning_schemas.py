"""Investigation Learning & Accountability Schemas (Phase 6).

Pydantic v2 models for deterministic accountability analysis of
verified historical investigation outcomes.

CRITICAL FRAMING:
- "The system compares the current investigation with similar
  previously verified investigations and shows how useful past
  recommendations were."
- NEVER: "The AI learned that..."
- ALWAYS: "Similar previously verified investigations showed..."
- NEVER: "79% reliability means this pollution is coming from..."
- ALWAYS: "Among similar verified investigations, recommendations
  were useful in approximately 79% of cases."

Design Rules:
- All calculations are deterministic (no ML)
- Never allow historical outcomes to become proof of current hypothesis
- Every response must contain limitations
- Minimum evidence thresholds for reliability claims
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


# ── Constants ──────────────────────────────────────────────────

# Minimum cases for reliability claims
MIN_CASES_FOR_INSUFFICIENT = 0
MIN_CASES_FOR_LIMITED = 3
MIN_CASES_FOR_MODERATE = 6
MIN_CASES_FOR_STRONG = 10

# Maximum similar cases to return
MAX_SIMILAR_CASES = 5


# ── Enums ──────────────────────────────────────────────────────


class EvidenceStatus(StrEnum):
    """How much historical verification evidence is available."""

    INSUFFICIENT = "INSUFFICIENT"
    LIMITED = "LIMITED"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class ReliabilityClassification(StrEnum):
    """Classification of recommendation reliability based on evidence volume."""

    INSUFFICIENT = "INSUFFICIENT"
    LIMITED = "LIMITED"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


# ── Investigation Context (stored with verification) ───────────


class InvestigationContextSnapshot(BaseModel):
    """Environmental context snapshot at time of investigation.

    Stored alongside verification outcomes to enable similarity
    matching for future investigations.
    """

    pm25_value: float | None = Field(
        default=None,
        description="Current PM2.5 value at investigation time",
    )
    pm25_severity_band: str = Field(
        default="UNKNOWN",
        description="PM2.5 severity band (GOOD, MODERATE, UNHEALTHY_SENSITIVE, UNHEALTHY, VERY_UNHEALTHY, HAZARDOUS)",
    )
    wind_sector: str = Field(
        default="UNKNOWN",
        description="Wind direction sector (N, NE, E, SE, S, SW, W, NW)",
    )
    wind_speed_ms: float | None = Field(
        default=None,
        description="Wind speed in m/s",
    )
    wind_speed_band: str = Field(
        default="UNKNOWN",
        description="Wind speed band (CALM, LIGHT, MODERATE, STRONG)",
    )
    temperature_c: float | None = Field(
        default=None,
        description="Temperature in Celsius",
    )
    temperature_band: str = Field(
        default="UNKNOWN",
        description="Temperature band (COLD, COOL, WARM, HOT)",
    )
    humidity_pct: float | None = Field(
        default=None,
        description="Relative humidity percentage",
    )
    humidity_band: str = Field(
        default="UNKNOWN",
        description="Humidity band (DRY, MODERATE, HUMID)",
    )
    investigation_corridor: str = Field(
        default="UNKNOWN",
        description="Investigation corridor label (e.g. 'East Corridor')",
    )
    eligible_domains: list[str] = Field(
        default_factory=list,
        description="List of eligible investigation domain IDs",
    )
    trajectory: str = Field(
        default="UNKNOWN",
        description="PM2.5 trajectory (rising, falling, stable, uncertain)",
    )
    episode_state: str = Field(
        default="UNKNOWN",
        description="Episode state (episode, improving, uncertain, normal)",
    )


# ── Similar Case ───────────────────────────────────────────────


class SimilarCase(BaseModel):
    """One similar verified investigation case."""

    investigation_id: str = Field(
        ..., description="Investigation session identifier"
    )
    outcome_id: str = Field(
        ..., description="Verification outcome identifier"
    )
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Similarity score (0=identical, 1=opposite). Note: score is 1-distance.",
    )
    date: str = Field(
        ..., description="Date of the verification"
    )
    overall_status: str = Field(
        ..., description="Overall verification outcome"
    )
    recommendation_verification: str = Field(
        ..., description="Was the recommendation supported?"
    )
    summary: str = Field(
        default="",
        description="Brief summary of the verification outcome",
    )
    matching_dimensions: list[str] = Field(
        default_factory=list,
        description="Which dimensions matched between current and historical"
    )
    differing_dimensions: list[str] = Field(
        default_factory=list,
        description="Which dimensions differed"
    )


# ── Reliability ────────────────────────────────────────────────


class ReliabilityScore(BaseModel):
    """Deterministic reliability calculation from verified outcomes.

    Scoring formula:
    - USEFUL = 1.0
    - PARTIALLY_USEFUL = 0.5
    - NOT_SUPPORTED = 0.0
    - INCONCLUSIVE = excluded from calculation

    Score = (useful × 1.0 + partially_useful × 0.5) / total_evaluated × 100
    """

    score: float | None = Field(
        default=None,
        description="Reliability percentage (0-100). Null when insufficient data.",
    )
    classification: ReliabilityClassification = Field(
        default=ReliabilityClassification.INSUFFICIENT,
        description="Reliability classification based on evidence volume",
    )
    description: str = Field(
        default="",
        description="Human-readable description of the reliability assessment",
    )
    useful_count: int = Field(default=0, description="Number of USEFUL outcomes")
    partially_useful_count: int = Field(default=0, description="Number of PARTIALLY_USEFUL outcomes")
    not_supported_count: int = Field(default=0, description="Number of NOT_SUPPORTED outcomes")
    inconclusive_count: int = Field(default=0, description="Number of INCONCLUSIVE outcomes")
    total_evaluated: int = Field(default=0, description="Total outcomes used in calculation")


# ── Top-level Response ─────────────────────────────────────────


class InvestigationLearningResponse(BaseModel):
    """Complete accountability context for a current investigation.

    Deterministic analysis of verified historical outcomes.
    Used to provide transparent accountability evidence
    for future decision-making.
    """

    historical_investigations_found: int = Field(
        default=0,
        description="Total number of similar verified investigations found",
    )
    verified_outcomes: dict[str, int] = Field(
        default_factory=lambda: {
            "useful": 0,
            "partially_useful": 0,
            "not_supported": 0,
            "inconclusive": 0,
        },
        description="Outcome distribution among similar cases",
    )
    recommendation_reliability: ReliabilityScore = Field(
        default_factory=ReliabilityScore,
        description="Deterministic reliability calculation",
    )
    similar_cases: list[SimilarCase] = Field(
        default_factory=list,
        description="Top similar verified investigations",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Mandatory limitations on this analysis",
    )
    evidence_status: EvidenceStatus = Field(
        default=EvidenceStatus.INSUFFICIENT,
        description="Overall evidence status classification",
    )
    historical_context_message: str = Field(
        default="",
        description="Auto-generated human-readable historical context",
    )
    disclaimer: str = Field(
        default=(
            "Historical verification does not confirm that the current "
            "recommendation is correct. Past outcomes provide accountability "
            "context only."
        ),
        description="Mandatory disclaimer",
    )
