"""Historical Analog Engine — find episodes similar to current conditions.

Provides deterministic, explainable similarity matching across
available meteorological dimensions. No ML model. No black-box.
Normalized Euclidean distance with qualitative match labels.

CRITICAL CLAIMS:
- Shows STATISTICAL SIMILARITY between current and historical episodes
- Does NOT imply identical causes
- Does NOT predict what will happen next
- Shows what happened AFTER similar historical episodes (observed data)
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .episode import (
    _get_read_connection,
    _fetch_weather_at,
    EPISODE_PM25_THRESHOLD,
    get_current_season,
)
from .source_compass import deg_to_sector, SECTORS


# ── Constants ──────────────────────────────────────────────────────

# Feature weights — higher = more influence on similarity
FEATURE_WEIGHTS = {
    "peak_pm25": 1.0,
    "temperature": 0.8,
    "humidity": 0.8,
    "wind_speed": 0.6,
    "wind_direction": 0.5,
    "pressure": 0.4,
    "month": 0.7,
}

# Normalization ranges (observed min/max from database audit)
NORMALIZATION_RANGES = {
    "peak_pm25": (0, 400.0),
    "temperature": (-5.0, 50.0),
    "humidity": (0.0, 100.0),
    "wind_speed": (0.0, 45.0),
    "wind_direction": (0.0, 360.0),
    "pressure": (985.0, 1030.0),
    "month": (1.0, 12.0),
}

# Match labels
MATCH_CLOSEST = "Closest match"
MATCH_STRONG = "Strong match"
MATCH_MODERATE = "Moderate match"
MATCH_WEAK = "Weak match"

# Thresholds for match labels (on normalized distance)
DISTANCE_CLOSEST = 0.25
DISTANCE_STRONG = 0.40
DISTANCE_MODERATE = 0.55


# ── Data Structures ────────────────────────────────────────────────


@dataclass
class EpisodeFeatures:
    """Feature vector for a single historical episode."""

    date: str
    peak_pm25: float
    avg_pm25: float
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: float
    pressure: float
    month: int
    hours: int  # reading count (proxy for duration)


@dataclass
class SimilarityFactor:
    """One dimension of similarity or difference."""

    dimension: str
    current_value: float | None
    historical_value: float
    matches: bool
    label: str
    unit: str


@dataclass
class AnalogResult:
    """One historical analog episode."""

    date: str
    peak_pm25: float
    avg_pm25: float
    duration_hours: int
    distance: float  # raw normalized distance
    similarity_label: str
    similarity_factors: list[SimilarityFactor]
    what_happened_next: dict[str, Any]
    replay_start: str
    replay_end: str


@dataclass
class AnalogResponse:
    """Complete analog engine response."""

    current_context: dict[str, Any]
    analogs: list[AnalogResult]
    total_episodes_searched: int
    caveat: str = ""


# ── Normalization ──────────────────────────────────────────────────


def _normalize(value: float, feature: str) -> float:
    """Normalize a feature value to [0, 1] range."""
    low, high = NORMALIZATION_RANGES[feature]
    if high == low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _circular_distance(a: float, b: float) -> float:
    """Angular distance between two directions in degrees [0, 360].

    Returns value in [0, 1] where 0 = same direction, 1 = opposite.
    """
    diff = abs(a - b) % 360
    if diff > 180:
        diff = 360 - diff
    return diff / 180.0


# ── Feature Extraction ─────────────────────────────────────────────


def _fetch_all_episode_features(db_path: Path) -> list[EpisodeFeatures]:
    """Fetch feature vectors for all historical episodes.

    Uses the same episode definition as the replay API:
    peak PM2.5 >= 120 on any calendar day.

    Two-phase query for performance:
    1. Find episode dates via pm2_5 index only (fast)
    2. Fetch weather features for those dates only (targeted)
    """
    conn = _get_read_connection(db_path)
    try:
        # Phase 1: Find episode dates using indexed pm2_5 scan
        date_rows = conn.execute(
            """
            SELECT DATE(observed_at) as date,
                   ROUND(MAX(value), 1) as peak_pm25,
                   ROUND(AVG(value), 1) as avg_pm25
            FROM observations
            WHERE parameter = 'pm2_5'
              AND observation_type = 'observation'
            GROUP BY DATE(observed_at)
            HAVING peak_pm25 >= ?
            ORDER BY date ASC
            """,
            [EPISODE_PM25_THRESHOLD],
        ).fetchall()

        if not date_rows:
            return []

        # Phase 2: Fetch weather + month for each episode date (targeted)
        # Use a single query with IN clause for all dates
        dates = [r[0] for r in date_rows]
        placeholders = ",".join("?" * len(dates))

        weather_rows = conn.execute(
            f"""
            SELECT
                DATE(observed_at) as date,
                ROUND(AVG(CASE WHEN parameter='temperature_2m' THEN value END), 1) as temp,
                ROUND(AVG(CASE WHEN parameter='relative_humidity_2m' THEN value END), 1) as humid,
                ROUND(AVG(CASE WHEN parameter='wind_speed_10m' THEN value END), 1) as wind_speed,
                ROUND(AVG(CASE WHEN parameter='wind_direction_10m' THEN value END), 1) as wind_dir,
                ROUND(AVG(CASE WHEN parameter='pressure_msl' THEN value END), 1) as pressure,
                CAST(strftime('%m', observed_at) AS INTEGER) as month,
                COUNT(DISTINCT CAST(strftime('%H', observed_at) AS INTEGER)) as hours
            FROM observations
            WHERE observation_type = 'observation'
              AND parameter IN ('temperature_2m', 'relative_humidity_2m', 'wind_speed_10m',
                                'wind_direction_10m', 'pressure_msl')
              AND DATE(observed_at) IN ({placeholders})
            GROUP BY DATE(observed_at)
            """,
            dates,
        ).fetchall()

        # Index weather rows by date for fast lookup
        weather_by_date = {r[0]: r for r in weather_rows}

        episodes = []
        for date, peak, avg in date_rows:
            wr = weather_by_date.get(date)
            if wr and wr[1] is not None and wr[2] is not None and wr[4] is not None:
                episodes.append(
                    EpisodeFeatures(
                        date=date,
                        peak_pm25=peak or 0.0,
                        avg_pm25=avg or 0.0,
                        temperature=wr[1] or 0.0,
                        humidity=wr[2] or 0.0,
                        wind_speed=wr[3] or 0.0,
                        wind_direction=wr[4] if wr[4] is not None else 0.0,
                        pressure=wr[5] or 1013.0,
                        month=wr[6] or 1,
                        hours=wr[7] or 0,
                    )
                )
        return episodes
    finally:
        conn.close()


def _get_current_context(db_path: Path) -> dict[str, Any]:
    """Get current conditions for similarity comparison.

    Uses a SINGLE connection for all queries to avoid overhead.
    """
    now = datetime.now(UTC)
    conn = _get_read_connection(db_path)
    try:
        # 1. Current PM2.5
        row = conn.execute(
            """
            SELECT value FROM observations
            WHERE parameter = 'pm2_5'
              AND observation_type = 'observation'
            ORDER BY observed_at DESC LIMIT 1
            """
        ).fetchone()
        current_pm25 = row[0] if row else None

        # 2. Current wind direction
        row = conn.execute(
            """
            SELECT value FROM observations
            WHERE parameter = 'wind_direction_10m'
              AND observation_type = 'observation'
            ORDER BY observed_at DESC LIMIT 1
            """
        ).fetchone()
        current_wind_dir = row[0] if row else None

        # 3. Latest weather params (optimized: subquery per parameter)
        weather: dict[str, float | None] = {
            "temperature": None,
            "humidity": None,
            "wind_speed": None,
            "pressure": None,
        }
        param_map = {
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "wind_speed_10m": "wind_speed",
            "pressure_msl": "pressure",
        }
        for db_param, out_key in param_map.items():
            row = conn.execute(
                """
                SELECT value FROM observations
                WHERE parameter = ?
                  AND observation_type = 'observation'
                  AND value IS NOT NULL
                ORDER BY observed_at DESC LIMIT 1
                """,
                [db_param],
            ).fetchone()
            if row:
                weather[out_key] = row[0]
    finally:
        conn.close()

    current_month = now.month
    current_sector = deg_to_sector(current_wind_dir) if current_wind_dir is not None else None

    return {
        "current_pm25": current_pm25,
        "temperature": weather.get("temperature"),
        "humidity": weather.get("humidity"),
        "wind_speed": weather.get("wind_speed"),
        "wind_direction": current_wind_dir,
        "wind_sector": current_sector,
        "pressure": weather.get("pressure"),
        "month": current_month,
        "season": get_current_season(),
        "timestamp": now.isoformat(),
    }


# ── Similarity Computation ─────────────────────────────────────────


def _compute_distance(
    current: dict[str, Any], episode: EpisodeFeatures
) -> tuple[float, list[SimilarityFactor]]:
    """Compute weighted Euclidean distance between current and episode.

    Returns (distance, factors) where distance is in [0, sqrt(sum_weights)].
    """
    factors = []
    weighted_sum = 0.0

    # PM2.5
    if current.get("current_pm25") is not None:
        c = _normalize(current["current_pm25"], "peak_pm25")
        h = _normalize(episode.peak_pm25, "peak_pm25")
        diff = abs(c - h)
        w = FEATURE_WEIGHTS["peak_pm25"]
        weighted_sum += w * diff * diff
        factors.append(
            SimilarityFactor(
                dimension="peak_pm25",
                current_value=current["current_pm25"],
                historical_value=episode.peak_pm25,
                matches=diff < 0.15,
                label="PM2.5 severity",
                unit="ug/m3",
            )
        )

    # Temperature
    if current.get("temperature") is not None:
        c = _normalize(current["temperature"], "temperature")
        h = _normalize(episode.temperature, "temperature")
        diff = abs(c - h)
        w = FEATURE_WEIGHTS["temperature"]
        weighted_sum += w * diff * diff
        factors.append(
            SimilarityFactor(
                dimension="temperature",
                current_value=current["temperature"],
                historical_value=episode.temperature,
                matches=diff < 0.15,
                label="temperature",
                unit="C",
            )
        )

    # Humidity
    if current.get("humidity") is not None:
        c = _normalize(current["humidity"], "humidity")
        h = _normalize(episode.humidity, "humidity")
        diff = abs(c - h)
        w = FEATURE_WEIGHTS["humidity"]
        weighted_sum += w * diff * diff
        factors.append(
            SimilarityFactor(
                dimension="humidity",
                current_value=current["humidity"],
                historical_value=episode.humidity,
                matches=diff < 0.15,
                label="humidity",
                unit="%",
            )
        )

    # Wind speed
    if current.get("wind_speed") is not None:
        c = _normalize(current["wind_speed"], "wind_speed")
        h = _normalize(episode.wind_speed, "wind_speed")
        diff = abs(c - h)
        w = FEATURE_WEIGHTS["wind_speed"]
        weighted_sum += w * diff * diff
        factors.append(
            SimilarityFactor(
                dimension="wind_speed",
                current_value=current["wind_speed"],
                historical_value=episode.wind_speed,
                matches=diff < 0.15,
                label="wind speed",
                unit="km/h",
            )
        )

    # Wind direction (circular)
    if current.get("wind_direction") is not None:
        diff = _circular_distance(current["wind_direction"], episode.wind_direction)
        w = FEATURE_WEIGHTS["wind_direction"]
        weighted_sum += w * diff * diff
        # Check if same sector
        current_sector = deg_to_sector(current["wind_direction"])
        episode_sector = deg_to_sector(episode.wind_direction)
        factors.append(
            SimilarityFactor(
                dimension="wind_direction",
                current_value=current["wind_direction"],
                historical_value=episode.wind_direction,
                matches=current_sector == episode_sector,
                label=f"wind from {episode_sector} sector",
                unit="deg",
            )
        )

    # Pressure
    if current.get("pressure") is not None:
        c = _normalize(current["pressure"], "pressure")
        h = _normalize(episode.pressure, "pressure")
        diff = abs(c - h)
        w = FEATURE_WEIGHTS["pressure"]
        weighted_sum += w * diff * diff
        factors.append(
            SimilarityFactor(
                dimension="pressure",
                current_value=current["pressure"],
                historical_value=episode.pressure,
                matches=diff < 0.15,
                label="atmospheric pressure",
                unit="hPa",
            )
        )

    # Month / Season
    c_month = _normalize(float(current.get("month", 1)), "month")
    h_month = _normalize(float(episode.month), "month")
    diff = abs(c_month - h_month)
    # Circular month distance (Dec=12, Jan=1 are close)
    if diff > 0.5:
        diff = 1.0 - diff
    w = FEATURE_WEIGHTS["month"]
    weighted_sum += w * diff * diff
    factors.append(
        SimilarityFactor(
            dimension="month",
            current_value=float(current.get("month", 1)),
            historical_value=float(episode.month),
            matches=diff < 0.15,
            label="seasonal timing",
            unit="month",
        )
    )

    distance = math.sqrt(weighted_sum)
    return distance, factors


def _label_distance(distance: float) -> str:
    """Convert normalized distance to qualitative label."""
    if distance < DISTANCE_CLOSEST:
        return MATCH_CLOSEST
    if distance < DISTANCE_STRONG:
        return MATCH_STRONG
    if distance < DISTANCE_MODERATE:
        return MATCH_MODERATE
    return MATCH_WEAK


# ── Historical Outcome ─────────────────────────────────────────────


def _compute_what_happened_next(
    db_path: Path, episode_date: str
) -> dict[str, Any]:
    """Compute what happened after the peak in a historical episode.

    Uses ONLY actual observed data. Never phrases as prediction.
    """
    conn = _get_read_connection(db_path)
    try:
        # Get hourly PM2.5 for the episode day
        rows = conn.execute(
            """
            SELECT
                CAST(strftime('%H', observed_at) AS INTEGER) as hour,
                ROUND(AVG(value), 1) as avg_pm25
            FROM observations
            WHERE parameter = 'pm2_5'
              AND observation_type = 'observation'
              AND DATE(observed_at) = ?
            GROUP BY CAST(strftime('%H', observed_at) AS INTEGER)
            ORDER BY hour ASC
            """,
            [episode_date],
        ).fetchall()

        if not rows:
            return {"peak_delay_hours": None, "recovery_hours": None}

        hours_data = [(r[0], r[1]) for r in rows]
        peak_pm25 = max(v for _, v in hours_data)
        peak_hour = next(h for h, v in hours_data if v == peak_pm25)

        # Time to peak from first reading
        first_hour = hours_data[0][0]
        peak_delay = peak_hour - first_hour

        # Recovery: hours from peak to first reading below 120
        recovery_hours = None
        for h, v in hours_data:
            if h > peak_hour and v < EPISODE_PM25_THRESHOLD:
                recovery_hours = h - peak_hour
                break

        # PM2.5 trajectory: was it declining at end of day?
        last_value = hours_data[-1][1]
        declining = last_value < peak_pm25

        return {
            "peak_delay_hours": peak_delay,
            "recovery_hours": recovery_hours,
            "peak_pm25": peak_pm25,
            "peak_hour": peak_hour,
            "end_value": last_value,
            "declining_at_end": declining,
        }
    finally:
        conn.close()


def _format_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    """Format historical outcome for API response.

    Uses past-tense, observational language only.
    """
    parts = []
    if outcome.get("peak_delay_hours") is not None:
        delay = outcome["peak_delay_hours"]
        if delay == 0:
            parts.append("Peak occurred in the first hour")
        elif delay == 1:
            parts.append("Peak arrived approximately 1 hour later")
        else:
            parts.append(f"Peak arrived approximately {delay}h later")

    if outcome.get("recovery_hours") is not None:
        rec = outcome["recovery_hours"]
        if rec <= 6:
            parts.append(f"Recovery followed within {rec}h")
        elif rec <= 12:
            parts.append(f"Conditions improved after {rec}h")
        else:
            parts.append(f"Recovery took approximately {rec}h")
    elif outcome.get("declining_at_end"):
        parts.append("PM2.5 was declining by end of recorded period")
    else:
        parts.append("Elevated conditions persisted through the recorded period")

    return {
        "peak_delay_hours": outcome.get("peak_delay_hours"),
        "recovery_hours": outcome.get("recovery_hours"),
        "summary": "; ".join(parts) if parts else "Insufficient data for outcome summary",
    }


# ── Replay Date Range ──────────────────────────────────────────────


def _replay_range(episode_date: str) -> tuple[str, str]:
    """Compute replay date range: day before through day after."""
    from datetime import timedelta

    d = datetime.strptime(episode_date, "%Y-%m-%d")
    start = (d - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (d + timedelta(days=2)).strftime("%Y-%m-%d")
    return start, end


# ── Main Entry Point ───────────────────────────────────────────────


def find_analogs(
    db_path: Path,
    limit: int = 3,
) -> AnalogResponse:
    """Find historical episodes most similar to current conditions.

    Args:
        db_path: Path to SQLite database.
        limit: Number of analogs to return (default 3).

    Returns:
        AnalogResponse with current context and ranked analogs.
    """
    # 1. Get current conditions
    current = _get_current_context(db_path)

    # 2. Fetch all episode features
    episodes = _fetch_all_episode_features(db_path)
    total_searched = len(episodes)

    if total_searched == 0:
        return AnalogResponse(
            current_context=current,
            analogs=[],
            total_episodes_searched=0,
            caveat="No historical episodes found in database.",
        )

    # 3. Compute distances
    scored: list[tuple[float, EpisodeFeatures, list[SimilarityFactor]]] = []
    for ep in episodes:
        dist, factors = _compute_distance(current, ep)
        scored.append((dist, ep, factors))

    # 4. Sort by distance (closest first)
    scored.sort(key=lambda x: x[0])

    # 5. Build top-N results
    analogs: list[AnalogResult] = []
    for dist, ep, factors in scored[:limit]:
        label = _label_distance(dist)

        # What happened next
        raw_outcome = _compute_what_happened_next(db_path, ep.date)
        outcome = _format_outcome(raw_outcome)

        # Replay range
        replay_start, replay_end = _replay_range(ep.date)

        analogs.append(
            AnalogResult(
                date=ep.date,
                peak_pm25=ep.peak_pm25,
                avg_pm25=ep.avg_pm25,
                duration_hours=ep.hours,
                distance=dist,
                similarity_label=label,
                similarity_factors=factors,
                what_happened_next=outcome,
                replay_start=replay_start,
                replay_end=replay_end,
            )
        )

    return AnalogResponse(
        current_context=current,
        analogs=analogs,
        total_episodes_searched=total_searched,
        caveat=(
            "Historical analogs describe similarity to past observations. "
            "They are not guarantees about the current event."
        ),
    )


# ── Verification Context Enrichment (Phase 5) ─────────────────────


def enrich_with_verification_context(
    response: AnalogResponse,
    db_path: Path,
) -> dict:
    """Enrich an analog response with verification statistics.

    Provides transparent context from past human verifications.
    Does NOT modify the original AnalogResponse — returns a new dict.

    Design Rules:
    - Minimum 3 verified cases before showing percentage statistics
    - Historical verification is context only, not a guarantee
    - This is a transparent feedback loop, NOT machine learning

    Args:
        response: The analog response to enrich.
        db_path: Path to the SQLite database.

    Returns:
        Dict with the original response data plus verification_stats.
    """
    # Import here to avoid circular imports
    from .verification import compute_verification_stats
    from .verification_schemas import MIN_SAMPLE_FOR_STATS

    result = {
        "current_context": response.current_context,
        "analogs": [
            {
                "date": a.date,
                "peak_pm25": a.peak_pm25,
                "avg_pm25": a.avg_pm25,
                "duration_hours": a.duration_hours,
                "distance": a.distance,
                "similarity_label": a.similarity_label,
                "similarity_factors": [
                    {
                        "dimension": f.dimension,
                        "current_value": f.current_value,
                        "historical_value": f.historical_value,
                        "matches": f.matches,
                        "label": f.label,
                        "unit": f.unit,
                    }
                    for f in a.similarity_factors
                ],
                "what_happened_next": a.what_happened_next,
                "replay_start": a.replay_start,
                "replay_end": a.replay_end,
            }
            for a in response.analogs
        ],
        "total_episodes_searched": response.total_episodes_searched,
        "caveat": response.caveat,
    }

    # Attempt to add verification context
    try:
        if db_path.exists():
            stats = compute_verification_stats(db_path)
            result["verification_context"] = {
                "total_verifications": stats.total_verifications,
                "has_sufficient_data": stats.total_verifications >= MIN_SAMPLE_FOR_STATS,
                "recommendation_supported_pct": stats.recommendation_supported_pct,
                "area_supported_pct": stats.area_supported_pct,
                "hypothesis_hit_rate": stats.hypothesis_hit_rate,
                "disclaimer": (
                    "Historical verification data provides context for ongoing investigations. "
                    "It does not guarantee the accuracy of current AI analysis."
                ),
            }
        else:
            result["verification_context"] = {
                "total_verifications": 0,
                "has_sufficient_data": False,
                "recommendation_supported_pct": None,
                "area_supported_pct": None,
                "hypothesis_hit_rate": None,
                "disclaimer": "Verification data unavailable.",
            }
    except Exception as exc:
        logger.warning("Verification context enrichment failed", error=str(exc))
        result["verification_context"] = {
            "total_verifications": 0,
            "has_sufficient_data": False,
            "recommendation_supported_pct": None,
            "area_supported_pct": None,
            "hypothesis_hit_rate": None,
            "disclaimer": "Verification context could not be loaded.",
        }

    return result
