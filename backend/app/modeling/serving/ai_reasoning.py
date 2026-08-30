"""AI Investigation Reasoning Service.

Assembles the AI-powered investigation analysis by:
1. Calling the evidence assembler
2. Sending structured evidence to an OpenAI-compatible API
3. Parsing and validating the structured response
4. Post-processing: confidence caps, evidence reference validation
5. Deterministic fallback on any failure

Provider: configurable via LPA_AI_PROVIDER env var.
Default: "openai" (any OpenAI-compatible API works).
No provider-specific SDK required — uses httpx directly.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from ...core.config import get_settings
from .ai_prompts import INVESTIGATION_SYSTEM_PROMPT, INVESTIGATION_USER_TEMPLATE, KNOWN_EVIDENCE_PATHS
from .ai_schemas import AIInvestigationResult, InvestigationAnalysisResponse
from .investigation import assemble_investigation_evidence


# ── Constants ──────────────────────────────────────────────────

CONFIDENCE_MIN = 0.30
CONFIDENCE_MAX = 0.85
AI_TIMEOUT_SECONDS = 45.0


# ── Confidence Post-Processing ─────────────────────────────────


def _clamp_confidence(value: float) -> float:
    """Clamp confidence to [0.30, 0.85]."""
    return max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, round(value, 2)))


def _is_valid_reference(ref: str) -> bool:
    """Check if an evidence reference maps to a known evidence path."""
    # Direct match
    if ref in KNOWN_EVIDENCE_PATHS:
        return True
    # Prefix match (e.g. "event_detection.data.current_pm25" matches "event_detection.data.*")
    for known in KNOWN_EVIDENCE_PATHS:
        if ref.startswith(known.rsplit(".", 1)[0]):
            return True
    return False


def _validate_evidence_references(
    items: list[dict[str, Any]],
    ref_key: str = "supporting_evidence",
) -> list[dict[str, Any]]:
    """Remove invalid evidence references from items."""
    validated = []
    for item in items:
        refs = item.get(ref_key, [])
        valid_refs = [r for r in refs if _is_valid_reference(r)]
        cleaned = {**item, ref_key: valid_refs}
        validated.append(cleaned)
    return validated


def _post_process_result(result: dict[str, Any]) -> dict[str, Any]:
    """Post-process the raw AI output to enforce constraints.

    - Cap all confidence values at 0.85
    - Remove hypotheses with confidence below 0.30
    - Validate evidence references
    - Ensure uncertainties section exists
    - Ensure every recommendation has a rationale
    """
    # Cap confidence on model inferences
    for item in result.get("model_inferences", []):
        if "confidence" in item:
            item["confidence"] = _clamp_confidence(item["confidence"])

    # Filter and cap hypotheses
    hypotheses = result.get("investigation_hypotheses", [])
    filtered_hypotheses = []
    for h in hypotheses:
        conf = h.get("confidence", 0)
        if conf >= CONFIDENCE_MIN:
            h["confidence"] = _clamp_confidence(conf)
            # Ensure evidence references are valid
            refs = h.get("supporting_evidence", [])
            h["supporting_evidence"] = [r for r in refs if _is_valid_reference(r)]
            filtered_hypotheses.append(h)
    result["investigation_hypotheses"] = filtered_hypotheses

    # Cap investigation priority confidence
    priority = result.get("investigation_priority")
    if priority and "confidence" in priority:
        priority["confidence"] = _clamp_confidence(priority["confidence"])

    # Cap exposure direction confidence
    exposure = result.get("likely_exposure_direction")
    if exposure and "confidence" in exposure:
        exposure["confidence"] = _clamp_confidence(exposure["confidence"])

    # Validate evidence references on facts and inferences
    result["observed_facts"] = _validate_evidence_references(
        result.get("observed_facts", []), "evidence_references"
    )
    result["model_inferences"] = _validate_evidence_references(
        result.get("model_inferences", []), "supporting_evidence"
    )

    # Ensure uncertainties section exists
    if not result.get("uncertainties"):
        result["uncertainties"] = [
            "AI analysis produced no explicit uncertainties — manual review recommended"
        ]

    # Ensure every recommendation has rationale
    for action in result.get("recommended_actions", []):
        if not action.get("rationale"):
            action["rationale"] = "Investigation recommended based on available evidence"

    return result


# ── JSON Extraction ────────────────────────────────────────────


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract JSON from the AI response text.

    Handles cases where the AI wraps JSON in markdown code blocks.
    """
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
        r"\{.*\}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                candidate = match.group(1) if match.lastindex else match.group(0)
                return json.loads(candidate)
            except (json.JSONDecodeError, IndexError):
                continue

    return None


# ── AI Provider Call ───────────────────────────────────────────


async def _call_ai_provider(
    system_prompt: str,
    user_message: str,
) -> str | None:
    """Call the configured AI provider and return the response text.

    Uses OpenAI-compatible chat completions API.
    Returns None on any failure (timeout, missing key, etc.).
    """
    settings = get_settings()
    api_key = settings.openai_api_key
    base_url = settings.ai_base_url
    model = settings.ai_model

    if not api_key:
        logger.warning("AI provider API key not configured")
        return None

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        logger.warning("AI provider request timed out")
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning("AI provider returned error", status=exc.response.status_code)
        return None
    except Exception as exc:
        logger.warning("AI provider call failed", error=str(exc))
        return None


# ── Demo Fixture ───────────────────────────────────────────────


DEMO_AI_ANALYSIS: dict[str, Any] = {
    "analysis_status": "complete",
    "event_summary": (
        "An active pollution episode is underway in Lahore with PM2.5 at elevated "
        "levels. Wind is from the East sector with historical directional enrichment "
        "of 1.44x. Weather conditions are compatible with multiple investigation "
        "domains including open burning, traffic emissions, and industrial activity."
    ),
    "severity_assessment": (
        "Episode state with rising trajectory indicates active pollution accumulation. "
        "Historical data shows 90.8% of episodes peak within 6 hours. "
        "Weather conditions (temperature < 18C, moderate humidity) are consistent "
        "with winter episode patterns."
    ),
    "observed_facts": [
        {
            "statement": (
                "PM2.5 levels are in the episode range as determined by the "
                "rule-based episode detection system."
            ),
            "evidence_references": [
                "event_detection.data.state",
                "event_detection.data.current_pm25",
            ],
        },
        {
            "statement": (
                "Wind is currently arriving from the East sector at low speed."
            ),
            "evidence_references": [
                "directional_analysis.current_wind",
                "directional_analysis.historical.strongest_sector",
            ],
        },
        {
            "statement": (
                "The East sector shows 1.44x enrichment with historical pollution "
                "episodes based on 972 episode-hours of evidence."
            ),
            "evidence_references": [
                "directional_analysis.historical.strongest_enrichment",
                "directional_analysis.historical.evidence_count",
            ],
        },
    ],
    "model_inferences": [
        {
            "statement": (
                "The directional enrichment in the East sector represents a "
                "statistical association between wind direction and historical "
                "episode occurrence, not a confirmed source."
            ),
            "confidence": 0.70,
            "supporting_evidence": [
                "directional_analysis.historical.strongest_enrichment",
                "directional_analysis.interpretation",
            ],
        },
        {
            "statement": (
                "Historical analog matching found episodes with similar "
                "meteorological conditions, suggesting a recurring pattern."
            ),
            "confidence": 0.65,
            "supporting_evidence": [
                "historical_analogs.matches",
                "historical_analogs.total_episodes_searched",
            ],
        },
    ],
    "investigation_hypotheses": [
        {
            "factor": "East sector industrial or agricultural emissions",
            "confidence": 0.65,
            "reasoning": (
                "Wind from the East sector with 1.44x historical enrichment "
                "suggests this corridor has higher episode association. "
                "Winter conditions (temperature < 18C, low wind speed) "
                "allow pollutant accumulation."
            ),
            "supporting_evidence": [
                "directional_analysis.historical.strongest_enrichment",
                "directional_analysis.historical.evidence_count",
                "investigation_domains",
            ],
            "verification_needed": (
                "Field inspection of industrial facilities and agricultural "
                "sites in the East corridor. Satellite imagery review for "
                "active burning signatures."
            ),
        },
        {
            "factor": "Traffic emission accumulation under calm conditions",
            "confidence": 0.55,
            "reasoning": (
                "Low wind speed (< 6 m/s) and high humidity (> 70%) create "
                "conditions where vehicle exhaust accumulates rather than disperses."
            ),
            "supporting_evidence": [
                "investigation_domains",
                "weather_context.variables",
            ],
            "verification_needed": (
                "Traffic count data for the episode period. Comparison with "
                "non-episode traffic patterns."
            ),
        },
        {
            "factor": "Regional transport from upwind agricultural burning",
            "confidence": 0.50,
            "reasoning": (
                "Historical episodes show similar meteorological patterns "
                "during the winter burning season. The East sector enrichment "
                "may partially reflect regional agricultural residue transport."
            ),
            "supporting_evidence": [
                "historical_analogs.matches",
                "directional_analysis.historical.season",
            ],
            "verification_needed": (
                "Fire detection satellite data (VIIRS/MODIS) for the broader "
                "region. Cross-reference with Punjab agricultural calendar."
            ),
        },
    ],
    "investigation_priority": {
        "area": "East sector corridor",
        "priority": "HIGH",
        "rationale": (
            "Highest directional enrichment (1.44x) with substantial evidence "
            "(972 episode-hours). Weather conditions favor accumulation."
        ),
        "confidence": 0.70,
    },
    "likely_exposure_direction": {
        "description": (
            "Pollutant exposure likely concentrated in areas downwind of "
            "the East sector, based on current wind direction and historical "
            "enrichment patterns."
        ),
        "confidence": 0.65,
        "limitations": [
            "Directional analysis shows association, not confirmed source",
            "Calm wind conditions may create localized accumulation patterns "
            "not captured by sector-level analysis",
        ],
    },
    "recommended_actions": [
        {
            "priority": 1,
            "action": (
                "Deploy field inspection team to East sector corridor "
                "for visual assessment of industrial and agricultural activity"
            ),
            "rationale": (
                "East sector shows highest historical enrichment with "
                "current wind conditions matching episode pattern"
            ),
            "verification_goal": (
                "Confirm or rule out active emission sources in the corridor"
            ),
        },
        {
            "priority": 2,
            "action": (
                "Request satellite fire detection data (VIIRS/MODIS) "
                "for Lahore and upwind regions"
            ),
            "rationale": (
                "Determine if open burning signatures are present in "
                "the region during this episode"
            ),
            "verification_goal": (
                "Establish whether agricultural or waste burning contributes "
                "to current episode"
            ),
        },
        {
            "priority": 3,
            "action": (
                "Review traffic monitoring data for correlation with "
                "episode timing and location"
            ),
            "rationale": (
                "Traffic emissions domain shows weather-compatible conditions "
                "(calm wind, high humidity)"
            ),
            "verification_goal": (
                "Determine if traffic patterns correlate with episode "
                "intensification periods"
            ),
        },
    ],
    "uncertainties": [
        (
            "The source compass enrichment shows statistical association "
            "between wind direction and episodes, but does not confirm "
            "a specific emission source in the East sector."
        ),
        (
            "Historical analog matching uses meteorological similarity "
            "and does not account for changes in emission sources or "
            "regulatory conditions since the analog episodes occurred."
        ),
        (
            "Data freshness may affect the accuracy of current condition "
            "assessment — check data_quality.freshness_state for current status."
        ),
        (
            "The investigation domains are evaluated against weather triggers "
            "only and do not incorporate real-time emission inventory data."
        ),
    ],
    "data_gaps": [
        (
            "No satellite fire detection data available in the current "
            "evidence package to confirm or rule out open burning."
        ),
        (
            "No real-time traffic volume data to assess traffic emission "
            "contribution during this episode."
        ),
    ],
}


# ── Main Service Function ──────────────────────────────────────


async def analyze_investigation(
    evidence_package: dict[str, Any] | None = None,
    db_path: Path | None = None,
    use_demo: bool = False,
) -> InvestigationAnalysisResponse:
    """Run AI investigation reasoning on the evidence package.

    Flow:
    1. Assemble evidence (or use provided package)
    2. Check if evidence is sufficient for AI analysis
    3. Call AI provider
    4. Parse and validate response
    5. Post-process (confidence caps, reference validation)
    6. Return structured result

    On any AI failure, returns deterministic fallback with
    analysis_status="unavailable".

    Args:
        evidence_package: Pre-assembled evidence dict (optional).
        db_path: Database path (used if evidence_package not provided).
        use_demo: If True, return deterministic demo fixture.

    Returns:
        InvestigationAnalysisResponse with evidence + analysis + metadata.
    """
    now = datetime.now(UTC)

    # ── 1. Assemble evidence ────────────────────────────────────
    if evidence_package is None:
        if db_path is None:
            _settings = get_settings()
            backend_dir = Path(__file__).resolve().parent.parent.parent.parent
            raw_path = _settings.database_url.replace("sqlite:///", "")
            db_path_obj = Path(raw_path)
            if not db_path_obj.is_absolute():
                db_path_obj = backend_dir / db_path_obj
            db_path = db_path_obj
        evidence_package = assemble_investigation_evidence(db_path).to_dict()

    # ── 2. Demo mode ────────────────────────────────────────────
    if use_demo:
        logger.info("Returning demo AI analysis")
        return InvestigationAnalysisResponse(
            evidence=evidence_package,
            analysis=DEMO_AI_ANALYSIS,
            analysis_metadata={
                "mode": "demo",
                "provider": "fixture",
                "generated_at": now.isoformat(),
                "fallback_used": False,
                "demo": True,
            },
        )

    # ── 3. Check evidence sufficiency ───────────────────────────
    event_data = evidence_package.get("event_detection", {}).get("data")
    if not event_data:
        logger.warning("No event detection data — cannot run AI analysis")
        return _build_fallback_response(
            evidence_package,
            reason="No event detection data available for analysis",
        )

    # ── 4. Call AI provider ─────────────────────────────────────
    settings = get_settings()
    if not settings.openai_api_key:
        logger.info("AI API key not configured — using deterministic fallback")
        return _build_fallback_response(
            evidence_package,
            reason="AI provider not configured (LPA_OPENAI_API_KEY missing)",
        )

    user_message = INVESTIGATION_USER_TEMPLATE.format(
        evidence_json=json.dumps(evidence_package, indent=2, default=str)
    )

    raw_response = await _call_ai_provider(INVESTIGATION_SYSTEM_PROMPT, user_message)

    if raw_response is None:
        return _build_fallback_response(
            evidence_package,
            reason="AI provider returned no response (timeout or error)",
        )

    # ── 5. Parse JSON ───────────────────────────────────────────
    parsed = _extract_json(raw_response)
    if parsed is None:
        logger.warning("AI returned invalid JSON")
        return _build_fallback_response(
            evidence_package,
            reason="AI provider returned invalid JSON response",
        )

    # ── 6. Validate schema ──────────────────────────────────────
    try:
        validated = AIInvestigationResult(**parsed)
    except Exception as exc:
        logger.warning("AI response failed schema validation", error=str(exc))
        return _build_fallback_response(
            evidence_package,
            reason=f"AI response failed schema validation: {exc}",
        )

    # ── 7. Post-process ─────────────────────────────────────────
    result_dict = validated.model_dump()
    result_dict = _post_process_result(result_dict)

    logger.info(
        "AI investigation analysis complete",
        status=result_dict.get("analysis_status"),
        hypotheses=len(result_dict.get("investigation_hypotheses", [])),
        uncertainties=len(result_dict.get("uncertainties", [])),
    )

    return InvestigationAnalysisResponse(
        evidence=evidence_package,
        analysis=result_dict,
        analysis_metadata={
            "mode": "ai",
            "provider": settings.ai_provider,
            "model": settings.ai_model,
            "generated_at": now.isoformat(),
            "fallback_used": False,
        },
    )


# ── Fallback Builder ───────────────────────────────────────────


def _build_fallback_response(
    evidence_package: dict[str, Any],
    reason: str = "AI provider unavailable",
) -> InvestigationAnalysisResponse:
    """Build a deterministic fallback response when AI is unavailable."""
    now = datetime.now(UTC)
    fallback_analysis = {
        "analysis_status": "unavailable",
        "event_summary": (
            f"AI reasoning is currently unavailable ({reason}). "
            "Showing deterministic investigation evidence."
        ),
        "severity_assessment": "",
        "observed_facts": [],
        "model_inferences": [],
        "investigation_hypotheses": [],
        "investigation_priority": None,
        "likely_exposure_direction": None,
        "recommended_actions": [],
        "uncertainties": [
            "AI investigation reasoning was unavailable for this request.",
            reason,
            "Review the deterministic evidence package for manual analysis.",
        ],
        "data_gaps": [],
    }

    return InvestigationAnalysisResponse(
        evidence=evidence_package,
        analysis=fallback_analysis,
        analysis_metadata={
            "mode": "deterministic_fallback",
            "provider": None,
            "generated_at": now.isoformat(),
            "fallback_used": True,
            "fallback_reason": reason,
        },
    )
