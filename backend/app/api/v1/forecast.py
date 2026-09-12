"""Forecast API endpoints.

Exposes PM2.5 forecast predictions via HTTP.

Endpoints:
    GET /api/v1/forecast?horizon=6
        → Single-horizon prediction

    GET /api/v1/forecast/all
        → All horizons at once

    GET /api/v1/forecast/status
        → Model store and prediction service readiness

Design:
    - The endpoint is a thin HTTP adapter over PredictionService
    - All domain logic lives in app.modeling.serving
    - Error responses use the established ApplicationError pattern
    - Every response includes model provenance and data quality info
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from ...core.config import get_settings
from ...core.db import get_db_connection, db_exists, is_cloud_db
from ...core.errors import ErrorCode
from ...modeling.serving.audit import count_predictions, get_recent_predictions
from ...modeling.serving.model_store import ModelStore
from ...modeling.serving.prediction_service import SUPPORTED_HORIZONS, PredictionService

router = APIRouter(prefix="/forecast", tags=["forecast"])

# ── Singleton service (lazy initialisation) ────────────────────────

_prediction_service: PredictionService | None = None


def _resolve_backend_root() -> Path:
    """Resolve the backend/ project root directory.

    Uses Path(__file__) resolution — always works regardless of
    the current working directory when uvicorn is launched.

    File lives at: backend/app/api/v1/forecast.py
    Navigate up:   v1 → api → app → backend
    """
    return Path(__file__).resolve().parent.parent.parent.parent


async def _get_prediction_service() -> PredictionService:
    """Get or create the singleton PredictionService."""
    global _prediction_service  # noqa: PLW0603
    if _prediction_service is None:
        settings = get_settings()
        backend_dir = _resolve_backend_root()
        models_dir = backend_dir / "data" / "models"

        if is_cloud_db():
            db_path_obj = None  # cloud connection uses LAYERBASE_DB_URL
        else:
            db_path = settings.database_url.replace("sqlite:///", "")
            # Resolve db_path relative to backend root if it's not absolute
            db_path_obj = Path(db_path)
            if not db_path_obj.is_absolute():
                db_path_obj = backend_dir / db_path_obj

        store = ModelStore(models_dir)
        _prediction_service = PredictionService(
            model_store=store,
            db_path=db_path_obj,
            auto_load=True,
        )
    return _prediction_service


def reset_prediction_service() -> None:
    """Reset the singleton (for testing)."""
    global _prediction_service  # noqa: PLW0603
    if _prediction_service is not None:
        _prediction_service.model_store.unload_all()
    _prediction_service = None


# ── Endpoints ─────────────────────────────────────────────────────


@router.get(
    "",
    summary="Get PM2.5 forecast",
    description=(
        "Generate a PM2.5 concentration prediction for the specified "
        "forecast horizon. Returns the predicted value, model provenance, "
        "data freshness, and any warnings."
    ),
)
async def get_forecast(
    horizon: int = Query(
        ...,
        description="Forecast horizon in hours",
        ge=1,
        le=24,
    ),
) -> dict:
    """Generate a single-horizon PM2.5 prediction.

    The prediction uses the most recent available observations
    and the selected model for the requested horizon.
    """
    if horizon not in SUPPORTED_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": ErrorCode.CLIENT_INVALID_REQUEST.value,
                    "message": (
                        f"Unsupported horizon: {horizon}h. "
                        f"Supported horizons: {SUPPORTED_HORIZONS}"
                    ),
                }
            },
        )

    try:
        service = await _get_prediction_service()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.PREDICTION_UNAVAILABLE.value,
                    "message": "An internal error occurred",
                }
            },
        )

    result = service.predict(horizon=horizon, record_to_db=True)

    if not result.is_successful:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.PREDICTION_UNAVAILABLE.value,
                    "message": "Prediction failed",
                    "details": {
                        "errors": result.errors,
                        "warnings": result.warnings,
                    },
                }
            },
        )

    return {"forecast": result.to_dict()}


@router.get(
    "/all",
    summary="Get all-horizon forecasts",
    description="Generate PM2.5 predictions for all supported horizons (1h, 3h, 6h, 12h, 24h).",
)
async def get_all_forecasts() -> dict:
    """Generate predictions for all supported horizons."""
    try:
        service = await _get_prediction_service()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.PREDICTION_UNAVAILABLE.value,
                    "message": "An internal error occurred",
                }
            },
        )

    results = service.predict_all_horizons(record_to_db=True)
    forecasts = {}
    errors = []
    for horizon, result in results.items():
        if result.is_successful:
            forecasts[str(horizon)] = result.to_dict()
        else:
            errors.append({
                "horizon": horizon,
                "errors": result.errors,
                "warnings": result.warnings,
            })

    return {
        "forecasts": forecasts,
        "errors": errors,
        "horizon_count": len(forecasts),
    }


@router.get(
    "/status",
    summary="Forecast service status",
    description="Report the actual readiness state of models, prediction infrastructure, and data freshness.",
)
async def forecast_status() -> dict:
    """Report the actual readiness state of the forecast system.

    Includes:
    - Model store status (loaded horizons, errors)
    - Data freshness state (FRESH/DEGRADED/STALE/UNAVAILABLE)
    - Database health
    """
    try:
        service = await _get_prediction_service()
    except Exception:
        return {
            "ready": False,
            "error": "Prediction service not initialised",
        }

    try:
        base_status = service.status()
    except Exception as exc:
        base_status = {
            "ready": service.is_ready,
            "error": "An internal error occurred",
        }

    # Add freshness assessment
    try:
        from ...modeling.serving.freshness import assess_freshness
        settings = get_settings()
        db_path_str = settings.database_url.replace("sqlite:///", "")
        db_path_obj = Path(db_path_str)
        if not db_path_obj.is_absolute():
            db_path_obj = _resolve_backend_root() / db_path_obj

        freshness = assess_freshness(db_path_obj)
        base_status["freshness"] = freshness.to_dict()

        # Add data-quality summary: observation vs forecast counts
        conn = get_db_connection(read_only=True)
        try:
            rows = conn.execute(
                "SELECT observation_type, COUNT(*) FROM observations "
                "GROUP BY observation_type"
            ).fetchall()
            base_status["data_quality"] = {
                "observation_counts": {r[0]: r[1] for r in rows},
            }
        finally:
            conn.close()
    except Exception as exc:
        base_status["freshness"] = {
            "state": "unavailable",
            "error": "An internal error occurred",
        }

    return base_status


@router.get(
    "/history",
    summary="Recent prediction history",
    description="Retrieve recent prediction records from the audit trail.",
)
async def prediction_history(
    horizon: int | None = Query(None, description="Filter by horizon"),
    limit: int = Query(20, ge=1, le=100, description="Max records"),
) -> dict:
    """Get recent prediction records from the audit trail."""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")

    try:
        records = get_recent_predictions(db_path, horizon=horizon, limit=limit)
        counts = count_predictions(db_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )

    return {
        "predictions": records,
        "count": len(records),
        "summary": counts,
    }
