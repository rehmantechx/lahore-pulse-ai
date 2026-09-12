"""Health and readiness endpoints.

These endpoints report the ACTUAL state of the system.
They do NOT claim that external sources or models are operational
when they are not configured yet.

- /health: Basic liveness check (is the service running?)
- /readiness: Detailed readiness (what components are available?)
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter

from ...core.config import get_settings
from ...core.db import get_db_connection, db_exists, is_cloud_db

router = APIRouter(tags=["health"])

# ── Readiness cache ─────────────────────────────────────────────
# The readiness endpoint runs heavy synchronous SQLite queries against
# a 707 MB database.  Without caching it takes ~45s, which causes the
# frontend health hook (20 s timeout) to always time out → permanent
# "Offline" status.  We cache the result and refresh it in the
# background every 30 s.
_READINESS_CACHE: dict | None = None
_READINESS_CACHE_TIME: float = 0.0
_READINESS_LOCK = threading.Lock()
_READINESS_REFRESH_INTERVAL = 30  # seconds


def _resolve_db_path() -> Path:
    """Resolve the database file path from LPA_DATABASE_URL.

    Mirrors the resolution logic in infrastructure/database.py get_database():
    - Strips the sqlite:/// prefix
    - Resolves relative paths against the backend/ directory
    - Passes absolute paths through unchanged

    Returns:
        Resolved Path to the SQLite database file.
    """
    settings = get_settings()
    raw_path = settings.database_url.replace("sqlite:///", "")
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        # Navigate: app/api/v1 → api → app → backend
        backend_root = Path(__file__).resolve().parent.parent.parent.parent
        db_path = backend_root / db_path
    return db_path


def _refresh_readiness_cache() -> dict:
    """Compute a fresh readiness snapshot (blocking)."""
    db_path = _resolve_db_path()

    model_status = _check_model_store()
    db_health = _check_database(db_path)
    freshness_info = _check_data_freshness(db_path)
    prediction_info = _check_predictions(db_path)

    return {
        "status": "ready",
        "service": "lahore-pulse-ai",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "components": {
            "api": {"status": "operational"},
            "database": db_health,
            "data_freshness": freshness_info,
            "forecast_models": model_status,
            "prediction_accountability": prediction_info,
        },
    }


def _get_readiness_cached() -> dict:
    """Return cached readiness or refresh if stale."""
    global _READINESS_CACHE, _READINESS_CACHE_TIME
    now = time.monotonic()
    with _READINESS_LOCK:
        if _READINESS_CACHE is not None and (now - _READINESS_CACHE_TIME) < _READINESS_REFRESH_INTERVAL:
            return _READINESS_CACHE
    # Cache miss or stale — compute fresh result.
    result = _refresh_readiness_cache()
    with _READINESS_LOCK:
        _READINESS_CACHE = result
        _READINESS_CACHE_TIME = time.monotonic()
    return result


def _check_database(db_path: Path) -> dict:
    """Check database health: existence, size, and record counts."""
    # In cloud mode, DB is always accessible; in local mode, check the specific path
    if not is_cloud_db() and not db_path.exists():
        return {
            "status": "not_configured",
            "message": "Database not found",
        }

    # File size is only meaningful for local SQLite
    size_mb = None
    if not is_cloud_db() and db_path.exists() and db_path.stat().st_size > 0:
        size_mb = round(db_path.stat().st_size / (1024 * 1024), 1)

    try:
        conn = get_db_connection(read_only=True)
        count = conn.execute("SELECT COUNT(*) FROM observations WHERE observation_type = 'observation'").fetchone()[0]
        conn.close()
        result: dict = {
            "status": "available",
            "observation_count": count,
        }
        if size_mb is not None:
            result["size_mb"] = size_mb
        elif is_cloud_db():
            result["provider"] = "layerbase"
        return result
    except Exception:
        return {
            "status": "degraded",
            "message": "Database readable but query failed",
            **({"size_mb": size_mb} if size_mb else {}),
        }


def _check_data_freshness(db_path: Path) -> dict:
    """Check data freshness using the freshness service."""
    if not db_path.exists():
        return {
            "state": "unavailable",
            "message": "Database not found",
        }

    try:
        from ...modeling.serving.freshness import assess_freshness
        result = assess_freshness(db_path)
        return {
            "state": result.state.value if hasattr(result.state, "value") else str(result.state),
            "freshness_hours": round(result.freshness_hours, 1) if result.freshness_hours != float("inf") else None,
            "latest_observation_at": result.latest_observation_at.isoformat() if hasattr(result.latest_observation_at, "isoformat") else result.latest_observation_at,
            "parameters_available": result.parameters_available,
            "warnings": result.warnings,
        }
    except Exception:
        return {
            "state": "unavailable",
            "message": "Freshness check failed",
        }


def _check_predictions(db_path: Path) -> dict:
    """Check prediction accountability: how many predictions have been verified."""
    if not db_exists():
        return {"status": "not_configured"}

    try:
        conn = get_db_connection(read_only=True)
        total = conn.execute("SELECT COUNT(*) FROM prediction_records").fetchone()[0]
        if total == 0:
            conn.close()
            return {
                "status": "not_configured",
                "message": "No prediction records yet",
            }
        verified = conn.execute(
            "SELECT COUNT(*) FROM prediction_records WHERE actual_value IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        return {
            "status": "operational",
            "total_predictions": total,
            "verified_count": verified,
            "verification_rate": round(verified / total * 100, 1),
        }
    except Exception:
        return {
            "status": "degraded",
            "message": "Prediction check failed",
        }


def _check_model_store() -> dict:
    """Check whether trained model artifacts exist on disk.

    Reports the ACTUAL state — no fabrication.
    """
    # Navigate from this file (app/api/v1/health.py) to backend/
    this_file = Path(__file__).resolve()
    backend_dir = this_file.parent.parent.parent.parent  # app/api/v1 -> api -> app -> backend
    models_dir = backend_dir / "data" / "models"

    if not models_dir.exists():
        return {
            "status": "not_configured",
            "message": "Models directory does not exist",
        }

    registry_path = models_dir / "model_registry.json"
    if not registry_path.exists():
        return {
            "status": "not_configured",
            "message": "No model registry found",
        }

    joblib_files = list(models_dir.glob("**/*.joblib"))
    horizon_dirs = [
        d for d in models_dir.iterdir()
        if d.is_dir() and d.name.startswith("horizon_")
    ]

    if not joblib_files:
        return {
            "status": "not_configured",
            "message": "No model files found",
        }

    return {
        "status": "available",
        "model_count": len(joblib_files),
        "horizon_count": len(horizon_dirs),
        "horizons": sorted(
            d.name.replace("horizon_", "").replace("h", "")
            for d in horizon_dirs
        ),
    }


@router.get(
    "/health",
    summary="Basic health check",
    description="Returns service status. Use for liveness probes.",
)
async def health_check() -> dict:
    """Confirm the service is running and responsive."""
    return {
        "status": "healthy",
        "service": "lahore-pulse-ai",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/readiness",
    summary="Readiness check",
    description="Returns detailed component status. Use for readiness probes.",
)
async def readiness_check() -> dict:
    """Report actual system readiness.

    Results are cached and refreshed every 30 s in the background.
    This keeps the endpoint fast (< 1 ms) so the frontend health
    hook (20 s timeout) never times out.
    """
    return await asyncio.to_thread(_get_readiness_cached)
