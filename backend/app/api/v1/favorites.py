"""Favorites (Saved Locations) API endpoints.

Endpoints:
    GET    /api/v1/favorites              — List saved locations with live AQ data
    POST   /api/v1/favorites              — Add a saved location
    PUT    /api/v1/favorites/{location_id} — Update a saved location
    DELETE /api/v1/favorites/{location_id} — Remove a saved location

Persistence: SQLite saved_locations table.
Live AQ data is joined from observations table at request time.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..auth import require_auth, TokenPayload
from ...infrastructure.database import get_database

router = APIRouter(prefix="/favorites", tags=["favorites"])


# ── Request/Response Models ──────────────────────────────────────────


class FavoriteCreate(BaseModel):
    """Request to add a saved location."""
    station_id: str | None = None
    name: str
    label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    icon: str = "map-pin"


class FavoriteUpdate(BaseModel):
    """Request to update a saved location."""
    name: str | None = None
    label: str | None = None
    icon: str | None = None
    sort_order: int | None = None


# ── Helpers ──────────────────────────────────────────────────────────

# AQI classification (same as frontend)
_AQI_BANDS = [
    (12, "Excellent", "#22C55E"),
    (25, "Good", "#84CC16"),
    (35, "Fair", "#EAB308"),
    (55, "Moderate", "#F97316"),
    (90, "Poor", "#EF4444"),
    (150, "Very Poor", "#DC2626"),
    (999, "Hazardous", "#7F1D1D"),
]


def _aqi_label(value: float | None) -> dict:
    """Return AQI label, color, and band label for a PM2.5 value."""
    if value is None:
        return {"label": "No Data", "color": "#A09A93", "band": "none"}
    for threshold, label, color in _AQI_BANDS:
        if value <= threshold:
            return {"label": label, "color": color, "band": label.lower()}
    return {"label": "Hazardous", "color": "#7F1D1D", "band": "hazardous"}


def _get_latest_pm25_for_station(db, station_id: str) -> float | None:
    """Get latest PM2.5 reading for a station."""
    row = db.fetch_one(
        "SELECT value FROM observations "
        "WHERE station_id = ? AND parameter IN ('pm2_5', 'pm25') "
        "AND observation_type = 'observation' "
        "ORDER BY observed_at DESC LIMIT 1",
        (station_id,),
    )
    return row["value"] if row else None


def _get_pm10_for_station(db, station_id: str) -> float | None:
    """Get latest PM10 reading for a station."""
    row = db.fetch_one(
        "SELECT value FROM observations "
        "WHERE station_id = ? AND parameter = 'pm10' "
        "AND observation_type = 'observation' "
        "ORDER BY observed_at DESC LIMIT 1",
        (station_id,),
    )
    return row["value"] if row else None


def _get_temperature_for_station(db, station_id: str) -> float | None:
    """Get latest temperature reading for a station."""
    row = db.fetch_one(
        "SELECT value FROM observations "
        "WHERE station_id = ? AND parameter = 'temperature' "
        "AND observation_type = 'observation' "
        "ORDER BY observed_at DESC LIMIT 1",
        (station_id,),
    )
    return row["value"] if row else None


def _get_humidity_for_station(db, station_id: str) -> float | None:
    """Get latest humidity reading for a station."""
    row = db.fetch_one(
        "SELECT value FROM observations "
        "WHERE station_id = ? AND parameter = 'humidity' "
        "AND observation_type = 'observation' "
        "ORDER BY observed_at DESC LIMIT 1",
        (station_id,),
    )
    return row["value"] if row else None


def _enrich_location(db, loc: dict) -> dict:
    """Enrich a saved location with live AQ data from its station."""
    station_id = loc.get("station_id")
    if not station_id:
        loc["pm25"] = None
        loc["pm10"] = None
        loc["temperature"] = None
        loc["humidity"] = None
        loc["aqi"] = _aqi_label(None)
        return loc

    pm25 = _get_latest_pm25_for_station(db, station_id)
    loc["pm25"] = pm25
    loc["pm10"] = _get_pm10_for_station(db, station_id)
    loc["temperature"] = _get_temperature_for_station(db, station_id)
    loc["humidity"] = _get_humidity_for_station(db, station_id)
    loc["aqi"] = _aqi_label(pm25)
    return loc


def _get_station_name(db, station_id: str) -> str | None:
    """Get station name for display."""
    row = db.fetch_one(
        "SELECT name FROM stations WHERE station_id = ?",
        (station_id,),
    )
    return row["name"] if row else None


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("")
async def list_favorites():
    """List all saved locations with live AQ data, ordered by sort_order."""
    db = await get_database()
    rows = db.fetch_all(
        "SELECT * FROM saved_locations ORDER BY sort_order ASC, created_at ASC"
    )

    locations = []
    for row in rows:
        loc = {
            "id": row["location_id"],
            "station_id": row["station_id"],
            "name": row["name"],
            "label": row["label"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "icon": row["icon"],
            "sort_order": row["sort_order"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        _enrich_location(db, loc)
        locations.append(loc)

    return {
        "locations": locations,
        "count": len(locations),
    }


@router.post("")
async def add_favorite(body: FavoriteCreate, _auth: TokenPayload = Depends(require_auth)):
    """Add a new saved location.

    If station_id is provided, the location is linked to a monitoring
    station for live AQ data. Otherwise, only the name/label/icon are stored.
    """
    db = await get_database()

    # Validate station exists if provided
    if body.station_id:
        station = db.fetch_one(
            "SELECT station_id, name FROM stations WHERE station_id = ?",
            (body.station_id,),
        )
        if not station:
            raise HTTPException(
                status_code=404,
                detail=f"Station not found: {body.station_id}",
            )

    location_id = f"loc-{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    # Get current max sort_order
    max_order = db.fetch_one(
        "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM saved_locations"
    )
    next_order = (max_order["max_order"] if max_order else 0) + 1

    # Use station name as default name if not provided
    name = body.name
    if not name and body.station_id:
        station_name = _get_station_name(db, body.station_id)
        if station_name:
            name = station_name

    db.execute(
        "INSERT INTO saved_locations "
        "(location_id, station_id, name, label, latitude, longitude, icon, sort_order, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            location_id,
            body.station_id,
            name,
            body.label,
            body.latitude,
            body.longitude,
            body.icon,
            next_order,
            now,
            now,
        ),
    )
    db.commit()

    logger.info("Favorite added", location_id=location_id, name=name)

    # Return enriched location
    row = db.fetch_one(
        "SELECT * FROM saved_locations WHERE location_id = ?",
        (location_id,),
    )
    loc = {
        "id": row["location_id"],
        "station_id": row["station_id"],
        "name": row["name"],
        "label": row["label"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "icon": row["icon"],
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    _enrich_location(db, loc)
    return loc


@router.put("/{location_id}")
async def update_favorite(location_id: str, body: FavoriteUpdate, _auth: TokenPayload = Depends(require_auth)):
    """Update a saved location's name, label, icon, or sort order."""
    db = await get_database()

    existing = db.fetch_one(
        "SELECT * FROM saved_locations WHERE location_id = ?",
        (location_id,),
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Saved location not found")

    now = datetime.now(UTC).isoformat()
    updates = []
    params = []

    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name)
    if body.label is not None:
        updates.append("label = ?")
        params.append(body.label)
    if body.icon is not None:
        updates.append("icon = ?")
        params.append(body.icon)
    if body.sort_order is not None:
        updates.append("sort_order = ?")
        params.append(body.sort_order)

    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        params.append(location_id)

        db.execute(
            f"UPDATE saved_locations SET {', '.join(updates)} WHERE location_id = ?",
            tuple(params),
        )
        db.commit()

    logger.info("Favorite updated", location_id=location_id)

    # Return enriched location
    row = db.fetch_one(
        "SELECT * FROM saved_locations WHERE location_id = ?",
        (location_id,),
    )
    loc = {
        "id": row["location_id"],
        "station_id": row["station_id"],
        "name": row["name"],
        "label": row["label"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "icon": row["icon"],
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    _enrich_location(db, loc)
    return loc


@router.delete("/{location_id}")
async def delete_favorite(location_id: str, _auth: TokenPayload = Depends(require_auth)):
    """Remove a saved location."""
    db = await get_database()

    existing = db.fetch_one(
        "SELECT * FROM saved_locations WHERE location_id = ?",
        (location_id,),
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Saved location not found")

    db.execute(
        "DELETE FROM saved_locations WHERE location_id = ?",
        (location_id,),
    )
    db.commit()

    logger.info("Favorite deleted", location_id=location_id)

    return {"status": "deleted", "location_id": location_id}
