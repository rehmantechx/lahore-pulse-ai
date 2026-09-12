"""Freshness service — centralised data freshness state machine.

Determines whether the observation database is fresh enough for
reliable predictions.  Exposes four discrete states:

    FRESH       — Latest observation < 2 hours old.
    DEGRADED    — Latest observation 2–6 hours old.
    STALE       — Latest observation 6–12 hours old.
    UNAVAILABLE — Latest observation > 12 hours old OR no data at all.

Design principles:
    - Reads real data from the database — never fabricates.
    - All thresholds are constants sourced from the same values used
      by feature_assembly.py so the system is internally consistent.
    - Stateless: each call re-reads the database.  Caching is left
      to the caller (e.g. the forecast/status endpoint).
    - No AI models, no external services, no fallback data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

import sqlite3
from loguru import logger

from ...core.db import get_db_connection, is_cloud_db


# ── Freshness States ─────────────────────────────────────────────


class FreshnessState(StrEnum):
    """Discrete freshness states for the observation database."""

    FRESH = "fresh"
    DEGRADED = "degraded"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


# ── Thresholds (hours) ──────────────────────────────────────────

FRESH_THRESHOLD_HOURS = 2.0
DEGRADED_THRESHOLD_HOURS = 6.0  # == STALENESS_WARNING_HOURS in feature_assembly
STALE_THRESHOLD_HOURS = 12.0   # == STALENESS_CRITICAL_HOURS in feature_assembly


# ── Result Dataclass ────────────────────────────────────────────


@dataclass
class FreshnessResult:
    """Structured freshness assessment.

    Attributes:
        state: The discrete freshness state.
        freshness_hours: Hours between latest observation and the
            reference timestamp.  ``inf`` when no data exists.
        latest_observation_at: ISO timestamp of the most recent
            observation in the database, or ``None``.
        parameters_available: Number of distinct parameters with
            recent observations.
        warnings: Human-readable warning messages.
    """

    state: FreshnessState
    freshness_hours: float
    latest_observation_at: str | None
    parameters_available: int
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "freshness_hours": (
                round(self.freshness_hours, 2)
                if self.freshness_hours != float("inf")
                else None
            ),
            "latest_observation_at": self.latest_observation_at,
            "parameters_available": self.parameters_available,
            "warnings": self.warnings,
        }


# ── Core Function ───────────────────────────────────────────────


def _get_read_conn(db_path: Path) -> sqlite3.Connection:
    """Open a lightweight read-only connection (SQLite or PostgreSQL)."""
    if is_cloud_db():
        return get_db_connection(read_only=True)
    conn = sqlite3.connect(str(db_path), timeout=10, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-16000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def assess_freshness(
    db_path: str | Path,
    as_of: datetime | None = None,
) -> FreshnessResult:
    """Assess the freshness of the observation database.

    Queries the database directly for the latest observation timestamp
    and the number of distinct parameters available.

    Args:
        db_path: Path to the SQLite database.
        as_of: Reference timestamp (default: now UTC).

    Returns:
        FreshnessResult with state and diagnostics.
    """
    db_path = Path(db_path)
    if as_of is None:
        as_of = datetime.now(UTC)
    elif as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    warnings: list[str] = []

    if not is_cloud_db() and not db_path.exists():
        return FreshnessResult(
            state=FreshnessState.UNAVAILABLE,
            freshness_hours=float("inf"),
            latest_observation_at=None,
            parameters_available=0,
            warnings=[f"Database not found: {db_path}"],
        )

    conn = _get_read_conn(db_path)
    try:
        # Get the latest observation timestamp.
        # CRITICAL: Only consider actual observations, not forecasts.
        # Forecast records have observation_type='forecast' and may have
        # observed_at values in the future, which would produce negative
        # freshness_hours and false FRESH states.
        row = conn.execute(
            """SELECT MAX(observed_at) FROM observations
               WHERE observation_type = 'observation'"""
        ).fetchone()
        latest_str: str | None = row[0] if row else None

        if latest_str is None:
            return FreshnessResult(
                state=FreshnessState.UNAVAILABLE,
                freshness_hours=float("inf"),
                latest_observation_at=None,
                parameters_available=0,
                warnings=["No observations in database"],
            )

        # Parse the timestamp
        latest_dt = datetime.fromisoformat(latest_str)
        if latest_dt.tzinfo is None:
            latest_dt = latest_dt.replace(tzinfo=UTC)

        # Compute freshness
        freshness_hours = (as_of - latest_dt).total_seconds() / 3600

        # Count distinct parameters with recent data (within 24h of latest)
        param_row = conn.execute(
            """SELECT COUNT(DISTINCT parameter)
               FROM observations
               WHERE observed_at >= ?
               AND observation_type = 'observation'""",
            [(latest_dt - timedelta(hours=24)).isoformat()],
        ).fetchone()
        parameters_available = param_row[0] if param_row else 0

    finally:
        conn.close()

    # Determine state
    if freshness_hours <= FRESH_THRESHOLD_HOURS:
        state = FreshnessState.FRESH
    elif freshness_hours <= DEGRADED_THRESHOLD_HOURS:
        state = FreshnessState.DEGRADED
    elif freshness_hours <= STALE_THRESHOLD_HOURS:
        state = FreshnessState.STALE
    else:
        state = FreshnessState.UNAVAILABLE

    # Build warnings
    if state == FreshnessState.FRESH:
        pass  # No warnings needed
    elif state == FreshnessState.DEGRADED:
        warnings.append(
            f"Data is {freshness_hours:.1f}h old — "
            f"within degraded range (>{FRESH_THRESHOLD_HOURS}h)"
        )
    elif state == FreshnessState.STALE:
        warnings.append(
            f"WARNING: Data is {freshness_hours:.1f}h old — "
            f"stale (>{DEGRADED_THRESHOLD_HOURS}h). "
            f"Forecasts may be unreliable."
        )
    else:
        warnings.append(
            f"CRITICAL: Data is {freshness_hours:.1f}h old — "
            f"unavailable for reliable forecasting (>{STALE_THRESHOLD_HOURS}h). "
            f"Run a data refresh to restore forecast capability."
        )

    if parameters_available < 5:
        warnings.append(
            f"Only {parameters_available} parameters available — "
            f"predictions require 19+ parameters"
        )

    logger.info(
        "Freshness assessed",
        state=state.value,
        freshness_hours=round(freshness_hours, 1),
        parameters=parameters_available,
    )

    return FreshnessResult(
        state=state,
        freshness_hours=freshness_hours,
        latest_observation_at=latest_str,
        parameters_available=parameters_available,
        warnings=warnings,
    )
