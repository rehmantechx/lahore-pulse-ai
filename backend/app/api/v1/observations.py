"""Observations API endpoints.

Provides read-only access to stored observations.
Phase 1: Basic query and inspection.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ...infrastructure.database import get_database

router = APIRouter(prefix="/observations", tags=["observations"])


@router.get("")
async def list_observations(
    parameter: str | None = Query(None, description="Filter by parameter"),
    source_id: str | None = Query(None, description="Filter by data source"),
    station_id: str | None = Query(None, description="Filter by station ID"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD or ISO format)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD or ISO format)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """List observations with optional filters.

    Args:
        parameter: Filter by parameter name (e.g., pm25, temperature_2m).
        source_id: Filter by source (e.g., openmeteo, openaq, aqicn).
        station_id: Filter by station ID.
        start_date: Start of date range (YYYY-MM-DD or ISO format).
        end_date: End of date range (YYYY-MM-DD or ISO format).
        limit: Maximum observations to return.
        offset: Pagination offset.
    """
    db = await get_database()

    conditions = []
    params: list = []

    if parameter:
        conditions.append("parameter = ?")
        params.append(parameter)
    if source_id:
        conditions.append("source_id = ?")
        params.append(source_id)
    if station_id:
        conditions.append("station_id = ?")
        params.append(station_id)
    if start_date:
        conditions.append("observed_at >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("observed_at <= ?")
        params.append(end_date)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Get count
    count_result = db.fetch_one(
        f"SELECT COUNT(*) as count FROM observations{where_clause}",
        params,
    )
    total = count_result["count"] if count_result else 0

    # Get data
    results = db.fetch_all(
        f"""SELECT observation_id, source_id, station_id, parameter, value, unit,
                   observed_at, latitude, longitude, quality_status, created_at
            FROM observations
            {where_clause}
            ORDER BY observed_at DESC
            LIMIT ? OFFSET ?""",
        params + [limit, offset],
    )

    return {
        "observations": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_observation_stats() -> dict:
    """Get summary statistics of stored observations.

    Returns counts by source, parameter, and quality.
    """
    db = await get_database()

    by_source = db.fetch_all(
        """SELECT source_id, COUNT(*) as count, MIN(observed_at) as earliest,
                  MAX(observed_at) as latest
           FROM observations GROUP BY source_id"""
    )

    by_parameter = db.fetch_all(
        """SELECT parameter, COUNT(*) as count,
                  MIN(value) as min_value, MAX(value) as max_value,
                  AVG(value) as avg_value
           FROM observations GROUP BY parameter"""
    )

    by_quality = db.fetch_all(
        """SELECT quality_status, COUNT(*) as count
           FROM observations GROUP BY quality_status"""
    )

    total = db.fetch_one("SELECT COUNT(*) as count FROM observations")

    return {
        "total_observations": total["count"] if total else 0,
        "by_source": by_source,
        "by_parameter": by_parameter,
        "by_quality": by_quality,
    }


@router.get("/{observation_id}")
async def get_observation(observation_id: str) -> dict:
    """Get a specific observation by ID.

    Args:
        observation_id: The observation UUID.
    """
    db = await get_database()
    result = db.fetch_one(
        "SELECT * FROM observations WHERE observation_id = ?",
        [observation_id],
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Observation '{observation_id}' not found",
        )

    return {"observation": result}
