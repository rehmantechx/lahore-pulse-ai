"""Investigation Evidence Assembler — structured evidence packages.

Assembles all available data sources into a structured evidence
package for a pollution event investigation.  This is NOT a decision
engine — it collects OBSERVED FACTS, MODEL INFERENCES, and
HYPOTHESES with explicit epistemic labels.

Design:
    - Each data source is optional and independently failure-isolated
    - Partial results are returned when any source fails
    - Every field carries an `evidence_type` tag:
        OBSERVED  — directly measured, highest confidence
        INFERRED  — derived from model or statistical analysis
        HYPOTHESIS — domain-informed guess, lowest confidence
    - No AI reasoning layer — this is pure data assembly
    - Graceful degradation: endpoint never fails completely

Investigation domains are evaluated against weather triggers
(Punjab environmental response framework) and carry an
`evaluated` flag indicating whether weather conditions match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .episode import compute_episode_intelligence
from .freshness import FreshnessState, assess_freshness
from .historical_analog import find_analogs, AnalogResponse
from .source_compass import compute_source_compass


# ── Evidence Type Constants ─────────────────────────────────────


class EvidenceType:
    """Epistemic labels for evidence fields."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    HYPOTHESIS = "hypothesis"


# ── Investigation Domains ──────────────────────────────────────

# Port of frontend responseDomains.js to Python for server-side evaluation.
# Each domain has weather trigger functions that mirror the JS logic.

INVESTIGATION_DOMAINS: list[dict[str, Any]] = [
    {
        "id": "open-burning",
        "icon": "🔥",
        "name": "Open Burning",
        "description": "Agricultural residue, waste burning, or biomass combustion",
        "legal_basis": (
            "Punjab EPA: Open burning ban under Punjab Environmental "
            "Protection Act; smog emergency orders target crop residue burning"
        ),
        "triggers": {
            "temperature": lambda v: v is not None and v < 18.0,
            "humidity": lambda v: v is not None and v < 60.0,
            "wind_speed": lambda v: v is not None and v < 6.0,
        },
    },
    {
        "id": "traffic-emissions",
        "icon": "🚗",
        "name": "Traffic Emissions",
        "description": "Vehicle exhaust and transport-related particulate accumulation",
        "legal_basis": (
            "Punjab Transport Department: vehicle emission standards; "
            "Lahore Traffic Engineering & Planning Agency traffic management during smog"
        ),
        "triggers": {
            "wind_speed": lambda v: v is not None and v < 6.0,
            "humidity": lambda v: v is not None and v > 70.0,
        },
    },
    {
        "id": "road-dust",
        "icon": "🏗",
        "name": "Road / Construction Dust",
        "description": "Suspension of particulates from road surface and construction activity",
        "legal_basis": (
            "Punjab EPA: Construction activity restrictions during smog season; "
            "Lahore Development Authority dust suppression orders"
        ),
        "triggers": {
            "humidity": lambda v: v is not None and v < 60.0,
            "wind_speed": lambda v: v is not None and v > 4.0,
        },
    },
    {
        "id": "industrial",
        "icon": "🏭",
        "name": "Industrial Emissions",
        "description": "Factory, brick kiln, and industrial process emissions",
        "legal_basis": (
            "Punjab EPA: Brick kiln conversion order; industrial emission "
            "standards under Punjab Environmental Protection Act 1997"
        ),
        "triggers": {
            "pressure": lambda v: v is not None and v > 1010.0,
            "wind_speed": lambda v: v is not None and v < 6.0,
        },
    },
]


# ── Data Structures ────────────────────────────────────────────


@dataclass
class DomainEvaluation:
    """Result of evaluating one investigation domain against weather."""

    id: str
    name: str
    icon: str
    description: str
    legal_basis: str
    triggers_evaluated: int
    triggers_matched: int
    conditions_met: bool  # True if >= half the triggers match
    evidence_type: str  # always HYPOTHESIS (domain hints are not facts)
    caveat: str = "Weather-based domain screening — not source confirmation"


@dataclass
class DataQualityReport:
    """Data quality and freshness for the investigation package."""

    freshness_state: str
    freshness_hours: float | None
    latest_observation_at: str | None
    parameters_available: int
    data_limitations: list[str] = field(default_factory=list)
    evidence_type: str = EvidenceType.OBSERVED


@dataclass
class InvestigationEvidencePackage:
    """Complete evidence package for a pollution event investigation.

    Assembles data from multiple existing services into a structured
    package that can drive downstream AI reasoning or frontend display.
    """

    # Metadata
    assembled_at: str = ""
    assembly_version: str = "1.0.0"

    # Event Detection (from episode intelligence)
    event_detection: dict[str, Any] = field(default_factory=dict)

    # Weather Context (from episode weather variables)
    weather_context: dict[str, Any] = field(default_factory=dict)

    # Directional Analysis (from source compass)
    directional_analysis: dict[str, Any] | None = None

    # Investigation Domains (weather-trigger evaluated)
    investigation_domains: list[dict[str, Any]] = field(default_factory=list)

    # Historical Analog (from analog engine)
    historical_analogs: dict[str, Any] | None = None

    # Geographic Context (extensible, initially empty)
    geographic_context: dict[str, Any] = field(default_factory=dict)

    # Data Quality
    data_quality: dict[str, Any] = field(default_factory=dict)

    # System Limitations
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "metadata": {
                "assembled_at": self.assembled_at,
                "assembly_version": self.assembly_version,
            },
            "event_detection": self.event_detection,
            "weather_context": self.weather_context,
            "directional_analysis": self.directional_analysis,
            "investigation_domains": self.investigation_domains,
            "historical_analogs": self.historical_analogs,
            "geographic_context": self.geographic_context,
            "data_quality": self.data_quality,
            "limitations": self.limitations,
        }


# ── Domain Evaluation Logic ────────────────────────────────────


def _evaluate_domain(
    domain: dict[str, Any],
    weather_vars: list[dict[str, Any]],
) -> DomainEvaluation:
    """Evaluate a single investigation domain against current weather.

    Mirrors the frontend evaluateDomain() logic from responseDomains.js.
    """
    # Build a lookup of weather variable values by label
    var_map: dict[str, float | None] = {}
    for v in weather_vars:
        label = v.get("label", "").lower()
        value = v.get("current_value")
        if "temperature" in label:
            var_map["temperature"] = value
        elif "humidity" in label:
            var_map["humidity"] = value
        elif "wind" in label and "speed" in label:
            var_map["wind_speed"] = value
        elif "pressure" in label:
            var_map["pressure"] = value

    matched = 0
    total = 0
    for param_name, trigger_fn in domain["triggers"].items():
        total += 1
        val = var_map.get(param_name)
        if val is not None and trigger_fn(val):
            matched += 1

    return DomainEvaluation(
        id=domain["id"],
        name=domain["name"],
        icon=domain["icon"],
        description=domain["description"],
        legal_basis=domain["legal_basis"],
        triggers_evaluated=total,
        triggers_matched=matched,
        conditions_met=matched >= max(1, total // 2),
        evidence_type=EvidenceType.HYPOTHESIS,
    )


def _evaluate_all_domains(
    weather_vars: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate all investigation domains and return serializable results."""
    results = []
    for domain in INVESTIGATION_DOMAINS:
        evaluation = _evaluate_domain(domain, weather_vars)
        results.append({
            "id": evaluation.id,
            "name": evaluation.name,
            "icon": evaluation.icon,
            "description": evaluation.description,
            "legal_basis": evaluation.legal_basis,
            "triggers_evaluated": evaluation.triggers_evaluated,
            "triggers_matched": evaluation.triggers_matched,
            "conditions_met": evaluation.conditions_met,
            "evidence_type": evaluation.evidence_type,
            "caveat": evaluation.caveat,
        })
    return results


# ── Geographic Context (extensible stub) ───────────────────────


def _build_geographic_context(
    compass_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build geographic context from available data.

    Initially returns a minimal structure with the grid point
    and directional corridor hint. Designed to be extended with
    satellite imagery, terrain data, and point-of-interest data
    in future phases.
    """
    context: dict[str, Any] = {
        "grid_point": {"lat": 31.5204, "lon": 74.3587},
        "scope": "Lahore metropolitan area",
    }

    if compass_data and compass_data.get("investigation_hint"):
        hint = compass_data["investigation_hint"]
        context["suggested_search_corridor"] = {
            "sectors": hint.get("corridor_sectors", []),
            "label": hint.get("corridor_label", ""),
        }

    return context


# ── Core Assembly Function ─────────────────────────────────────


def assemble_investigation_evidence(
    db_path: Path,
) -> InvestigationEvidencePackage:
    """Assemble the full investigation evidence package.

    Each data source is independently failure-isolated.  If any
    source fails, the package is returned with partial data and
    a limitation note explaining what is missing.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        InvestigationEvidencePackage with all available evidence.
    """
    logger.info("Assembling investigation evidence package")
    now = datetime.now(UTC)
    limitations: list[str] = []

    # ── 1. Data Quality / Freshness ──────────────────────────────
    freshness_result = None
    try:
        freshness_result = assess_freshness(db_path)
    except Exception as exc:
        logger.warning("Freshness assessment failed", error=str(exc))
        limitations.append(f"Data freshness unavailable: {exc}")

    data_quality = {
        "evidence_type": EvidenceType.OBSERVED,
        "freshness_state": (
            freshness_result.state.value
            if freshness_result
            else FreshnessState.UNAVAILABLE.value
        ),
        "freshness_hours": (
            round(freshness_result.freshness_hours, 2)
            if freshness_result and freshness_result.freshness_hours != float("inf")
            else None
        ),
        "latest_observation_at": (
            freshness_result.latest_observation_at
            if freshness_result
            else None
        ),
        "parameters_available": (
            freshness_result.parameters_available
            if freshness_result
            else 0
        ),
        "data_limitations": limitations[:],
    }

    # Derive freshness_hours for downstream services
    freshness_hours: float | None = None
    if freshness_result and freshness_result.freshness_hours != float("inf"):
        freshness_hours = freshness_result.freshness_hours

    # ── 2. Event Detection (Episode Intelligence) ────────────────
    event_detection: dict[str, Any] = {
        "evidence_type": EvidenceType.OBSERVED,
        "data": None,
        "error": None,
    }
    weather_vars: list[dict[str, Any]] = []

    try:
        episode_result = compute_episode_intelligence(
            db_path=db_path,
            forecasts={},  # No forecasts in evidence assembly
            freshness_hours=freshness_hours,
            freshness_state=(
                freshness_result.state.value
                if freshness_result
                else FreshnessState.UNAVAILABLE.value
            ),
        )
        episode_dict = episode_result.to_dict()
        event_detection["data"] = episode_dict

        # Extract weather variables for domain evaluation
        weather_ctx = episode_dict.get("weather_context", {})
        weather_vars = weather_ctx.get("variables", [])

    except Exception as exc:
        logger.warning("Episode intelligence failed", error=str(exc))
        event_detection["error"] = str(exc)
        limitations.append(f"Event detection unavailable: {exc}")

    # ── 3. Weather Context ───────────────────────────────────────
    weather_context: dict[str, Any] = {
        "evidence_type": EvidenceType.OBSERVED,
        "variables": weather_vars,
    }

    # ── 4. Directional Analysis (Source Compass) ─────────────────
    directional_analysis: dict[str, Any] | None = None
    try:
        compass_result = compute_source_compass(db_path)
        compass_dict = compass_result.to_dict()

        # Add explicit interpretation metadata
        compass_dict["interpretation"] = {
            "claim": (
                "Statistical association between wind direction and "
                "historical pollution episodes. NOT source attribution."
            ),
            "evidence_type": EvidenceType.INFERRED,
            "method": "Directional enrichment analysis (8-sector, winter-only)",
            "season": compass_dict.get("historical", {}).get("season", "unknown"),
            "data_basis": (
                f"{compass_dict.get('historical', {}).get('total_observations', 0)} "
                "wind direction observations"
            ),
        }

        directional_analysis = compass_dict

    except Exception as exc:
        logger.warning("Source Compass failed", error=str(exc))
        limitations.append(f"Directional analysis unavailable: {exc}")

    # ── 5. Investigation Domains ─────────────────────────────────
    investigation_domains: list[dict[str, Any]] = []
    if weather_vars:
        try:
            investigation_domains = _evaluate_all_domains(weather_vars)
        except Exception as exc:
            logger.warning("Domain evaluation failed", error=str(exc))
            limitations.append(f"Domain evaluation unavailable: {exc}")
    else:
        limitations.append(
            "Domain evaluation skipped: no weather variables available"
        )

    # ── 6. Historical Analogs ────────────────────────────────────
    historical_analogs: dict[str, Any] | None = None
    try:
        analog_result: AnalogResponse = find_analogs(db_path, limit=3)
        analogs_list = []
        for analog in analog_result.analogs[:3]:
            analogs_list.append({
                "date": analog.date,
                "peak_pm25": round(analog.peak_pm25, 1),
                "duration_hours": analog.duration_hours,
                "distance": round(analog.distance, 3),
                "similarity_label": analog.similarity_label,
                "replay_window": {
                    "start": analog.replay_start,
                    "end": analog.replay_end,
                },
                "evidence_type": EvidenceType.INFERRED,
                "caveat": (
                    "Statistical similarity only — does NOT imply "
                    "identical causes or identical outcomes"
                ),
            })

        historical_analogs = {
            "evidence_type": EvidenceType.INFERRED,
            "matches": analogs_list,
            "total_episodes_searched": analog_result.total_episodes_searched,
            "caveat": analog_result.caveat or (
                "Analog matching uses normalized Euclidean distance "
                "across meteorological features. Similar conditions "
                "do not guarantee identical causes."
            ),
        }

    except Exception as exc:
        logger.warning("Historical analog search failed", error=str(exc))
        limitations.append(f"Historical analogs unavailable: {exc}")

    # ── 7. Geographic Context ────────────────────────────────────
    geographic_context = _build_geographic_context(directional_analysis)

    # ── 8. Assemble Final Package ────────────────────────────────
    package = InvestigationEvidencePackage(
        assembled_at=now.isoformat(),
        assembly_version="1.0.0",
        event_detection=event_detection,
        weather_context=weather_context,
        directional_analysis=directional_analysis,
        investigation_domains=investigation_domains,
        historical_analogs=historical_analogs,
        geographic_context=geographic_context,
        data_quality=data_quality,
        limitations=limitations,
    )

    logger.info(
        "Investigation evidence assembled",
        limitations=len(limitations),
        domains_evaluated=len(investigation_domains),
        has_compass=directional_analysis is not None,
        has_analogs=historical_analogs is not None,
    )

    return package
