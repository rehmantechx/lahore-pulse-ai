"""Investigation Learning & Accountability Service (Phase 6).

Provides deterministic analysis of verified historical investigation
outcomes for accountability context. NOT machine learning. NOT
automatic improvement. Deterministic comparison only.

CRITICAL FRAMING:
- "Similar previously verified investigations showed..."
- "Historical verification data indicates..."
- NEVER: "The AI learned that..."

All calculations are deterministic:
- Similarity matching: weighted Euclidean distance on normalized features
- Reliability: weighted scoring of verification outcomes
- Evidence classification: based on sample size thresholds
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from loguru import logger

from ...core.db import get_db_connection, is_cloud_db

from ...modeling.serving.learning_schemas import (
    EvidenceStatus,
    InvestigationContextSnapshot,
    InvestigationLearningResponse,
    MAX_SIMILAR_CASES,
    MIN_CASES_FOR_LIMITED,
    MIN_CASES_FOR_MODERATE,
    MIN_CASES_FOR_STRONG,
    ReliabilityClassification,
    ReliabilityScore,
    SimilarCase,
)
from ...modeling.serving.source_compass import SECTORS
from ...modeling.serving.verification_schemas import (
    OverallVerificationStatus,
    VerificationOutcomeResponse,
)


# ── Constants ──────────────────────────────────────────────────

# Similarity feature weights — higher = more influence
FEATURE_WEIGHTS = {
    "pm25_severity_band": 1.0,
    "trajectory": 0.8,
    "wind_sector": 1.0,
    "wind_speed_band": 0.6,
    "temperature_band": 0.5,
    "humidity_band": 0.5,
    "investigation_corridor": 0.8,
    "eligible_domains": 0.4,
    "episode_state": 0.3,
}

# Band ordinal mappings for severity/distance calculation
PM25_BAND_ORDER = {
    "GOOD": 0,
    "MODERATE": 1,
    "UNHEALTHY_SENSITIVE": 2,
    "UNHEALTHY": 3,
    "VERY_UNHEALTHY": 4,
    "HAZARDOUS": 5,
    "UNKNOWN": -1,
}

WIND_SPEED_BAND_ORDER = {
    "CALM": 0,
    "LIGHT": 1,
    "MODERATE": 2,
    "STRONG": 3,
    "UNKNOWN": -1,
}

TEMPERATURE_BAND_ORDER = {
    "COLD": 0,
    "COOL": 1,
    "WARM": 2,
    "HOT": 3,
    "UNKNOWN": -1,
}

HUMIDITY_BAND_ORDER = {
    "DRY": 0,
    "MODERATE": 1,
    "HUMID": 2,
    "UNKNOWN": -1,
}

EPISODE_STATE_ORDER = {
    "normal": 0,
    "uncertain": 1,
    "improving": 2,
    "episode": 3,
    "UNKNOWN": -1,
}

TRAJECTORY_ORDER = {
    "falling": 0,
    "stable": 1,
    "uncertain": 2,
    "rising": 3,
    "UNKNOWN": -1,
}

# Sector angular distance
SECTOR_ANGLES = {s: i * 45.0 for i, s in enumerate(SECTORS)}

# Reliability scoring weights
STATUS_SCORES = {
    "USEFUL": 1.0,
    "PARTIALLY_USEFUL": 0.5,
    "NOT_SUPPORTED": 0.0,
    # INCONCLUSIVE is excluded from calculation
}


# ── Helpers ────────────────────────────────────────────────────


def _get_read_connection(db_path: Path) -> sqlite3.Connection:
    """Open a read-only connection (SQLite or PostgreSQL)."""
    if is_cloud_db():
        return get_db_connection(read_only=True, row_factory=sqlite3.Row)
    uri_path = str(db_path).replace("\\", "/")
    if len(uri_path) >= 2 and uri_path[1] == ":":
        uri_path = "/" + uri_path
    conn = sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _get_write_connection(db_path: Path) -> sqlite3.Connection:
    """Open a write connection (SQLite or PostgreSQL)."""
    if is_cloud_db():
        return get_db_connection(row_factory=sqlite3.Row)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _band_distance(band_a: str, band_b: str, band_order: dict[str, int]) -> float:
    """Calculate distance between two bands on an ordinal scale.

    Returns 0.0 if identical, 1.0 if maximally different.
    Returns 1.0 if either band is UNKNOWN.
    """
    a = band_order.get(band_a, -1)
    b = band_order.get(band_b, -1)
    if a == -1 or b == -1:
        return 1.0
    max_distance = max(band_order.values())
    if max_distance == 0:
        return 0.0
    return abs(a - b) / max_distance


def _sector_distance(sector_a: str, sector_b: str) -> float:
    """Calculate angular distance between two wind sectors.

    Returns 0.0 if same sector, 1.0 if opposite direction.
    """
    if sector_a == "UNKNOWN" or sector_b == "UNKNOWN":
        return 1.0
    angle_a = SECTOR_ANGLES.get(sector_a, 0)
    angle_b = SECTOR_ANGLES.get(sector_b, 0)
    diff = abs(angle_a - angle_b) % 360
    if diff > 180:
        diff = 360 - diff
    return diff / 180.0


def _list_distance(list_a: list[str], list_b: list[str]) -> float:
    """Calculate Jaccard distance between two lists.

    Returns 0.0 if identical, 1.0 if completely disjoint.
    """
    set_a = set(list_a)
    set_b = set(list_b)
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return 1.0 - (len(intersection) / len(union)) if union else 1.0


def _exact_distance(val_a: str, val_b: str) -> float:
    """Calculate exact match distance.

    Returns 0.0 if identical, 1.0 if different.
    """
    if val_a == "UNKNOWN" or val_b == "UNKNOWN":
        return 1.0
    return 0.0 if val_a == val_b else 1.0


# ── Similarity Calculation ─────────────────────────────────────


def compute_similarity(
    current: InvestigationContextSnapshot,
    historical: InvestigationContextSnapshot,
) -> tuple[float, list[str], list[str]]:
    """Compute weighted similarity between two investigation contexts.

    Returns (similarity_score, matching_dimensions, differing_dimensions)
    where similarity_score is in [0, 1] (1 = identical, 0 = opposite).
    """
    total_distance = 0.0
    total_weight = 0.0
    matching: list[str] = []
    differing: list[str] = []

    # PM2.5 severity band
    d = _band_distance(
        current.pm25_severity_band, historical.pm25_severity_band, PM25_BAND_ORDER
    )
    w = FEATURE_WEIGHTS["pm25_severity_band"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("PM2.5 severity")
    else:
        differing.append("PM2.5 severity")

    # Trajectory
    d = _exact_distance(current.trajectory, historical.trajectory)
    w = FEATURE_WEIGHTS["trajectory"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("trajectory")
    else:
        differing.append("trajectory")

    # Wind sector
    d = _sector_distance(current.wind_sector, historical.wind_sector)
    w = FEATURE_WEIGHTS["wind_sector"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("wind sector")
    else:
        differing.append("wind sector")

    # Wind speed band
    d = _band_distance(
        current.wind_speed_band, historical.wind_speed_band, WIND_SPEED_BAND_ORDER
    )
    w = FEATURE_WEIGHTS["wind_speed_band"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("wind speed")
    else:
        differing.append("wind speed")

    # Temperature band
    d = _band_distance(
        current.temperature_band, historical.temperature_band, TEMPERATURE_BAND_ORDER
    )
    w = FEATURE_WEIGHTS["temperature_band"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("temperature")
    else:
        differing.append("temperature")

    # Humidity band
    d = _band_distance(
        current.humidity_band, historical.humidity_band, HUMIDITY_BAND_ORDER
    )
    w = FEATURE_WEIGHTS["humidity_band"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("humidity")
    else:
        differing.append("humidity")

    # Investigation corridor
    d = _exact_distance(current.investigation_corridor, historical.investigation_corridor)
    w = FEATURE_WEIGHTS["investigation_corridor"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("investigation corridor")
    else:
        differing.append("investigation corridor")

    # Eligible domains
    d = _list_distance(current.eligible_domains, historical.eligible_domains)
    w = FEATURE_WEIGHTS["eligible_domains"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("investigation domains")
    else:
        differing.append("investigation domains")

    # Episode state
    d = _exact_distance(current.episode_state, historical.episode_state)
    w = FEATURE_WEIGHTS["episode_state"]
    total_distance += d * w
    total_weight += w
    if d == 0.0:
        matching.append("episode state")
    else:
        differing.append("episode state")

    # Normalize to [0, 1]
    normalized_distance = total_distance / total_weight if total_weight > 0 else 1.0
    similarity_score = 1.0 - normalized_distance

    return round(similarity_score, 3), matching, differing


# ── Reliability Calculation ────────────────────────────────────


def compute_reliability(
    useful: int,
    partially_useful: int,
    not_supported: int,
    inconclusive: int,
) -> ReliabilityScore:
    """Compute deterministic reliability from verified outcome counts.

    Formula:
    - USEFUL = 1.0, PARTIALLY_USEFUL = 0.5, NOT_SUPPORTED = 0.0
    - INCONCLUSIVE excluded from calculation
    - Score = (useful × 1.0 + partially × 0.5) / total_evaluated × 100

    Classification based on total_evaluated:
    - 0-2: INSUFFICIENT
    - 3-5: LIMITED
    - 6-9: MODERATE
    - 10+: STRONG
    """
    total_evaluated = useful + partially_useful + not_supported
    total_all = useful + partially_useful + not_supported + inconclusive

    # Classification
    if total_evaluated >= MIN_CASES_FOR_STRONG:
        classification = ReliabilityClassification.STRONG
    elif total_evaluated >= MIN_CASES_FOR_MODERATE:
        classification = ReliabilityClassification.MODERATE
    elif total_evaluated >= MIN_CASES_FOR_LIMITED:
        classification = ReliabilityClassification.LIMITED
    else:
        classification = ReliabilityClassification.INSUFFICIENT

    # Score calculation
    score = None
    description = ""

    if total_evaluated >= MIN_CASES_FOR_LIMITED:
        weighted_sum = useful * 1.0 + partially_useful * 0.5
        score = round((weighted_sum / total_evaluated) * 100, 1)

        if score >= 80:
            description = (
                "Similar previously verified investigations were useful in most cases."
            )
        elif score >= 60:
            description = (
                "Similar previously verified investigations were frequently useful."
            )
        elif score >= 40:
            description = (
                "Similar previously verified investigations had mixed outcomes."
            )
        else:
            description = (
                "Similar previously verified investigations were frequently not supported by field findings."
            )
    else:
        description = (
            "Not enough similar verified investigations exist to estimate historical reliability."
        )

    return ReliabilityScore(
        score=score,
        classification=classification,
        description=description,
        useful_count=useful,
        partially_useful_count=partially_useful,
        not_supported_count=not_supported,
        inconclusive_count=inconclusive,
        total_evaluated=total_evaluated,
    )


# ── Band Classification Helpers ────────────────────────────────


def classify_pm25_band(value: float | None) -> str:
    """Classify PM2.5 value into severity band."""
    if value is None:
        return "UNKNOWN"
    if value < 12:
        return "GOOD"
    if value < 35.5:
        return "MODERATE"
    if value < 55.5:
        return "UNHEALTHY_SENSITIVE"
    if value < 150.5:
        return "UNHEALTHY"
    if value < 250.5:
        return "VERY_UNHEALTHY"
    return "HAZARDOUS"


def classify_wind_speed_band(value: float | None) -> str:
    """Classify wind speed into band."""
    if value is None:
        return "UNKNOWN"
    if value < 1.5:
        return "CALM"
    if value < 5.0:
        return "LIGHT"
    if value < 10.0:
        return "MODERATE"
    return "STRONG"


def classify_temperature_band(value: float | None) -> str:
    """Classify temperature into band."""
    if value is None:
        return "UNKNOWN"
    if value < 10:
        return "COLD"
    if value < 20:
        return "COOL"
    if value < 30:
        return "WARM"
    return "HOT"


def classify_humidity_band(value: float | None) -> str:
    """Classify humidity into band."""
    if value is None:
        return "UNKNOWN"
    if value < 40:
        return "DRY"
    if value < 70:
        return "MODERATE"
    return "HUMID"


# ── Context Building ───────────────────────────────────────────


def build_context_from_evidence(evidence: dict) -> InvestigationContextSnapshot:
    """Extract investigation context from an evidence package.

    Builds a similarity-matching context from the investigation
    evidence package structure.
    """
    # PM2.5 from event detection
    pm25_value = None
    pm25_severity = "UNKNOWN"
    event_data = evidence.get("event_detection", {}).get("data")
    if event_data:
        current_pm25 = event_data.get("current_pm25")
        if current_pm25 is not None:
            pm25_value = float(current_pm25)
            pm25_severity = classify_pm25_band(pm25_value)
        episode_state = event_data.get("state", "UNKNOWN")
        trajectory = event_data.get("trajectory", "UNKNOWN")
    else:
        episode_state = "UNKNOWN"
        trajectory = "UNKNOWN"

    # Weather from weather_context
    wind_sector = "UNKNOWN"
    wind_speed_ms = None
    wind_speed_band = "UNKNOWN"
    temperature_c = None
    temperature_band = "UNKNOWN"
    humidity_pct = None
    humidity_band = "UNKNOWN"

    weather_vars = evidence.get("weather_context", {}).get("variables", [])
    for var in weather_vars:
        name = var.get("name", "").lower()
        value = var.get("value")
        if value is not None:
            value = float(value)
        if "temperature" in name:
            temperature_c = value
            temperature_band = classify_temperature_band(value)
        elif "humidity" in name:
            humidity_pct = value
            humidity_band = classify_humidity_band(value)
        elif "wind_speed" in name or "wind" in name and "speed" in name:
            wind_speed_ms = value
            wind_speed_band = classify_wind_speed_band(value)
        elif "wind_direction" in name:
            pass  # Direction handled separately

    # Wind sector from source compass
    compass = evidence.get("directional_analysis")
    if compass:
        current_wind = compass.get("current_wind", {})
        wind_sector = current_wind.get("sector", "UNKNOWN")

    # Investigation corridor from geographic context
    investigation_corridor = "UNKNOWN"
    geo_ctx = evidence.get("geographic_context", {})
    corridor_hint = geo_ctx.get("suggested_search_corridor", {})
    if corridor_hint:
        investigation_corridor = corridor_hint.get("label", "UNKNOWN")

    # Eligible domains
    eligible_domains = []
    domains = evidence.get("investigation_domains", [])
    for domain in domains:
        if domain.get("conditions_met", False):
            eligible_domains.append(domain.get("id", ""))

    return InvestigationContextSnapshot(
        pm25_value=pm25_value,
        pm25_severity_band=pm25_severity,
        wind_sector=wind_sector,
        wind_speed_ms=wind_speed_ms,
        wind_speed_band=wind_speed_band,
        temperature_c=temperature_c,
        temperature_band=temperature_band,
        humidity_pct=humidity_pct,
        humidity_band=humidity_band,
        investigation_corridor=investigation_corridor,
        eligible_domains=eligible_domains,
        trajectory=trajectory,
        episode_state=episode_state,
    )


# ── Core Learning Analytics ────────────────────────────────────


def compute_investigation_learning(
    db_path: Path,
    current_evidence: dict,
) -> InvestigationLearningResponse:
    """Compute investigation learning accountability context.

    Deterministic analysis of verified historical investigation outcomes.
    Finds similar verified cases and computes reliability scores.

    Args:
        db_path: Path to the SQLite database.
        current_evidence: Current investigation evidence package (dict).

    Returns:
        InvestigationLearningResponse with accountability context.
    """
    logger.info("Computing investigation learning accountability context")

    # Build current context from evidence
    current_context = build_context_from_evidence(current_evidence)

    # Fetch all non-PENDING verification outcomes with context
    all_outcomes = _fetch_outcomes_with_context(db_path)

    if not all_outcomes:
        return InvestigationLearningResponse(
            historical_investigations_found=0,
            evidence_status=EvidenceStatus.INSUFFICIENT,
            historical_context_message="",
            limitations=[
                "No verified investigation history is available yet.",
                "Recommendations will become accountable to historical outcomes "
                "as human verification records are collected.",
            ],
        )

    # Compute similarity for each historical outcome
    cases_with_similarity: list[tuple[dict, float, list[str], list[str]]] = []

    for outcome_row in all_outcomes:
        # Parse stored context snapshot
        context_json = outcome_row.get("investigation_context")
        if context_json:
            try:
                hist_context = InvestigationContextSnapshot(**json.loads(context_json))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        else:
            continue

        similarity, matching, differing = compute_similarity(
            current_context, hist_context
        )

        cases_with_similarity.append((outcome_row, similarity, matching, differing))

    if not cases_with_similarity:
        return InvestigationLearningResponse(
            historical_investigations_found=0,
            evidence_status=EvidenceStatus.INSUFFICIENT,
            historical_context_message="",
            limitations=[
                "No verified investigation outcomes with environmental context "
                "were found for similarity matching.",
                "Similarity matching requires stored environmental context "
                "snapshots alongside verification outcomes.",
            ],
        )

    # Sort by similarity (highest first), take top N
    cases_with_similarity.sort(key=lambda x: x[1], reverse=True)
    top_cases = cases_with_similarity[:MAX_SIMILAR_CASES]

    # Build similar cases list
    similar_cases: list[SimilarCase] = []
    useful = 0
    partially_useful = 0
    not_supported = 0
    inconclusive = 0

    # Count ALL similar cases (not just top N) for reliability
    for row, sim_score, matching, differing in cases_with_similarity:
        status_str = row["overall_status"]
        if status_str == "USEFUL":
            useful += 1
        elif status_str == "PARTIALLY_USEFUL":
            partially_useful += 1
        elif status_str == "NOT_SUPPORTED":
            not_supported += 1
        elif status_str == "INCONCLUSIVE":
            inconclusive += 1

    # Build similar case summaries for top N
    for row, sim_score, matching, differing in top_cases:
        # Generate brief summary
        status_str = row["overall_status"]
        rec_str = row.get("recommendation_verification", "UNKNOWN")
        summary = _generate_case_summary(status_str, rec_str, row.get("field_notes", ""))

        similar_cases.append(SimilarCase(
            investigation_id=row["investigation_id"],
            outcome_id=row["outcome_id"],
            similarity_score=sim_score,
            date=row.get("verified_at") or row.get("created_at", "Unknown date"),
            overall_status=status_str,
            recommendation_verification=rec_str,
            summary=summary,
            matching_dimensions=matching,
            differing_dimensions=differing,
        ))

    # Compute reliability
    reliability = compute_reliability(useful, partially_useful, not_supported, inconclusive)

    # Determine evidence status from total
    total = useful + partially_useful + not_supported + inconclusive
    if total >= MIN_CASES_FOR_STRONG:
        evidence_status = EvidenceStatus.STRONG
    elif total >= MIN_CASES_FOR_MODERATE:
        evidence_status = EvidenceStatus.MODERATE
    elif total >= MIN_CASES_FOR_LIMITED:
        evidence_status = EvidenceStatus.LIMITED
    else:
        evidence_status = EvidenceStatus.INSUFFICIENT

    # Generate historical context message
    historical_context_message = _generate_context_message(
        total, useful, partially_useful, not_supported, reliability
    )

    # Build limitations
    limitations = _build_limitations(total, evidence_status, reliability)

    response = InvestigationLearningResponse(
        historical_investigations_found=total,
        verified_outcomes={
            "useful": useful,
            "partially_useful": partially_useful,
            "not_supported": not_supported,
            "inconclusive": inconclusive,
        },
        recommendation_reliability=reliability,
        similar_cases=similar_cases,
        limitations=limitations,
        evidence_status=evidence_status,
        historical_context_message=historical_context_message,
    )

    logger.info(
        "Investigation learning context computed",
        similar_found=total,
        top_similar=len(similar_cases),
        reliability=reliability.score,
        evidence_status=evidence_status.value,
    )

    return response


# ── Database Queries ───────────────────────────────────────────


def _fetch_outcomes_with_context(db_path: Path) -> list[dict]:
    """Fetch all non-PENDING verification outcomes with context snapshots.

    Returns list of row dicts (SQLite Row objects converted to dicts).
    """
    conn = _get_read_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT outcome_id, investigation_id, overall_status,
                   recommendation_verification, investigation_area_verification,
                   hypothesis_verifications, field_notes, verified_by,
                   verified_at, created_at, updated_at, investigation_context
            FROM verification_outcomes
            WHERE overall_status != 'PENDING'
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        # Column investigation_context may not exist yet (pre-migration)
        # Fall back to querying without it
        rows = conn.execute(
            """
            SELECT outcome_id, investigation_id, overall_status,
                   recommendation_verification, investigation_area_verification,
                   hypothesis_verifications, field_notes, verified_by,
                   verified_at, created_at, updated_at, NULL as investigation_context
            FROM verification_outcomes
            WHERE overall_status != 'PENDING'
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Message Generation ─────────────────────────────────────────


def _generate_case_summary(
    overall_status: str,
    recommendation_verification: str,
    field_notes: str,
) -> str:
    """Generate a brief summary for a similar historical case."""
    status_phrases = {
        "USEFUL": "Investigation recommendations were confirmed useful after field review.",
        "PARTIALLY_USEFUL": "Investigation recommendations were partially supported by field findings.",
        "NOT_SUPPORTED": "Investigation recommendations were not supported by field findings.",
        "INCONCLUSIVE": "Investigation outcome was inconclusive.",
    }
    base = status_phrases.get(overall_status, "Outcome recorded.")

    rec_phrases = {
        "SUPPORTED": " Investigation corridor was supported.",
        "PARTIALLY_SUPPORTED": " Investigation corridor was partially supported.",
        "NOT_SUPPORTED": " Investigation corridor was not supported.",
    }
    rec_addon = rec_phrases.get(recommendation_verification, "")

    if field_notes and len(field_notes) > 10:
        notes_preview = field_notes[:80]
        if len(field_notes) > 80:
            notes_preview += "..."
        return f"{base}{rec_addon} Notes: {notes_preview}"

    return base + rec_addon


def _generate_context_message(
    total: int,
    useful: int,
    partially_useful: int,
    not_supported: int,
    reliability: ReliabilityScore,
) -> str:
    """Generate human-readable historical context message."""
    if total == 0:
        return ""

    verified_count = useful + partially_useful
    if total <= 2:
        return (
            f"Only {total} similar verified investigation"
            f"{'s' if total != 1 else ''} found. "
            "Not enough historical data for reliable accountability assessment."
        )

    if reliability.score is not None:
        if reliability.score >= 80:
            assessment = "were verified or partially verified in most cases"
        elif reliability.score >= 60:
            assessment = "were frequently verified or partially verified"
        elif reliability.score >= 40:
            assessment = "had mixed outcomes"
        else:
            assessment = "were frequently not supported by field findings"
    else:
        assessment = "had mixed outcomes"

    return (
        f"Among {total} similar investigations that were later reviewed by humans, "
        f"investigation recommendations {assessment}."
    )


def _build_limitations(
    total: int,
    evidence_status: EvidenceStatus,
    reliability: ReliabilityScore,
) -> list[str]:
    """Build mandatory limitations list."""
    limitations: list[str] = []

    if evidence_status == EvidenceStatus.INSUFFICIENT:
        limitations.append(
            "Not enough similar verified investigations exist to estimate "
            "historical reliability."
        )
    elif evidence_status == EvidenceStatus.LIMITED:
        limitations.append(
            "Historical verification data is limited. Reliability estimates "
            "may not be representative."
        )

    limitations.append(
        "Past outcomes do not prove the current recommendation is correct."
    )
    limitations.append(
        "Similarity is based on available environmental and investigation context."
    )
    limitations.append(
        "Historical verification provides accountability context, not confirmation."
    )

    return limitations
