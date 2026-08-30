"""Replay API endpoint.

Provides historical observation data for the episode replay feature.
Read-only access to PM2.5 time series for a given date range.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ...infrastructure.database import get_database

router = APIRouter(prefix="/replay", tags=["replay"])


@router.get("/observations")
async def get_replay_observations(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    parameter: str = Query("pm2_5", description="Parameter name"),
) -> dict:
    """Get hourly observations for replay animation.

    Returns time-series data grouped by hour for the specified date range.
    Used by the frontend replay component to animate historical episodes.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        parameter: Parameter to query (default: pm2_5).
    """
    db = await get_database()

    # Validate date format (basic check)
    for date_str, label in [(start_date, "start_date"), (end_date, "end_date")]:
        if len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
            raise HTTPException(
                status_code=422,
                detail=f"Invalid {label} format. Expected YYYY-MM-DD.",
            )

    # Query hourly aggregated observations
    rows = db.fetch_all(
        """SELECT
               DATE(observed_at) as date,
               CAST(strftime('%H', observed_at) AS INTEGER) as hour,
               ROUND(AVG(value), 1) as avg_value,
               ROUND(MIN(value), 1) as min_value,
               ROUND(MAX(value), 1) as max_value,
               COUNT(*) as reading_count
           FROM observations
           WHERE parameter = ?
             AND DATE(observed_at) BETWEEN ? AND ?
           GROUP BY DATE(observed_at), CAST(strftime('%H', observed_at) AS INTEGER)
           ORDER BY date ASC, hour ASC""",
        [parameter, start_date, end_date],
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No observations found for parameter '{parameter}' between {start_date} and {end_date}.",
        )

    # Compute summary stats
    values = [r["avg_value"] for r in rows]
    peak_value = max(values)
    avg_value = round(sum(values) / len(values), 1)
    total_readings = sum(r["reading_count"] for r in rows)

    return {
        "observations": rows,
        "meta": {
            "start_date": start_date,
            "end_date": end_date,
            "parameter": parameter,
            "total_hours": len(rows),
            "total_readings": total_readings,
            "peak_value": peak_value,
            "avg_value": avg_value,
        },
    }


@router.get("/episodes")
async def list_episodes(
    min_peak: float = Query(120.0, description="Minimum peak PM2.5 to include"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """List historical dates where episode detection would trigger.

    Returns dates sorted by peak PM2.5 descending, filtered by
    the minimum peak threshold. Used by the replay date picker.

    Args:
        min_peak: Minimum peak PM2.5 value to include (default: 120.0).
        limit: Maximum number of episodes to return.
    """
    db = await get_database()

    rows = db.fetch_all(
        """SELECT
               DATE(observed_at) as date,
               ROUND(MAX(value), 1) as peak_pm25,
               ROUND(AVG(value), 1) as avg_pm25,
               COUNT(*) as readings,
               SUM(CASE WHEN value > 150 THEN 1 ELSE 0 END) as hours_above_severe
           FROM observations
           WHERE parameter = 'pm2_5'
           GROUP BY DATE(observed_at)
           HAVING peak_pm25 >= ?
           ORDER BY peak_pm25 DESC
           LIMIT ?""",
        [min_peak, limit],
    )

    return {
        "episodes": rows,
        "count": len(rows),
        "min_peak_threshold": min_peak,
    }
