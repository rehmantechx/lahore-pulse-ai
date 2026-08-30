"""Source Compass — Directional pollution-association analysis.

Provides wind-direction-to-episode enrichment analysis using
historical PM2.5 data and wind direction observations.

Direction model: 8 meteorological sectors (N, NE, E, SE, S, SW, W, NW).

CRITICAL CLAIMS:
- This shows STATISTICAL ASSOCIATION between wind direction and episodes
- It does NOT identify pollution sources
- It does NOT imply causation
- It is an investigation HINT, not source confirmation

Seasonal framing:
- Historical enrichment uses winter (Oct-Mar) data only
- 96% of episodes occur in winter
- Non-winter enrichment is unreliable (too few episodes)
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger


# ── Constants ──────────────────────────────────────────────────

SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Enrichment thresholds (from Phase 2 hostile validation)
ENRICHMENT_HIGH = 1.30      # >= 1.30x = HIGH ASSOCIATION
ENRICHMENT_MODERATE = 1.10  # >= 1.10x = MODERATE ASSOCIATION
ENRICHMENT_MIN_SAMPLE = 50  # minimum episode-hours per sector for valid enrichment

# Winter months for seasonal framing (Oct-Mar)
WINTER_MONTHS = {10, 11, 12, 1, 2, 3}

# Calm wind threshold (m/s) — below this, direction is meaningless
CALM_WIND_THRESHOLD_MS = 1.5


# ── Sector Geometry ────────────────────────────────────────────


def deg_to_sector(degrees: float) -> str:
    """Convert wind direction (meteorological FROM-degrees) to 8-bin sector.

    Meteorological convention: degrees indicate where the wind is COMING FROM.
    0° = N, 90° = E, 180° = S, 270° = W.

    Each sector spans 45°, centered on the cardinal direction.
    """
    idx = int((degrees + 22.5) / 45.0) % 8
    return SECTORS[idx]


def sector_midpoint(sector: str) -> float:
    """Return the midpoint bearing (degrees) of a sector."""
    midpoints = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
    return midpoints[sector]


def sector_arrow(sector: str) -> str:
    """Return a Unicode arrow character for a sector."""
    arrows = {"N": "↓", "NE": "↙", "E": "←", "SE": "↖", "S": "↑", "SW": "↗", "W": "→", "NW": "↘"}
    return arrows.get(sector, "?")


def sector_range(sector: str) -> tuple[float, float]:
    """Return (lower, upper) degree range for a sector."""
    idx = SECTORS.index(sector)
    center = idx * 45.0
    lower = (center - 22.5) % 360
    upper = (center + 22.5) % 360
    return lower, upper


# ── Data structures ────────────────────────────────────────────


@dataclass
class SectorAnalysis:
    """Analysis result for a single sector."""
    sector: str
    total_hours: int
    episode_hours: int
    enrichment: float  # ratio of P(episode|sector) to P(episode overall)
    avg_pm25: float
    avg_wind_speed: float | None


@dataclass
class SourceCompassResult:
    """Complete Source Compass analysis result."""
    # Current wind
    current_direction_degrees: float | None
    current_sector: str | None
    current_wind_speed_ms: float | None

    # Historical enrichment
    enrichment_profile: list[SectorAnalysis]
    strongest_sector: str
    strongest_enrichment: float
    association_label: str  # HIGH ASSOCIATION / MODERATE / LOW / INSUFFICIENT

    # Evidence
    evidence_count: int  # episode-hours in strongest sector
    total_episode_hours: int
    total_observations: int

    # Seasonal context
    season: str  # "winter" or "non-winter"
    season_month_count: int

    # Safety
    is_calm: bool
    disclaimer: str

    # Investigation corridor (for Response Orchestrator integration)
    investigation_hint: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "current_wind": {
                "direction_degrees": (
                    round(self.current_direction_degrees, 1)
                    if self.current_direction_degrees is not None
                    else None
                ),
                "sector": self.current_sector,
                "wind_speed_ms": (
                    round(self.current_wind_speed_ms, 1)
                    if self.current_wind_speed_ms is not None
                    else None
                ),
                "is_calm": self.is_calm,
            },
            "historical": {
                "profile": [
                    {
                        "sector": s.sector,
                        "enrichment": round(s.enrichment, 2),
                        "episode_hours": s.episode_hours,
                        "total_hours": s.total_hours,
                        "avg_pm25": round(s.avg_pm25, 1),
                    }
                    for s in self.enrichment_profile
                ],
                "strongest_sector": self.strongest_sector,
                "strongest_enrichment": round(self.strongest_enrichment, 2),
                "association_label": self.association_label,
                "evidence_count": self.evidence_count,
                "total_episode_hours": self.total_episode_hours,
                "total_observations": self.total_observations,
                "season": self.season,
                "season_month_count": self.season_month_count,
            },
            "investigation_hint": self.investigation_hint,
            "disclaimer": self.disclaimer,
        }


# ── Database helpers ───────────────────────────────────────────


def _get_read_connection(db_path: Path) -> sqlite3.Connection:
    """Open a read-optimized SQLite connection."""
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-16000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def _fetch_wind_data(db_path: Path) -> list[dict]:
    """Fetch all wind_direction_10m observations from the database.

    Returns list of {observed_at, value, wind_speed} dicts.
    """
    sql = """
        SELECT d.observed_at, d.value,
               s.value AS wind_speed
        FROM observations d
        LEFT JOIN observations s
          ON s.parameter = 'wind_speed_10m'
          AND s.observation_type = 'observation'
          AND s.observed_at = d.observed_at
        WHERE d.parameter = 'wind_direction_10m'
          AND d.observation_type = 'observation'
        ORDER BY d.observed_at ASC
    """
    conn = _get_read_connection(db_path)
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    result = []
    for observed_at, direction, wind_speed in rows:
        result.append({
            "observed_at": observed_at,
            "direction": direction,
            "wind_speed": wind_speed,
        })
    return result


def _fetch_pm25_timeseries(db_path: Path) -> list[dict]:
    """Fetch all pm2_5 observations for episode determination."""
    sql = """
        SELECT observed_at, value
        FROM observations
        WHERE parameter = 'pm2_5'
          AND observation_type = 'observation'
        ORDER BY observed_at ASC
    """
    conn = _get_read_connection(db_path)
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    return [{"observed_at": r[0], "value": r[1]} for r in rows]


def _fetch_current_conditions(db_path: Path) -> dict:
    """Fetch the most recent wind direction and speed."""
    sql = """
        SELECT parameter, value, observed_at
        FROM observations
        WHERE parameter IN ('wind_direction_10m', 'wind_speed_10m')
          AND observation_type = 'observation'
        ORDER BY observed_at DESC
    """
    conn = _get_read_connection(db_path)
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    result: dict[str, float | str | None] = {
        "wind_direction_10m": None,
        "wind_speed_10m": None,
        "observed_at": None,
    }
    seen = set()
    for param, value, ts in rows:
        if param not in seen:
            result[param] = value
            if result["observed_at"] is None:
                result["observed_at"] = ts
            seen.add(param)
    return result


# ── Core analysis ──────────────────────────────────────────────


def _is_episode_hour(pm25: float, recent_above_threshold: int) -> bool:
    """Determine if an hour is part of an episode.

    Simplified episode detection for directional analysis:
    PM2.5 > 120 (the validated episode threshold).
    """
    return pm25 > 120.0


def _compute_enrichment(
    wind_data: list[dict],
    pm25_data: list[dict],
    winter_only: bool = True,
) -> tuple[list[SectorAnalysis], str, int]:
    """Compute directional enrichment for episodes.

    Returns enrichment profile, season label, and season month count.
    """
    # Build PM2.5 lookup by hour
    pm25_by_hour: dict[str, float] = {}
    for obs in pm25_data:
        ts = obs["observed_at"].replace("+00:00", "").replace("Z", "")
        pm25_by_hour[ts] = obs["value"]

    # Join wind with PM2.5
    joined: list[dict] = []
    for w in wind_data:
        ts_key = w["observed_at"].replace("+00:00", "").replace("Z", "")
        pm25 = pm25_by_hour.get(ts_key)
        if pm25 is not None:
            try:
                dt = datetime.fromisoformat(ts_key.replace("+00:00", ""))
                month = dt.month
            except (ValueError, TypeError):
                month = None
            joined.append({
                "ts": ts_key,
                "pm25": pm25,
                "direction": w["direction"],
                "wind_speed": w["wind_speed"],
                "month": month,
                "is_episode": _is_episode_hour(pm25, 0),
            })

    if not joined:
        return [], "unknown", 0

    # Apply seasonal filter
    if winter_only:
        filtered = [j for j in joined if j["month"] in WINTER_MONTHS]
        season = "winter"
    else:
        filtered = [j for j in joined if j["month"] not in WINTER_MONTHS]
        season = "non-winter"

    season_count = len(set(j["month"] for j in filtered if j["month"] is not None))

    if not filtered:
        return [], season, season_count

    # Compute per-sector stats
    total = len(filtered)
    total_episodes = sum(1 for j in filtered if j["is_episode"])
    overall_rate = total_episodes / total if total > 0 else 0

    sector_stats: dict[str, dict] = {}
    for s in SECTORS:
        sector_stats[s] = {"count": 0, "episodes": 0, "pm25_sum": 0.0, "wind_speed_sum": 0.0, "wind_count": 0}

    for j in filtered:
        sector = deg_to_sector(j["direction"])
        sector_stats[sector]["count"] += 1
        sector_stats[sector]["pm25_sum"] += j["pm25"]
        if j["is_episode"]:
            sector_stats[sector]["episodes"] += 1
        if j["wind_speed"] is not None:
            sector_stats[sector]["wind_speed_sum"] += j["wind_speed"]
            sector_stats[sector]["wind_count"] += 1

    profile: list[SectorAnalysis] = []
    for s in SECTORS:
        stats = sector_stats[s]
        rate = stats["episodes"] / stats["count"] if stats["count"] > 0 else 0
        enrichment = rate / overall_rate if overall_rate > 0 else 0
        avg_pm = stats["pm25_sum"] / stats["count"] if stats["count"] > 0 else 0
        avg_ws = stats["wind_speed_sum"] / stats["wind_count"] if stats["wind_count"] > 0 else None
        profile.append(SectorAnalysis(
            sector=s,
            total_hours=stats["count"],
            episode_hours=stats["episodes"],
            enrichment=enrichment,
            avg_pm25=avg_pm,
            avg_wind_speed=avg_ws,
        ))

    return profile, season, season_count


def _label_association(enrichment: float, evidence: int) -> str:
    """Convert enrichment ratio + sample size to a user-facing label."""
    if evidence < ENRICHMENT_MIN_SAMPLE:
        return "INSUFFICIENT DATA"
    if enrichment >= ENRICHMENT_HIGH:
        return "HIGH ASSOCIATION"
    if enrichment >= ENRICHMENT_MODERATE:
        return "MODERATE ASSOCIATION"
    return "LOW ASSOCIATION"


def _build_investigation_hint(
    strongest_sector: str,
    association_label: str,
    evidence_count: int,
    is_episode: bool,
) -> dict[str, Any] | None:
    """Build investigation corridor hint for Response Orchestrator integration."""
    if association_label == "INSUFFICIENT DATA":
        return None

    domains = ["Open burning", "Traffic", "Industrial activity", "Construction dust"]

    return {
        "corridor_sectors": [strongest_sector],
        "corridor_label": f"{strongest_sector} sector",
        "association_label": association_label,
        "evidence_count": evidence_count,
        "suggested_domains": domains,
        "message": (
            f"Wind arriving from the {strongest_sector} sector shows "
            f"{association_label.lower()} with historical pollution episodes "
            f"({evidence_count:,} episode-hours). "
            f"Suggested investigation domains: {', '.join(domains)}."
        ),
    }


# ── Main entry point ───────────────────────────────────────────


def compute_source_compass(db_path: Path) -> SourceCompassResult:
    """Compute the full Source Compass analysis.

    Reads wind direction, wind speed, and PM2.5 data from the database,
    computes seasonal enrichment, and returns the complete compass result.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        SourceCompassResult with all analysis data.
    """
    logger.info("Computing Source Compass", db_path=str(db_path))

    # 1. Fetch data
    wind_data = _fetch_wind_data(db_path)
    pm25_data = _fetch_pm25_timeseries(db_path)
    current = _fetch_current_conditions(db_path)

    logger.info(
        "Source Compass data loaded",
        wind_hours=len(wind_data),
        pm25_hours=len(pm25_data),
    )

    # 2. Handle missing data
    if not wind_data:
        return SourceCompassResult(
            current_direction_degrees=None,
            current_sector=None,
            current_wind_speed_ms=None,
            enrichment_profile=[],
            strongest_sector="N",
            strongest_enrichment=0.0,
            association_label="INSUFFICIENT DATA",
            evidence_count=0,
            total_episode_hours=0,
            total_observations=0,
            season="unknown",
            season_month_count=0,
            is_calm=True,
            disclaimer="Wind direction data not yet available. The unit fix must be applied and data re-collected before Source Compass can function.",
        )

    # 3. Compute enrichment (winter-only by default)
    profile, season, season_count = _compute_enrichment(wind_data, pm25_data, winter_only=True)

    # 4. Find strongest sector
    if profile:
        strongest = max(profile, key=lambda p: p.enrichment)
    else:
        strongest = SectorAnalysis(sector="N", total_hours=0, episode_hours=0, enrichment=0, avg_pm25=0, avg_wind_speed=None)

    # 5. Label association
    association_label = _label_association(strongest.enrichment, strongest.episode_hours)

    # 6. Current conditions
    current_dir = current.get("wind_direction_10m")
    current_speed = current.get("wind_speed_10m")
    current_sector = deg_to_sector(current_dir) if current_dir is not None else None
    is_calm = current_speed is not None and current_speed < CALM_WIND_THRESHOLD_MS

    # 7. Count total observations
    total_obs = len(wind_data)

    # 8. Determine if currently in episode (from the latest PM2.5)
    current_pm25 = pm25_data[-1]["value"] if pm25_data else None
    is_episode = current_pm25 is not None and current_pm25 > 120.0

    # 9. Build investigation hint
    investigation_hint = _build_investigation_hint(
        strongest_sector=strongest.sector,
        association_label=association_label,
        evidence_count=strongest.episode_hours,
        is_episode=is_episode,
    )

    # 10. Disclaimer
    disclaimer = (
        "Directional evidence shows statistical association between wind direction "
        "and historical pollution episodes. It does NOT confirm a pollution source. "
        "Use as an investigation hint for narrowing geographic focus."
    )

    result = SourceCompassResult(
        current_direction_degrees=current_dir,
        current_sector=current_sector,
        current_wind_speed_ms=current_speed,
        enrichment_profile=profile,
        strongest_sector=strongest.sector,
        strongest_enrichment=strongest.enrichment,
        association_label=association_label,
        evidence_count=strongest.episode_hours,
        total_episode_hours=sum(p.episode_hours for p in profile),
        total_observations=total_obs,
        season=season,
        season_month_count=season_count,
        is_calm=is_calm,
        disclaimer=disclaimer,
        investigation_hint=investigation_hint,
    )

    logger.info(
        "Source Compass computed",
        current_sector=current_sector,
        strongest_sector=strongest.sector,
        enrichment=round(strongest.enrichment, 2),
        association=association_label,
    )

    return result
