"""Alerts API endpoints.

Endpoints:
    GET  /api/v1/alerts/history     — List recent alerts
    GET  /api/v1/alerts/preferences — Get alert preferences
    PUT  /api/v1/alerts/preferences — Update alert preferences

Persistence: SQLite alert_history + alert_tables
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from ...infrastructure.database import get_database

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ── Request/Response Models ──────────────────────────────────────────


class AlertPreferenceUpdate(BaseModel):
    """Single alert preference update."""
    alert_type: str
    enabled: bool


class AlertPreferencesBulkUpdate(BaseModel):
    """Bulk update alert preferences."""
    preferences: list[AlertPreferenceUpdate]


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/history")
async def get_alert_history():
    """Get recent alerts, newest first."""
    db = await get_database()
    rows = db.fetch_all(
        "SELECT * FROM alert_history ORDER BY created_at DESC LIMIT 50"
    )
    return [
        {
            "id": row["alert_id"],
            "type": row["alert_type"],
            "severity": row["severity"],
            "aqi": row["aqi_value"],
            "level": row["level"],
            "message": row["message"],
            "read": bool(row["read"]),
            "timestamp": row["created_at"],
        }
        for row in rows
    ]


@router.get("/preferences")
async def get_alert_preferences():
    """Get all alert preferences."""
    db = await get_database()
    rows = db.fetch_all(
        "SELECT * FROM alert_preferences ORDER BY alert_type"
    )
    return [
        {
            "id": row["pref_id"],
            "alert_type": row["alert_type"],
            "enabled": bool(row["enabled"]),
            "threshold": row["threshold"],
        }
        for row in rows
    ]


@router.put("/preferences")
async def update_alert_preferences(body: AlertPreferencesBulkUpdate):
    """Update alert preferences (bulk)."""
    db = await get_database()
    now = datetime.now(UTC).isoformat()

    for pref in body.preferences:
        # Validate alert_type
        valid_types = {"fair", "moderate", "poor", "dangerous"}
        if pref.alert_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid alert_type: {pref.alert_type}. Must be one of: {valid_types}",
            )

        db.execute(
            "UPDATE alert_preferences SET enabled = ?, updated_at = ? WHERE alert_type = ?",
            (1 if pref.enabled else 0, now, pref.alert_type),
        )

    db.commit()

    # Return updated preferences
    rows = db.fetch_all(
        "SELECT * FROM alert_preferences ORDER BY alert_type"
    )
    return [
        {
            "id": row["pref_id"],
            "alert_type": row["alert_type"],
            "enabled": bool(row["enabled"]),
            "threshold": row["threshold"],
        }
        for row in rows
    ]


@router.post("/history")
async def create_alert(
    alert_type: str,
    severity: str,
    aqi_value: float | None = None,
    level: str = "",
    message: str = "",
):
    """Create a new alert (internal — called by episode detection)."""
    db = await get_database()
    alert_id = f"alert-{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    db.execute(
        "INSERT INTO alert_history (alert_id, alert_type, severity, aqi_value, level, message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (alert_id, alert_type, severity, aqi_value, level, message, now),
    )
    db.commit()

    logger.info("Alert created", alert_id=alert_id, type=alert_type, severity=severity)

    return {
        "id": alert_id,
        "type": alert_type,
        "severity": severity,
        "aqi": aqi_value,
        "level": level,
        "message": message,
        "read": False,
        "timestamp": now,
    }
