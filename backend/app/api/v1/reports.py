"""Reports API endpoints.

Endpoints:
    GET  /api/v1/reports             — List generated reports
    POST /api/v1/reports/generate    — Generate a new report
    GET  /api/v1/reports/{report_id} — Get report details

Persistence: SQLite report_history
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..auth import require_officer, TokenPayload

from ...infrastructure.database import get_database

router = APIRouter(prefix="/reports", tags=["reports"])


# ── Request/Response Models ──────────────────────────────────────────


class ReportGenerateRequest(BaseModel):
    """Request to generate a report."""
    report_type: str  # daily | weekly | monthly | episode | snapshot


# ── Helpers ──────────────────────────────────────────────────────────

def _format_date_range(report_type: str, now: datetime) -> tuple[str, str]:
    """Calculate date range for a report type."""
    if report_type == "daily":
        return now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    elif report_type == "weekly":
        # Last 7 days
        from datetime import timedelta
        start = now - timedelta(days=7)
        return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    elif report_type == "monthly":
        # Current month
        start = now.replace(day=1)
        return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    elif report_type == "episode":
        return now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    elif report_type == "snapshot":
        return now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")


def _report_name(report_type: str, now: datetime) -> str:
    """Generate a human-readable report name."""
    date_str = now.strftime("%b %d, %Y")
    if report_type == "daily":
        return f"Daily Summary – {date_str}"
    elif report_type == "weekly":
        from datetime import timedelta
        start = now - timedelta(days=7)
        return f"Weekly Report – {start.strftime('%b %d')} to {now.strftime('%b %d')}"
    elif report_type == "monthly":
        return f"Monthly Report – {now.strftime('%B %Y')}"
    elif report_type == "episode":
        return f"Episode Report – {date_str}"
    elif report_type == "snapshot":
        return f"Share Snapshot – {date_str}"
    return f"Report – {date_str}"


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("")
async def list_reports():
    """List generated reports, newest first."""
    db = await get_database()
    rows = db.fetch_all(
        "SELECT * FROM report_history ORDER BY created_at DESC LIMIT 50"
    )
    return [
        {
            "id": row["report_id"],
            "name": row["name"],
            "type": row["report_type"].capitalize() if row["report_type"] != "snapshot" else "Snapshot",
            "generatedOn": _format_generated_on(row["created_at"]),
            "range": _format_range(row["range_start"], row["range_end"]),
            "format": row["format"].upper(),
            "status": row["status"],
        }
        for row in rows
    ]


@router.post("/generate")
async def generate_report(body: ReportGenerateRequest, _auth: TokenPayload = Depends(require_officer)):
    """Generate a new report from current data."""
    valid_types = {"daily", "weekly", "monthly", "episode", "snapshot"}
    if body.report_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report_type: {body.report_type}. Must be one of: {valid_types}",
        )

    db = await get_database()
    now = datetime.now(UTC)
    report_id = f"rpt-{uuid4().hex[:12]}"
    range_start, range_end = _format_date_range(body.report_type, now)
    name = _report_name(body.report_type, now)
    fmt = "png" if body.report_type == "snapshot" else "pdf"

    # Fetch current data to embed in report metadata
    metadata = {}

    # Get latest observation stats
    try:
        stats = db.fetch_one(
            "SELECT COUNT(*) as total, MAX(observed_at) as latest FROM observations"
        )
        metadata["total_observations"] = stats["total"] if stats else 0
        metadata["latest_observation"] = stats["latest"] if stats else None
    except Exception:
        pass

    # Get latest PM2.5 for current conditions
    try:
        latest_pm = db.fetch_one(
            "SELECT value FROM observations WHERE parameter IN ('pm2_5', 'pm25') "
            "ORDER BY observed_at DESC LIMIT 1"
        )
        metadata["current_pm25"] = latest_pm["value"] if latest_pm else None
    except Exception:
        pass

    # Get station count
    try:
        station_count = db.fetch_one("SELECT COUNT(*) as cnt FROM stations")
        metadata["station_count"] = station_count["cnt"] if station_count else 0
    except Exception:
        pass

    db.execute(
        "INSERT INTO report_history "
        "(report_id, report_type, name, range_start, range_end, format, status, metadata, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'generated', ?, ?)",
        (
            report_id,
            body.report_type,
            name,
            range_start,
            range_end,
            fmt,
            json.dumps(metadata),
            now.isoformat(),
        ),
    )
    db.commit()

    logger.info("Report generated", report_id=report_id, type=body.report_type)

    return {
        "id": report_id,
        "name": name,
        "type": body.report_type.capitalize() if body.report_type != "snapshot" else "Snapshot",
        "generatedOn": _format_generated_on(now.isoformat()),
        "range": _format_range(range_start, range_end),
        "format": fmt.upper(),
        "status": "generated",
        "metadata": metadata,
    }


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get report details by ID."""
    db = await get_database()
    row = db.fetch_one(
        "SELECT * FROM report_history WHERE report_id = ?",
        (report_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    metadata = {}
    if row["metadata"]:
        try:
            metadata = json.loads(row["metadata"])
        except json.JSONDecodeError:
            pass

    return {
        "id": row["report_id"],
        "name": row["name"],
        "type": row["report_type"],
        "generatedOn": _format_generated_on(row["created_at"]),
        "range": _format_range(row["range_start"], row["range_end"]),
        "format": row["format"].upper(),
        "status": row["status"],
        "metadata": metadata,
    }


# ── Helpers ──────────────────────────────────────────────────────────

def _format_generated_on(iso_timestamp: str) -> str:
    """Format ISO timestamp to 'Aug 26, 2026 · 7:30 AM'."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        # Use %I (zero-padded) for Windows compatibility, strip leading zero manually
        hour_12 = dt.hour % 12 or 12
        minute = dt.minute
        ampm = "AM" if dt.hour < 12 else "PM"
        return f"{dt.strftime('%b %d, %Y')} · {hour_12}:{minute:02d} {ampm}"
    except Exception:
        return iso_timestamp


def _format_range(start: str | None, end: str | None) -> str:
    """Format date range."""
    if not start:
        return "N/A"
    try:
        s = datetime.fromisoformat(start)
        if end and end != start:
            e = datetime.fromisoformat(end)
            return f"{s.strftime('%b %d')} – {e.strftime('%b %d, %Y')}"
        return s.strftime("%b %d, %Y")
    except Exception:
        return start
