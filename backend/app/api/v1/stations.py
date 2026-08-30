"""Stations API endpoints.

Exposes ground-level monitoring station data for map overlays.

Endpoints:
    GET /api/v1/stations
        → All known stations with latest PM2.5 readings

    GET /api/v1/stations/{station_id}
        → Specific station with recent observations

Design:
    - Stations are discovered from data ingestion (AQICN/WAQI, OpenAQ)
    - Each station shows its latest PM2.5 reading, location, and source
    - Used by the frontend map to show ground-level resolution
      alongside the 45km CAMS grid indicator
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query
from loguru import logger

from ...core.config import get_settings

router = APIRouter(prefix="/stations", tags=["stations"])


def _resolve_backend_root() -> Path:
    """Resolve the backend/ project root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_db_path() -> Path:
    """Get resolved database path."""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")
    db_path_obj = Path(db_path)
    if not db_path_obj.is_absolute():
        db_path_obj = _resolve_backend_root() / db_path_obj
    return db_path_obj


@router.get("")
async def list_stations(
    source: str | None = Query(None, description="Filter by source (aqicn, openaq)"),
) -> dict:
    """List monitoring stations with their latest PM2.5 readings.

    Returns station locations, source info, and most recent observation.
    """
    import sqlite3

    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # Check if stations table exists
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='stations'"
        ).fetchall()

        if not tables:
            return {"stations": [], "count": 0, "note": "Stations table not yet populated"}

        # Get stations with their latest PM2.5 observation
        if source:
            stations = conn.execute(
                """SELECT s.station_id, s.source_id, s.name, s.latitude, s.longitude,
                          s.active,
                          o.value as latest_pm25, o.observed_at as latest_observed_at
                   FROM stations s
                   LEFT JOIN (
                       SELECT station_id, value, observed_at,
                              ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY observed_at DESC) as rn
                       FROM observations
                       WHERE parameter = 'pm25'
                         AND observation_type = 'observation'
                   ) o ON s.station_id = o.station_id AND o.rn = 1
                   WHERE s.source_id = ?
                   ORDER BY s.name""",
                (source,),
            ).fetchall()
        else:
            stations = conn.execute(
                """SELECT s.station_id, s.source_id, s.name, s.latitude, s.longitude,
                          s.active,
                          o.value as latest_pm25, o.observed_at as latest_observed_at
                   FROM stations s
                   LEFT JOIN (
                       SELECT station_id, value, observed_at,
                              ROW_NUMBER() OVER (PARTITION BY station_id ORDER BY observed_at DESC) as rn
                       FROM observations
                       WHERE parameter = 'pm25'
                         AND observation_type = 'observation'
                   ) o ON s.station_id = o.station_id AND o.rn = 1
                   WHERE s.active = 1
                   ORDER BY s.name""",
            ).fetchall()

        result = []
        for s in stations:
            result.append({
                "station_id": s["station_id"],
                "source_id": s["source_id"],
                "name": s["name"],
                "latitude": s["latitude"],
                "longitude": s["longitude"],
                "active": bool(s["active"]),
                "latest_pm25": s["latest_pm25"],
                "latest_observed_at": s["latest_observed_at"],
            })

        return {
            "stations": result,
            "count": len(result),
        }
    finally:
        conn.close()


@router.get("/history")
async def get_station_history(
    hours: int = Query(48, ge=1, le=168, description="Hours of history to return"),
) -> dict:
    """Get recent PM2.5 observations from ground stations.

    Returns time-series data for charting station-level trends.
    """
    import sqlite3

    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT o.station_id, o.source_id, o.value, o.observed_at
               FROM observations o
               WHERE o.parameter = 'pm25'
                 AND o.observation_type = 'observation'
                 AND o.observed_at >= datetime('now', ?)
               ORDER BY o.observed_at ASC""",
            (f"-{hours} hours",),
        ).fetchall()

        return {
            "count": len(rows),
            "hours": hours,
            "observations": [
                {
                    "station_id": r["station_id"],
                    "source_id": r["source_id"],
                    "value": r["value"],
                    "observed_at": r["observed_at"],
                }
                for r in rows
            ],
        }
    finally:
        conn.close()
