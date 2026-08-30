"""Shared test utilities for backend tests.

Provides helpers for resolving data-aware timestamps and other
common patterns used across test modules.

All helpers use REAL data — no mocks, no fabricated values.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def get_latest_observation_time(db_path: str | Path) -> datetime:
    """Get the timestamp of the most recent observation in the database.

    Returns a timezone-aware UTC datetime. This is the actual latest
    data point — not a fabricated or estimated time.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        UTC datetime of the most recent observation.

    Raises:
        ValueError: If no observations exist in the database.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise ValueError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path), timeout=10)
    try:
        row = conn.execute(
            """SELECT MAX(observed_at) FROM observations
               WHERE observation_type = 'observation'"""
        ).fetchone()
    finally:
        conn.close()

    if row is None or row[0] is None:
        raise ValueError("No observations in database")

    latest_str = row[0]
    latest_dt = datetime.fromisoformat(latest_str)
    if latest_dt.tzinfo is None:
        latest_dt = latest_dt.replace(tzinfo=UTC)

    return latest_dt


def get_data_aware_as_of(db_path: str | Path) -> datetime:
    """Get an as_of timestamp aligned to the latest available data.

    Returns the latest observation time plus a small offset (1 minute)
    so that lags and rolling windows can be computed. This makes
    feature assembly tests self-contained regardless of when the
    database was last refreshed.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        UTC datetime suitable for use as as_of in feature assembly.
    """
    from datetime import timedelta

    latest = get_latest_observation_time(db_path)
    # Add 1 minute so the as_of is just after the latest observation
    # but close enough that lag features can be computed
    return latest + timedelta(minutes=1)
