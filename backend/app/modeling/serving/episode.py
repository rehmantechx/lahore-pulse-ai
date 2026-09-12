"""Episode intelligence -- rule-based detection using ML forecasts as input.

This module provides deterministic episode detection, trajectory analysis,
weather context comparison, and narrative generation.

CRITICAL TERMINOLOGY:
- Episode detection is RULE-BASED, NOT machine learning
- The ML contribution is the PM2.5 forecast (from existing models)
- Weather comparisons show STATISTICAL ASSOCIATION, NOT causation
- No numeric confidence scores are generated

Episode Definition (Definition 4, validated):
    PM2.5 > 120 AND increase >= 30 in 6h, sustained >= 3h

For real-time stateless detection, we approximate:
    current PM2.5 > 120 AND6h_delta >= 30
    OR current PM2.5 > 150 (sustained severe)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from ...core.db import get_db_connection, is_cloud_db


# -- Episode States ---------------------------------------------------------


class EpisodeState:
    """Episode states -- 4 states maximum."""

    NORMAL = "normal"
    EPISODE = "episode"
    IMPROVING = "improving"
    UNCERTAIN = "uncertain"


# -- Trajectory Directions --------------------------------------------------


class Trajectory:
    """Trajectory directions."""

    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    UNKNOWN = "unknown"


# -- Detection Thresholds (validated from Definition 4) ---------------------

EPISODE_PM25_THRESHOLD = 120.0  # ug/m3 -- episode detection threshold
EPISODE_DELTA_THRESHOLD = 30.0  # ug/m3 -- minimum rise in 6h
EPISODE_SEVERE_THRESHOLD = 150.0  # ug/m3 -- sustained severe detection
IMPROVING_THRESHOLD = 100.0  # ug/m3 -- below this = improving
NORMAL_THRESHOLD = 80.0  # ug/m3 -- stable below this = normal
DELTA_WINDOW_HOURS = 6  # hours for delta calculation


# -- Weather Episode Profiles (validated from Phase 11) ---------------------

EPISODE_WEATHER_PROFILES = {
    "temperature": {
        "episode_median": 14.28,
        "non_episode_median": 24.10,
        "direction": "colder",
        "condition": lambda v: v < 18.0,
        "unit": "C",
        "label": "Temperature",
    },
    "humidity": {
        "episode_median": 81.51,
        "non_episode_median": 62.69,
        "direction": "higher",
        "condition": lambda v: v > 70.0,
        "unit": "%",
        "label": "Humidity",
    },
    "wind_speed": {
        "episode_median": 4.86,
        "non_episode_median": 7.67,
        "direction": "lower",
        "condition": lambda v: v < 6.0,
        "unit": "km/h",
        "label": "Wind speed",
    },
    "pressure": {
        "episode_median": 1015.88,
        "non_episode_median": 1008.10,
        "direction": "higher",
        "condition": lambda v: v > 1010.0,
        "unit": "hPa",
        "label": "Pressure",
    },
}


# -- Historical Context (validated from Phase 11 + Phase 10) ----------------

HISTORICAL_CONTEXT = {
    "total_episodes": 371,
    "seasonal": {
        "winter": {"count": 299, "pct": 80.6, "ci_95": [76.3, 84.3]},
        "autumn": {"count": 40, "pct": 10.8, "ci_95": [7.6, 14.0]},
        "spring": {"count": 17, "pct": 4.6, "ci_95": [2.9, 7.2]},
        "summer": {"count": 15, "pct": 4.0, "ci_95": [2.5, 6.6]},
    },
    "duration": {"mean": 5.8, "median": 6.0, "min": 3, "max": 15},
    "peak_pm25": {"mean": 186.2, "median": 171.4, "min": 122.5, "max": 353.9},
    "time_to_peak": {"mean": 3.6, "median": 3.0, "min": 1, "max": 8},
    "recovery": {
        "mild_peak": {"hours": 9, "note": "Peak < 150 ug/m3"},
        "moderate_peak": {"hours": 14, "note": "Peak 150-250 ug/m3"},
        "severe_peak": {"hours": 26, "note": "Peak > 250 ug/m3"},
    },
    "within_6h_peak_pct": 90.8,
    "within_24h_recovery_pct": 89.2,
}


# -- Data structures --------------------------------------------------------


@dataclass
class EpisodeWeatherVariable:
    """Single weather variable comparison."""

    label: str
    current_value: float | None
    episode_median: float
    non_episode_median: float
    matches_pattern: bool
    direction: str
    unit: str


@dataclass
class EpisodeResult:
    """Complete episode intelligence result.

    Contains all computed values for the API response.
    No numeric confidence scores -- uses existing trust displays.
    """

    # State
    state: str = EpisodeState.NORMAL
    state_description: str = ""

    # Current conditions
    current_pm25: float | None = None
    current_6h_delta: float | None = None

    # Trajectory
    trajectory: str = Trajectory.UNKNOWN
    trajectory_description: str = ""
    near_term: str = Trajectory.UNKNOWN
    medium_term: str = Trajectory.UNKNOWN
    recovery_expected: bool = False
    recovery_text: str = ""
    highest_forecast_horizon: int | None = None
    highest_forecast_value: float | None = None
    peak_passed: bool = True

    # Weather context
    weather_variables: list[EpisodeWeatherVariable] = field(default_factory=list)
    weather_note: str = ""

    # Historical context
    historical: dict[str, Any] = field(default_factory=dict)

    # Narrative
    narrative: str = ""
    narrative_caveat: str = ""

    # Data status
    data_status: str = "unknown"
    freshness_hours: float | None = None

    # Forecast reliability (from HORIZON_META)
    forecast_reliability: dict[str, str] = field(default_factory=dict)

    # System info
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "state": self.state,
            "state_description": self.state_description,
            "current_pm25": round(self.current_pm25, 1) if self.current_pm25 is not None else None,
            "current_6h_delta": round(self.current_6h_delta, 1) if self.current_6h_delta is not None else None,
            "trajectory": self.trajectory,
            "trajectory_description": self.trajectory_description,
            "near_term": self.near_term,
            "medium_term": self.medium_term,
            "recovery_expected": self.recovery_expected,
            "recovery_text": self.recovery_text,
            "highest_forecast_horizon": self.highest_forecast_horizon,
            "highest_forecast_value": (
                round(self.highest_forecast_value, 1)
                if self.highest_forecast_value is not None
                else None
            ),
            "peak_passed": self.peak_passed,
            "weather_context": {
                "variables": [
                    {
                        "label": wv.label,
                        "current_value": (
                            round(wv.current_value, 1)
                            if wv.current_value is not None
                            else None
                        ),
                        "episode_median": wv.episode_median,
                        "matches_pattern": wv.matches_pattern,
                        "direction": wv.direction,
                        "unit": wv.unit,
                    }
                    for wv in self.weather_variables
                ],
                "note": self.weather_note,
            },
            "historical_context": self.historical,
            "narrative": self.narrative,
            "narrative_caveat": self.narrative_caveat,
            "data_status": self.data_status,
            "freshness_hours": (
                round(self.freshness_hours, 1)
                if self.freshness_hours is not None
                else None
            ),
            "forecast_reliability": self.forecast_reliability,
            "warnings": self.warnings,
        }


# -- Database helpers -------------------------------------------------------


def _get_read_connection(db_path: Path) -> sqlite3.Connection:
    """Open a read-optimized connection (SQLite or PostgreSQL)."""
    if is_cloud_db():
        return get_db_connection(read_only=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-16000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def _fetch_recent_pm25(
    db_path: Path, as_of: datetime, hours: int = DELTA_WINDOW_HOURS
) -> list[tuple[str, float]]:
    """Fetch recent PM2.5 observations.

    Returns list of (observed_at_iso, value) sorted by time ascending.
    """
    start = (as_of - timedelta(hours=hours)).isoformat()
    sql = """
        SELECT observed_at, value
        FROM observations
        WHERE parameter = 'pm2_5'
          AND observation_type = 'observation'
          AND observed_at >= ?
        ORDER BY observed_at ASC
    """
    conn = _get_read_connection(db_path)
    try:
        rows = conn.execute(sql, [start]).fetchall()
        return [(r[0], r[1]) for r in rows]
    finally:
        conn.close()


def _fetch_weather_at(
    db_path: Path, timestamp: datetime
) -> dict[str, float | None]:
    """Fetch weather parameters at a specific timestamp.

    Returns dict with keys: temperature, humidity, wind_speed, pressure.
    """
    ts = timestamp.isoformat()
    sql = """
        SELECT parameter, value
        FROM observations
        WHERE observation_type = 'observation'
          AND observed_at <= ?
          AND parameter IN ('temperature_2m', 'relative_humidity_2m',
                            'wind_speed_10m', 'pressure_msl')
        ORDER BY observed_at DESC
    """
    conn = _get_read_connection(db_path)
    try:
        rows = conn.execute(sql, [ts]).fetchall()
    finally:
        conn.close()

    # Take the most recent value for each parameter
    result: dict[str, float | None] = {
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
    seen = set()
    for param, value in rows:
        mapped = param_map.get(param)
        if mapped and mapped not in seen:
            result[mapped] = value
            seen.add(mapped)
    return result


# -- Core logic functions ---------------------------------------------------


def detect_episode_state(
    current_pm25: float | None,
    recent_pm25: list[tuple[str, float]],
    freshness_hours: float | None,
) -> str:
    """Determine episode state from current PM2.5 and recent history.

    Uses two concepts per the architecture review corrections:
    1. EPISODE ACTIVITY: sustained elevated PM2.5 or rapid rise
    2. SEPARATELY: trajectory handles direction

    States:
        NORMAL    -- PM2.5 below thresholds, no episode conditions
        EPISODE   -- Active pollution episode (rapid rise OR sustained severe)
        IMPROVING -- Episode was active, PM2.5 now declining
        UNCERTAIN -- Insufficient data
    """
    # No data -> uncertain
    if current_pm25 is None:
        return EpisodeState.UNCERTAIN

    # Stale data -> uncertain
    if freshness_hours is not None and freshness_hours > 6.0:
        return EpisodeState.UNCERTAIN

    # Calculate 6h delta
    delta = _compute_delta(current_pm25, recent_pm25)

    # -- EPISODE detection --
    # Rapid rise: current above threshold AND significant increase in 6h
    rapid_rise = (
        current_pm25 > EPISODE_PM25_THRESHOLD
        and delta is not None
        and delta >= EPISODE_DELTA_THRESHOLD
    )

    # Sustained severe: high PM2.5 that has been elevated
    # (checks if multiple recent observations are all above severe threshold)
    sustained_severe = False
    if current_pm25 > EPISODE_SEVERE_THRESHOLD and len(recent_pm25) >= 3:
        above_count = sum(1 for _, v in recent_pm25[-3:] if v > EPISODE_SEVERE_THRESHOLD)
        sustained_severe = above_count >= 3

    if rapid_rise or sustained_severe:
        return EpisodeState.EPISODE

    # -- IMPROVING detection --
    # Below improving threshold AND was recently in episode conditions
    if current_pm25 < IMPROVING_THRESHOLD:
        was_recently_elevated = any(
            v > EPISODE_PM25_THRESHOLD for _, v in recent_pm25
        )
        if was_recently_elevated:
            return EpisodeState.IMPROVING

    return EpisodeState.NORMAL


def _compute_delta(
    current_pm25: float, recent_pm25: list[tuple[str, float]]
) -> float | None:
    """Compute the change in PM2.5 over the delta window.

    Returns the difference (current - oldest in window), or None
    if insufficient data.
    """
    if not recent_pm25:
        return None

    # Use the oldest observation in the window as baseline
    oldest_value = recent_pm25[0][1]
    if oldest_value is None:
        return None

    return current_pm25 - oldest_value


def compute_trajectory(
    current_pm25: float | None,
    forecasts: dict[int, float | None],
    state: str,
) -> dict[str, Any]:
    """Compute trajectory from direct forecast comparisons.

    Uses MAE-based margins from HORIZON_META:
        1h MAE = 4.5 -> margin = 5
        6h MAE = 14.5 -> margin = 15
    """
    if current_pm25 is None:
        return {
            "near_term": Trajectory.UNKNOWN,
            "medium_term": Trajectory.UNKNOWN,
            "recovery_expected": False,
            "recovery_text": "Insufficient data for trajectory analysis.",
            "highest_forecast_horizon": None,
            "highest_forecast_value": None,
            "peak_passed": True,
            "trajectory_description": "Insufficient data for trajectory analysis.",
        }

    f1 = forecasts.get(1)
    f6 = forecasts.get(6)
    f12 = forecasts.get(12)
    f24 = forecasts.get(24)

    # Near-term (1h, MAE=4.5 -> margin=5)
    if f1 is not None:
        if f1 > current_pm25 + 5:
            near_term = Trajectory.RISING
        elif f1 < current_pm25 - 5:
            near_term = Trajectory.FALLING
        else:
            near_term = Trajectory.STABLE
    else:
        near_term = Trajectory.UNKNOWN

    # Medium-term (6h, MAE=14.5 -> margin=15)
    if f6 is not None:
        if f6 > current_pm25 + 15:
            medium_term = Trajectory.RISING
        elif f6 < current_pm25 - 15:
            medium_term = Trajectory.FALLING
        else:
            medium_term = Trajectory.STABLE
    else:
        medium_term = Trajectory.UNKNOWN

    # Recovery indication from longer horizons
    recovery_expected = False
    recovery_parts = []
    if f12 is not None and f12 < IMPROVING_THRESHOLD:
        recovery_expected = True
        recovery_parts.append(
            f"12-hour forecast is {f12:.0f} ug/m3 (below {IMPROVING_THRESHOLD:.0f})"
        )
    if f24 is not None and f24 < IMPROVING_THRESHOLD:
        recovery_expected = True
        recovery_parts.append(
            f"24-hour forecast is {f24:.0f} ug/m3 (below {IMPROVING_THRESHOLD:.0f})"
        )

    if recovery_expected:
        recovery_text = (
            "Forecast suggests conditions will improve: "
            + "; ".join(recovery_parts)
            + "."
        )
    else:
        recovery_text = (
            "Forecast does not yet indicate conditions dropping below "
            f"{IMPROVING_THRESHOLD:.0f} ug/m3."
        )

    # Highest forecast horizon
    available_forecasts = {
        h: v for h, v in forecasts.items() if v is not None
    }
    if available_forecasts:
        highest_h = max(available_forecasts, key=available_forecasts.get)
        highest_v = available_forecasts[highest_h]
    else:
        highest_h = None
        highest_v = None

    # Peak passed determination
    if near_term == Trajectory.RISING or medium_term == Trajectory.RISING:
        peak_passed = False
    else:
        peak_passed = True

    # Trajectory description
    if near_term == Trajectory.RISING:
        trajectory_desc = (
            "PM2.5 is expected to increase in the near term."
        )
    elif near_term == Trajectory.FALLING:
        if medium_term == Trajectory.FALLING:
            trajectory_desc = (
                "PM2.5 is expected to decline over the next several hours."
            )
        else:
            trajectory_desc = (
                "PM2.5 shows near-term decline."
            )
    elif near_term == Trajectory.STABLE:
        trajectory_desc = (
            "PM2.5 is expected to remain near the current level."
        )
    else:
        trajectory_desc = (
            "Insufficient forecast data to determine trajectory."
        )

    return {
        "near_term": near_term,
        "medium_term": medium_term,
        "recovery_expected": recovery_expected,
        "recovery_text": recovery_text,
        "highest_forecast_horizon": highest_h,
        "highest_forecast_value": highest_v,
        "peak_passed": peak_passed,
        "trajectory_description": trajectory_desc,
    }


def compare_weather(
    current_weather: dict[str, float | None],
) -> list[EpisodeWeatherVariable]:
    """Compare current weather to validated episode profiles.

    Each variable is compared INDEPENDENTLY.
    No composite score. No numeric percentages.
    """
    results = []
    for key, profile in EPISODE_WEATHER_PROFILES.items():
        value = current_weather.get(key)
        matches = profile["condition"](value) if value is not None else False
        results.append(
            EpisodeWeatherVariable(
                label=profile["label"],
                current_value=value,
                episode_median=profile["episode_median"],
                non_episode_median=profile["non_episode_median"],
                matches_pattern=matches,
                direction=profile["direction"],
                unit=profile["unit"],
            )
        )
    return results


def generate_narrative(
    state: str,
    current_pm25: float | None,
    trajectory: dict[str, Any],
    weather_vars: list[EpisodeWeatherVariable],
) -> tuple[str, str]:
    """Generate human-readable narrative.

    Returns (narrative, caveat).
    No causal language. No prescriptive recommendations.
    """
    parts = []

    # State description
    if state == EpisodeState.EPISODE:
        parts.append("A pollution episode is currently active.")
    elif state == EpisodeState.IMPROVING:
        parts.append("Pollution episode conditions are improving.")
    elif state == EpisodeState.NORMAL:
        parts.append("No pollution episode is currently detected.")
    else:
        parts.append("Insufficient data to determine episode status.")

    # Current reading
    if current_pm25 is not None:
        parts.append(f"Current PM2.5 is {current_pm25:.0f} ug/m3.")

    # Trajectory
    near = trajectory.get("near_term", Trajectory.UNKNOWN)
    if near == Trajectory.RISING:
        parts.append("PM2.5 is expected to increase in the near term.")
    elif near == Trajectory.FALLING:
        parts.append("PM2.5 is expected to decline.")
    elif near == Trajectory.STABLE:
        parts.append("PM2.5 is expected to remain near current levels.")

    # Recovery
    recovery_text = trajectory.get("recovery_text", "")
    if recovery_text and trajectory.get("recovery_expected"):
        parts.append(recovery_text)

    # Weather context
    matching = [wv for wv in weather_vars if wv.matches_pattern]
    if matching:
        labels = ", ".join(wv.label.lower() for wv in matching)
        parts.append(
            f"Current conditions ({labels}) are consistent with "
            "conditions associated with historical pollution episodes."
        )

    narrative = " ".join(parts)

    # Standard caveat
    caveat = (
        "This is based on a single grid point (31.5204, 74.3587). "
        "Weather associations are statistical, not causal. "
        "Recovery timing has high uncertainty."
    )

    return narrative, caveat


def get_forecast_reliability() -> dict[str, str]:
    """Map horizon reliability from validated HORIZON_META labels.

    No numeric scores. Uses existing project terminology.
    """
    return {
        "1h": "High reliability",
        "3h": "High reliability",
        "6h": "Moderate reliability",
        "12h": "Moderate reliability",
        "24h": "Greater uncertainty",
    }


def get_current_season() -> str:
    """Get current season name from date."""
    month = datetime.now(UTC).month
    if month in (11, 12, 1, 2):
        return "winter"
    elif month in (9, 10):
        return "autumn"
    elif month in (3, 4, 5):
        return "spring"
    else:
        return "summer"


# -- Main orchestration function --------------------------------------------


def compute_episode_intelligence(
    db_path: Path,
    forecasts: dict[int, float | None],
    freshness_hours: float | None,
    freshness_state: str | None = None,
) -> EpisodeResult:
    """Compute complete episode intelligence.

    Orchestrates all sub-computations into a single result.
    Stateless: computes from scratch on every call.

    Args:
        db_path: Path to SQLite database.
        forecasts: Dict mapping horizon -> predicted PM2.5 value.
        freshness_hours: Hours since latest observation.
        freshness_state: Freshness state string (fresh/degraded/stale/unavailable).

    Returns:
        EpisodeResult with all computed values.
    """
    result = EpisodeResult()

    # 1. Fetch current PM2.5 from database
    now = datetime.now(UTC)
    recent_pm25 = _fetch_recent_pm25(db_path, now, hours=DELTA_WINDOW_HOURS)

    if recent_pm25:
        result.current_pm25 = recent_pm25[-1][1]  # Latest value
        result.current_6h_delta = _compute_delta(result.current_pm25, recent_pm25)
    else:
        # Fallback: use 1h forecast as current reading
        if forecasts.get(1) is not None:
            result.current_pm25 = forecasts[1]
            result.warnings.append(
                "No direct observations available; "
                "using 1h forecast as current estimate."
            )

    # 2. Determine episode state
    result.state = detect_episode_state(
        result.current_pm25, recent_pm25, freshness_hours
    )

    # 3. Compute trajectory
    trajectory = compute_trajectory(
        result.current_pm25, forecasts, result.state
    )
    result.trajectory = trajectory["near_term"]
    result.near_term = trajectory["near_term"]
    result.medium_term = trajectory["medium_term"]
    result.recovery_expected = trajectory["recovery_expected"]
    result.recovery_text = trajectory["recovery_text"]
    result.highest_forecast_horizon = trajectory["highest_forecast_horizon"]
    result.highest_forecast_value = trajectory["highest_forecast_value"]
    result.peak_passed = trajectory["peak_passed"]
    result.trajectory_description = trajectory["trajectory_description"]

    # 4. Compare weather
    weather_data = _fetch_weather_at(db_path, now)
    result.weather_variables = compare_weather(weather_data)
    matching = [wv for wv in result.weather_variables if wv.matches_pattern]
    total = len(result.weather_variables)
    result.weather_note = (
        f"{len(matching)} of {total} weather factors match "
        "conditions associated with historical episodes. "
        "This is statistical association, not causation."
    )

    # 5. Historical context
    season = get_current_season()
    season_ctx = HISTORICAL_CONTEXT["seasonal"].get(season, {})
    result.historical = {
        "total_episodes": HISTORICAL_CONTEXT["total_episodes"],
        "season": season,
        "seasonal_frequency": (
            f"{season_ctx.get('pct', 0):.1f}% of episodes occur in "
            f"{season}"
        ),
        "average_duration_hours": HISTORICAL_CONTEXT["duration"]["mean"],
        "average_peak": HISTORICAL_CONTEXT["peak_pm25"]["mean"],
        "recovery_stats": HISTORICAL_CONTEXT["recovery"],
        "peaks_within_6h_pct": HISTORICAL_CONTEXT["within_6h_peak_pct"],
        "recovery_within_24h_pct": HISTORICAL_CONTEXT["within_24h_recovery_pct"],
    }

    # 6. Narrative
    result.narrative, result.narrative_caveat = generate_narrative(
        result.state, result.current_pm25, trajectory, result.weather_variables
    )

    # 7. Data status
    result.data_status = freshness_state or "unknown"
    result.freshness_hours = freshness_hours

    # 8. Forecast reliability (from existing project metadata)
    result.forecast_reliability = get_forecast_reliability()

    # 9. State description
    state_descriptions = {
        EpisodeState.NORMAL: "No pollution episode is currently detected.",
        EpisodeState.EPISODE: (
            "A pollution episode is currently active. "
            "PM2.5 is elevated above normal levels."
        ),
        EpisodeState.IMPROVING: (
            "Pollution episode conditions are improving. "
            "PM2.5 is declining from recent elevated levels."
        ),
        EpisodeState.UNCERTAIN: (
            "Insufficient data to determine episode status. "
            "Data may be stale or unavailable."
        ),
    }
    result.state_description = state_descriptions.get(result.state, "")

    return result
