"""Episode Intelligence API endpoint.

Endpoints:
    GET /api/v1/episode         — Current episode intelligence
    GET /api/v1/episode/analogs — Historical analog search

Design:
    - Reuses existing PredictionService for forecast retrieval
    - Reuses existing assess_freshness for data status
    - Rule-based episode detection (NOT machine learning)
    - Weather context shows statistical association (NOT causation)
    - Analog engine uses normalized distance (NOT ML similarity)
    - No numeric confidence scores generated
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from ...core.config import get_settings
from ...core.errors import ErrorCode
from ...modeling.serving.episode import EpisodeState, compute_episode_intelligence
from ...modeling.serving.freshness import FreshnessState, assess_freshness
from ...modeling.serving.model_store import ModelStore
from ...modeling.serving.prediction_service import (
    SUPPORTED_HORIZONS,
    PredictionService,
)
from ...modeling.serving.source_compass import compute_source_compass

router = APIRouter(prefix="/episode", tags=["episode"])

# -- Singleton service (lazy initialisation) --------------------------------

_prediction_service: PredictionService | None = None


def _resolve_backend_root() -> Path:
    """Resolve the backend/ project root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


async def _get_prediction_service() -> PredictionService:
    """Get or create the singleton PredictionService."""
    global _prediction_service  # noqa: PLW0603
    if _prediction_service is None:
        settings = get_settings()
        backend_dir = _resolve_backend_root()
        models_dir = backend_dir / "data" / "models"
        db_path = settings.database_url.replace("sqlite:///", "")

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


def _get_db_path() -> Path:
    """Get resolved database path."""
    settings = get_settings()
    backend_dir = _resolve_backend_root()
    db_path = settings.database_url.replace("sqlite:///", "")
    db_path_obj = Path(db_path)
    if not db_path_obj.is_absolute():
        db_path_obj = backend_dir / db_path_obj
    return db_path_obj


# -- Endpoint ---------------------------------------------------------------


@router.get(
    "",
    summary="Get episode intelligence",
    description=(
        "Provides episode-level interpretation of current PM2.5 conditions. "
        "Combines rule-based episode detection with ML forecast trajectory "
        "and historical weather associations. "
        "Episode detection is rule-based, not machine learning."
    ),
)
async def get_episode_intelligence() -> dict:
    """Get episode intelligence for current conditions.

    Returns episode state, trajectory, weather context, and narrative.
    Uses existing forecast infrastructure -- no new ML models.
    """
    db_path = _get_db_path()

    # 1. Assess data freshness
    try:
        freshness = assess_freshness(db_path)
    except Exception as exc:
        logger.error("Freshness assessment failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.PREDICTION_UNAVAILABLE.value,
                    "message": "An internal error occurred",
                }
            },
        )

    # 2. Get forecasts from existing service
    forecasts: dict[int, float | None] = {}
    try:
        service = await _get_prediction_service()
        results = service.predict_all_horizons(record_to_db=False)
        for horizon, result in results.items():
            if result.is_successful:
                forecasts[horizon] = result.predicted_pm25
            else:
                forecasts[horizon] = None
    except Exception as exc:
        logger.warning(
            "Forecast retrieval failed, continuing with episode detection",
            error=str(exc),
        )
        # Continue without forecasts -- trajectory will be unknown
        forecasts = {h: None for h in SUPPORTED_HORIZONS}

    # 3. Compute episode intelligence
    try:
        result = compute_episode_intelligence(
            db_path=db_path,
            forecasts=forecasts,
            freshness_hours=freshness.freshness_hours
            if freshness.freshness_hours != float("inf")
            else None,
            freshness_state=freshness.state.value
            if hasattr(freshness.state, "value")
            else str(freshness.state),
        )
    except Exception as exc:
        logger.error("Episode computation failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )

    # 3b. Compute Source Compass (directional analysis)
    compass = None
    try:
        compass = compute_source_compass(db_path)
        logger.info(
            "Source Compass computed",
            strongest_sector=compass.historical.strongest_sector if compass else None,
            association=compass.historical.association_label if compass else None,
        )
    except Exception as exc:
        logger.warning(
            "Source Compass computation failed, continuing without directional data",
            error=str(exc),
        )

    # 4. Build response
    response = result.to_dict()

    # Add Source Compass data
    if compass is not None:
        response["source_compass"] = compass.to_dict()

    # Add system metadata
    response["system"] = {
        "grid_point": {"lat": 31.5204, "lon": 74.3587},
        "detection_definition": (
            "PM2.5 > 120 AND increase >= 30 in 6h, sustained >= 3h "
            "(Definition 4, validated on 371 episodes)"
        ),
        "detection_method": "Rule-based (NOT machine learning)",
        "dataset_size": 371,
    }

    return response


# ── Historical Analog Endpoint ─────────────────────────────────────


@router.get(
    "/analogs",
    summary="Find historical analog episodes",
    description=(
        "Finds historical episodes most similar to current conditions "
        "using normalized Euclidean distance across meteorological dimensions. "
        "Similarity is statistical, not causal. "
        "No ML model is used."
    ),
)
async def get_episode_analogs(
    limit: int = Query(3, ge=1, le=10, description="Number of analogs to return"),
) -> dict:
    """Find historical episodes similar to current conditions.

    Uses deterministic similarity matching across available
    meteorological dimensions. No ML. No black-box.
    """
    db_path = _get_db_path()

    try:
        from ...modeling.serving.historical_analog import find_analogs

        result = find_analogs(db_path, limit=limit)

        # Serialize
        return {
            "current_context": result.current_context,
            "analogs": [
                {
                    "date": a.date,
                    "peak_pm25": a.peak_pm25,
                    "avg_pm25": a.avg_pm25,
                    "duration_hours": a.duration_hours,
                    "similarity_label": a.similarity_label,
                    "similarity_factors": [
                        {
                            "dimension": f.dimension,
                            "current_value": f.current_value,
                            "historical_value": f.historical_value,
                            "matches": f.matches,
                            "label": f.label,
                            "unit": f.unit,
                        }
                        for f in a.similarity_factors
                    ],
                    "what_happened_next": a.what_happened_next,
                    "replay_start": a.replay_start,
                    "replay_end": a.replay_end,
                }
                for a in result.analogs
            ],
            "total_episodes_searched": result.total_episodes_searched,
            "caveat": result.caveat,
        }
    except Exception as exc:
        logger.error("Historical analog computation failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "ANALOG_UNAVAILABLE",
                    "message": "An internal error occurred",
                }
            },
        )
