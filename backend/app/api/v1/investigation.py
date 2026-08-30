"""Investigation Evidence API endpoints.

Endpoints:
    GET /api/v1/investigation/current
        → Assembled evidence package for the current pollution event

    GET /api/v1/investigation/analyze
        → AI reasoning analysis with evidence (supports ?demo=true)

    GET /api/v1/investigation/exposure
        → Deterministic exposure geometry (wind-driven, no AI)

    GET /api/v1/investigation/learning
        → Historical investigation learning context (deterministic, no AI)

Design:
    - Assembles evidence from existing services (no new ML)
    - Each data source is independently failure-isolated
    - Partial results returned when any source fails
    - Every field tagged with evidence_type: observed/inferred/hypothesis
    - Never fails completely — returns package with limitations
    - /analyze endpoint never returns HTTP 500 due to AI failure
    - /exposure is deterministic (no AI dependency)
    - /learning is deterministic — compares against verified historical outcomes
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from ...core.config import get_settings
from ...core.errors import ErrorCode
from ...modeling.serving.ai_reasoning import analyze_investigation
from ...modeling.serving.investigation import assemble_investigation_evidence
from ...application.services.exposure import compute_exposure_geometry
from ...application.services.investigation_learning import compute_investigation_learning

router = APIRouter(prefix="/investigation", tags=["investigation"])


# -- Helpers --------------------------------------------------------------


def _resolve_backend_root() -> Path:
    """Resolve the backend/ project root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_db_path() -> Path:
    """Get resolved database path."""
    settings = get_settings()
    backend_dir = _resolve_backend_root()
    db_path = settings.database_url.replace("sqlite:///", "")
    db_path_obj = Path(db_path)
    if not db_path_obj.is_absolute():
        db_path_obj = backend_dir / db_path_obj
    return db_path_obj


# -- Endpoint -------------------------------------------------------------


@router.get(
    "/current",
    summary="Get investigation evidence package",
    description=(
        "Assembles all available data sources into a structured evidence "
        "package for the current pollution event investigation. "
        "Combines episode detection, directional analysis, weather context, "
        "investigation domains, and historical analogs. "
        "Each field is tagged with evidence_type (observed/inferred/hypothesis). "
        "Never fails completely — returns partial results with limitations."
    ),
)
async def get_investigation_evidence() -> dict:
    """Get the investigation evidence package for current conditions.

    Returns a structured evidence package with:
    - Event detection (episode state, trajectory)
    - Weather context (variables, pattern match)
    - Directional analysis (source compass with interpretation)
    - Investigation domains (weather-trigger evaluated)
    - Historical analogs (similar past episodes)
    - Geographic context (grid point, search corridor)
    - Data quality (freshness, limitations)
    - System limitations (what is missing and why)

    Evidence types:
    - observed: directly measured data, highest confidence
    - inferred: derived from statistical analysis, medium confidence
    - hypothesis: domain-informed weather matching, lowest confidence
    """
    db_path = _get_db_path()

    # Validate database exists
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.DATA_SOURCE_UNAVAILABLE.value,
                    "message": "Database not found",
                    "details": {"error": "Database not available"},
                }
            },
        )

    try:
        package = assemble_investigation_evidence(db_path)
        return package.to_dict()

    except Exception as exc:
        logger.error("Investigation evidence assembly failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.get(
    "/analyze",
    summary="AI investigation reasoning analysis",
    description=(
        "Runs AI-powered investigation reasoning on the assembled evidence package. "
        "Returns both the raw evidence and the AI analysis including hypotheses, "
        "recommended actions, and uncertainties. "
        "Supports ?demo=true for deterministic demo fixture. "
        "Never returns HTTP 500 due to AI failure — always returns a response "
        "with analysis_status indicating availability."
    ),
)
async def get_investigation_analysis(
    demo: bool = Query(
        default=False,
        description="If true, return deterministic demo fixture (no AI call)",
    ),
) -> dict:
    """Run AI investigation reasoning on current conditions.

    Response includes:
    - evidence: the raw evidence package
    - analysis: AI-generated hypotheses, facts, recommendations, uncertainties
    - analysis_metadata: provider info, mode, timestamp

    The analysis_status field indicates:
    - "complete": full AI analysis available
    - "limited": partial analysis with caveats
    - "unavailable": AI failed, deterministic fallback returned

    This endpoint NEVER fails with HTTP 500. If AI is unavailable, it returns
    a fallback response with analysis_status="unavailable".
    """
    db_path = _get_db_path()

    # Validate database exists (this is the only hard requirement)
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.DATA_SOURCE_UNAVAILABLE.value,
                    "message": "Database not found",
                    "details": {"error": "Database not available"},
                }
            },
        )

    # Assemble evidence first (this is deterministic, not AI-dependent)
    try:
        evidence = assemble_investigation_evidence(db_path).to_dict()
    except Exception as exc:
        logger.error("Evidence assembly failed for /analyze", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )

    # Run AI analysis — never return HTTP 500 on AI failure
    try:
        result = await analyze_investigation(
            evidence_package=evidence,
            db_path=db_path,
            use_demo=demo,
        )
        response = result.model_dump()
    except Exception as exc:
        logger.error("AI analysis endpoint error (returning fallback)", error=str(exc))
        # Absolute safety net: even if analyze_investigation itself raises,
        # return a valid fallback response
        from datetime import UTC, datetime
        from ...modeling.serving.ai_reasoning import _build_fallback_response
        fallback = _build_fallback_response(
            evidence,
            reason=f"Unexpected analysis error: {exc}",
        )
        response = fallback.model_dump()

    # ── Attach exposure geometry (deterministic, AI-independent) ──
    try:
        exposure = _compute_exposure_from_evidence(evidence, demo=demo)
        response["exposure_geometry"] = exposure
    except Exception as exc:
        logger.warning("Exposure geometry computation failed", error=str(exc))
        response["exposure_geometry"] = {
            "event_location": {"lat": 31.5204, "lng": 74.3587},
            "investigation_area": None,
            "exposure_path": None,
            "vulnerable_locations": {"schools": [], "hospitals": [], "summary": {"schools_in_path": 0, "hospitals_in_path": 0}},
            "uncertainty": f"Exposure geometry unavailable: {exc}",
        }

    return response


@router.get(
    "/exposure",
    summary="Deterministic exposure geometry",
    description=(
        "Returns wind-driven exposure geometry for the current pollution event. "
        "This is purely deterministic — no AI is involved. "
        "Includes upwind investigation corridor, downwind exposure cone, "
        "and vulnerable locations (schools, hospitals) from OpenStreetMap. "
        "Gracefully degrades when wind data or Overpass API is unavailable."
    ),
)
async def get_exposure_geometry(
    demo: bool = Query(
        default=False,
        description="If true, return deterministic demo fixture",
    ),
) -> dict:
    """Get deterministic exposure geometry for the current pollution event.

    Response includes:
    - event_location: current observation point
    - investigation_area: upwind corridor polygon
    - exposure_path: downwind cone polygon
    - vulnerable_locations: schools and hospitals from OSM

    This endpoint NEVER fails due to AI — geometry is deterministic.
    Missing wind data returns a degraded response with event location only.
    """
    if demo:
        return _get_demo_exposure_geometry()

    db_path = _get_db_path()

    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.DATA_SOURCE_UNAVAILABLE.value,
                    "message": "Database not found",
                    "details": {"error": "Database not available"},
                }
            },
        )

    try:
        evidence = assemble_investigation_evidence(db_path).to_dict()
        return _compute_exposure_from_evidence(evidence)
    except Exception as exc:
        logger.error("Exposure geometry endpoint failed", error=str(exc))
        # Return degraded response — never HTTP 500 for geometry
        return {
            "event_location": {"lat": 31.5204, "lng": 74.3587},
            "investigation_area": None,
            "exposure_path": None,
            "vulnerable_locations": {"schools": [], "hospitals": [], "summary": {"schools_in_path": 0, "hospitals_in_path": 0}},
            "uncertainty": f"Exposure geometry computation failed: {exc}",
        }


@router.get(
    "/learning",
    summary="Investigation learning context from verified historical outcomes",
    description=(
        "Deterministic comparison of the current investigation against previously "
        "verified investigation outcomes. Shows what percentage of similar past "
        "investigations were found useful, partially useful, or not supported. "
        "Requires at least 3 verified cases before showing statistics. "
        "Supports ?demo=true for deterministic demo fixture with 12 cases. "
        "NO machine learning — purely rule-based similarity matching."
    ),
)
async def get_investigation_learning(
    demo: bool = Query(
        default=False,
        description="If true, return deterministic demo fixture with 12 cases",
    ),
) -> dict:
    """Get investigation learning context from verified historical outcomes.

    Compares the current investigation context against previously verified
    investigation outcomes using deterministic similarity matching.

    Returns:
    - historical_investigations_found: count of verified outcomes
    - verified_outcomes: breakdown by status
    - recommendation_reliability: score and classification
    - similar_cases: top-N most similar verified cases
    - limitations: mandatory caveats about this context
    - evidence_status: INSUFFICIENT / LIMITED / MODERATE / STRONG
    - historical_context_message: transparent human-readable summary
    - disclaimer: what this does and does not mean

    Important: This is NOT a prediction. It provides accountability context
    from similar past verified investigations only.
    """
    db_path = _get_db_path()

    if demo:
        return _get_demo_investigation_learning()

    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.DATA_SOURCE_UNAVAILABLE.value,
                    "message": "Database not found",
                    "details": {"error": "Database not available"},
                }
            },
        )

    try:
        # Assemble current evidence for context snapshot
        evidence = assemble_investigation_evidence(db_path).to_dict()

        result = compute_investigation_learning(
            db_path=db_path,
            current_evidence=evidence,
        )
        return result.model_dump()

    except Exception as exc:
        logger.error("Investigation learning endpoint failed", error=str(exc))
        # Never HTTP 500 — return degraded response
        return {
            "historical_investigations_found": 0,
            "verified_outcomes": {
                "useful": 0,
                "partially_useful": 0,
                "not_supported": 0,
                "inconclusive": 0,
                "pending": 0,
                "total_verified": 0,
            },
            "recommendation_reliability": {
                "score": None,
                "classification": "INSUFFICIENT",
                "description": "Unable to compute reliability: service temporarily unavailable.",
                "useful_count": 0,
                "partially_useful_count": 0,
                "not_supported_count": 0,
                "inconclusive_count": 0,
                "total_evaluated": 0,
            },
            "similar_cases": [],
            "limitations": [
                "Investigation learning service is temporarily unavailable.",
                "No historical context is available for this investigation.",
                f"Service error: {exc}",
            ],
            "evidence_status": "INSUFFICIENT",
            "historical_context_message": (
                "No historical investigation context is available at this time."
            ),
            "disclaimer": (
                "This service compares the current investigation against previously "
                "verified outcomes to provide accountability context. It does NOT "
                "make predictions or recommendations."
            ),
        }


# ── Helpers ───────────────────────────────────────────────────


def _compute_exposure_from_evidence(
    evidence: dict,
    demo: bool = False,
) -> dict:
    """Extract wind data from evidence package and compute exposure geometry.

    This is the bridge between the evidence assembler and the exposure service.
    It extracts the necessary wind data from the evidence package and delegates
    to compute_exposure_geometry() for the actual coordinate calculation.
    """
    # Extract wind data from directional analysis
    compass = evidence.get("directional_analysis") or {}
    current_wind = compass.get("current_wind") or {}

    wind_degrees = current_wind.get("direction_degrees")
    wind_speed = current_wind.get("wind_speed_ms")

    # Extract event data
    event_detection = evidence.get("event_detection") or {}
    event_data = event_detection.get("data") or {}

    lat = 31.5204  # Default Lahore center
    lng = 74.3587
    pm25 = event_data.get("current_pm25")
    severity = event_data.get("state")
    trajectory = event_data.get("trajectory")

    return compute_exposure_geometry(
        lat=lat,
        lng=lng,
        wind_direction_degrees=wind_degrees,
        wind_speed_ms=wind_speed,
        pm25=pm25,
        severity=severity,
        trajectory=trajectory,
    )


def _get_demo_exposure_geometry() -> dict:
    """Return deterministic demo exposure geometry.

    Wind is FROM East (90°), moving toward West (270°).
    Demo coordinates: US Embassy area (31.5204, 74.3587).
    """
    return compute_exposure_geometry(
        lat=31.5204,
        lng=74.3587,
        wind_direction_degrees=90.0,
        wind_speed_ms=3.2,
        pm25=165.0,
        severity="episode",
        trajectory="rising",
    )


def _get_demo_investigation_learning() -> dict:
    """Return deterministic demo investigation learning response.

    12 verified cases: 8 USEFUL, 3 PARTIALLY_USEFUL, 1 NOT_SUPPORTED
    Reliability: ~79% (weighted score)

    Framing: always uses "Similar previously verified investigations showed..."
    Never: "The AI learned that..."
    """
    return {
        "historical_investigations_found": 12,
        "verified_outcomes": {
            "useful": 8,
            "partially_useful": 3,
            "not_supported": 1,
            "inconclusive": 0,
            "pending": 0,
            "total_verified": 12,
        },
        "recommendation_reliability": {
            "score": 0.79,
            "classification": "MODERATE",
            "description": (
                "Of 12 similar previously verified investigations, "
                "8 were found useful, 3 partially useful, and 1 not supported. "
                "This suggests moderate reliability for similar conditions."
            ),
            "useful_count": 8,
            "partially_useful_count": 3,
            "not_supported_count": 1,
            "inconclusive_count": 0,
            "total_evaluated": 12,
        },
        "similar_cases": [
            {
                "investigation_id": "INV-2024-0892",
                "outcome_id": "VER-2024-0892",
                "similarity_score": 0.92,
                "date": "2024-11-15",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "High PM25 episode with east wind sector. Open burning and "
                    "traffic emissions confirmed as primary sources. Investigation "
                    "corridor aligned with known industrial zone."
                ),
                "matching_dimensions": [
                    "pm25_severity_band",
                    "wind_sector",
                    "trajectory",
                    "investigation_corridor",
                ],
                "differing_dimensions": ["humidity_band"],
            },
            {
                "investigation_id": "INV-2024-0756",
                "outcome_id": "VER-2024-0756",
                "similarity_score": 0.87,
                "date": "2024-10-28",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "Similar episode-level PM25 with moderate wind. Road dust "
                    "and traffic emissions were primary contributors. Industrial "
                    "sources were secondary."
                ),
                "matching_dimensions": [
                    "pm25_severity_band",
                    "wind_sector",
                    "wind_speed_band",
                ],
                "differing_dimensions": ["temperature_band", "investigation_corridor"],
            },
            {
                "investigation_id": "INV-2024-0634",
                "outcome_id": "VER-2024-0634",
                "similarity_score": 0.81,
                "date": "2024-10-12",
                "overall_status": "PARTIALLY_USEFUL",
                "recommendation_verification": "PARTIALLY_SUPPORTED",
                "summary": (
                    "Episode PM25 with east wind. Industrial sources were overestimated; "
                    "actual primary source was agricultural burning in nearby peri-urban area."
                ),
                "matching_dimensions": [
                    "pm25_severity_band",
                    "wind_sector",
                ],
                "differing_dimensions": [
                    "investigation_corridor",
                    "eligible_domains",
                    "humidity_band",
                ],
            },
            {
                "investigation_id": "INV-2024-0501",
                "outcome_id": "VER-2024-0501",
                "similarity_score": 0.76,
                "date": "2024-09-22",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "Moderate-high PM25 with light east wind. Traffic emissions "
                    "and road dust confirmed. Investigation area matched predictions."
                ),
                "matching_dimensions": [
                    "wind_sector",
                    "wind_speed_band",
                    "eligible_domains",
                ],
                "differing_dimensions": [
                    "pm25_severity_band",
                    "investigation_corridor",
                ],
            },
            {
                "investigation_id": "INV-2024-0389",
                "outcome_id": "VER-2024-0389",
                "similarity_score": 0.73,
                "date": "2024-09-08",
                "overall_status": "NOT_SUPPORTED",
                "recommendation_verification": "NOT_SUPPORTED",
                "summary": (
                    "PM25 episode with east wind but higher wind speeds than typical. "
                    "Open burning was hypothesized but field investigation found no "
                    "evidence — sources were predominantly vehicular."
                ),
                "matching_dimensions": [
                    "wind_sector",
                    "pm25_severity_band",
                ],
                "differing_dimensions": [
                    "wind_speed_band",
                    "eligible_domains",
                    "investigation_corridor",
                ],
            },
            {
                "investigation_id": "INV-2024-0267",
                "outcome_id": "VER-2024-0267",
                "similarity_score": 0.70,
                "date": "2024-08-25",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "Rising PM25 trajectory with east wind. Open burning and traffic "
                    "emissions confirmed. Investigation corridor matched known hotspots."
                ),
                "matching_dimensions": [
                    "trajectory",
                    "wind_sector",
                    "investigation_corridor",
                ],
                "differing_dimensions": ["temperature_band", "humidity_band"],
            },
            {
                "investigation_id": "INV-2024-0145",
                "outcome_id": "VER-2024-0145",
                "similarity_score": 0.68,
                "date": "2024-08-10",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "Episode-level PM25 with moderate east wind. Traffic and road dust "
                    "were primary contributors, consistent with predictions."
                ),
                "matching_dimensions": [
                    "pm25_severity_band",
                    "wind_sector",
                    "eligible_domains",
                ],
                "differing_dimensions": [
                    "wind_speed_band",
                    "investigation_corridor",
                ],
            },
            {
                "investigation_id": "INV-2024-0102",
                "outcome_id": "VER-2024-0102",
                "similarity_score": 0.65,
                "date": "2024-07-30",
                "overall_status": "PARTIALLY_USEFUL",
                "recommendation_verification": "PARTIALLY_SUPPORTED",
                "summary": (
                    "Moderate PM25 with variable wind direction. Sources were mixed — "
                    "industrial and traffic both contributed but proportions differed "
                    "from predictions."
                ),
                "matching_dimensions": [
                    "wind_sector",
                    "trajectory",
                ],
                "differing_dimensions": [
                    "pm25_severity_band",
                    "investigation_corridor",
                    "wind_speed_band",
                ],
            },
            {
                "investigation_id": "INV-2024-0078",
                "outcome_id": "VER-2024-0078",
                "similarity_score": 0.62,
                "date": "2024-07-15",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "High PM25 with east-southeast wind. Open burning detected in "
                    "investigation corridor. Seasonal pattern consistent with known "
                    "burning cycles."
                ),
                "matching_dimensions": [
                    "pm25_severity_band",
                    "investigation_corridor",
                ],
                "differing_dimensions": [
                    "wind_sector",
                    "wind_speed_band",
                    "humidity_band",
                ],
            },
            {
                "investigation_id": "INV-2024-0045",
                "outcome_id": "VER-2024-0045",
                "similarity_score": 0.58,
                "date": "2024-07-01",
                "overall_status": "PARTIALLY_USEFUL",
                "recommendation_verification": "PARTIALLY_SUPPORTED",
                "summary": (
                    "Moderate episode PM25 with light wind. Industrial sources were "
                    "overestimated; road dust was the actual primary source."
                ),
                "matching_dimensions": [
                    "wind_speed_band",
                    "trajectory",
                ],
                "differing_dimensions": [
                    "pm25_severity_band",
                    "investigation_corridor",
                    "eligible_domains",
                ],
            },
            {
                "investigation_id": "INV-2024-0023",
                "outcome_id": "VER-2024-0023",
                "similarity_score": 0.55,
                "date": "2024-06-15",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "PM25 rising event with moderate east wind. Traffic emissions and "
                    "open burning confirmed by ground observation."
                ),
                "matching_dimensions": [
                    "wind_sector",
                    "eligible_domains",
                ],
                "differing_dimensions": [
                    "pm25_severity_band",
                    "investigation_corridor",
                    "temperature_band",
                ],
            },
            {
                "investigation_id": "INV-2023-1201",
                "outcome_id": "VER-2023-1201",
                "similarity_score": 0.52,
                "date": "2024-05-20",
                "overall_status": "USEFUL",
                "recommendation_verification": "SUPPORTED",
                "summary": (
                    "Winter episode PM25 with east wind. Multiple sources confirmed: "
                    "traffic, open burning, and road dust. Investigation corridor "
                    "aligned well with ground truth."
                ),
                "matching_dimensions": [
                    "wind_sector",
                    "trajectory",
                ],
                "differing_dimensions": [
                    "pm25_severity_band",
                    "wind_speed_band",
                    "investigation_corridor",
                ],
            },
        ],
        "limitations": [
            "This analysis is based on 12 previously verified investigations — a small sample that may not represent all future conditions.",
            "Similarity matching uses 9 environmental dimensions with fixed weights; real-world conditions may differ in unmeasured ways.",
            "Historical verification outcomes reflect the judgment of individual verifiers and may contain bias.",
            "This provides accountability context, NOT a prediction of what will happen or what the AI recommends.",
            "Conditions not well-represented in the historical database may produce misleading similarity scores.",
            "The similarity algorithm is deterministic and rule-based — it does not learn or improve over time.",
        ],
        "evidence_status": "MODERATE",
        "historical_context_message": (
            "Similar previously verified investigations in the east wind sector with "
            "episode-level PM25 showed that investigation recommendations were useful "
            "in about 79% of cases (8 of 12). Open burning and traffic emissions were "
            "the most commonly confirmed sources in this pattern. However, industrial "
            "sources were sometimes overestimated — one investigation found no industrial "
            "contribution where it was hypothesized."
        ),
        "disclaimer": (
            "This context is derived from deterministic comparison with previously "
            "verified investigations. It does NOT represent the AI's opinion, prediction, "
            "or recommendation. It is provided solely for accountability and transparency "
            "so that users can see how reliable similar past investigations have been. "
            "Historical verification outcomes are the work of human verifiers and do not "
            "guarantee similar results for the current investigation."
        ),
    }
