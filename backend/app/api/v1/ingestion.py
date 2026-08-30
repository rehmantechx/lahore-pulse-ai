"""Ingestion API endpoints.

Provides endpoints for triggering data ingestion and viewing run history.
Phase 1: Basic ingestion triggers and run status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_officer, TokenPayload
from ...application.services.ingestion import IngestionService
from ...core.config import get_settings
from ...infrastructure.database import get_database
from ...infrastructure.providers.aqicn import AQICNProvider
from ...infrastructure.providers.openaq import OpenAQProvider
from ...infrastructure.providers.openmeteo import OpenMeteoProvider

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


async def _get_ingestion_service() -> IngestionService:
    """Create an IngestionService with current config and database."""
    settings = get_settings()
    db = await get_database()
    return IngestionService(settings, db)


@router.post("/runs/weather/historical")
async def trigger_historical_weather_ingestion(
    _auth: TokenPayload = Depends(require_officer),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    latitude: float = Query(31.5204, description="Latitude"),
    longitude: float = Query(74.3587, description="Longitude"),
) -> dict:
    """Trigger historical weather data ingestion from Open-Meteo.

    Fetches weather data from the Open-Meteo Archive API for the
    specified date range and location.

    Args:
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        latitude: Location latitude (default: Lahore center).
        longitude: Location longitude (default: Lahore center).
    """
    settings = get_settings()
    db = await get_database()
    service = IngestionService(settings, db)

    provider = OpenMeteoProvider(settings)
    run = await service.ingest_historical_weather(
        provider=provider,
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "operation": run.operation.value,
        "provider": "openmeteo",
        "total_records": run.total_records,
        "accepted_records": run.accepted_records,
        "rejected_records": run.rejected_records,
        "duration_seconds": run.duration_seconds,
    }


@router.post("/runs/aq/historical")
async def trigger_historical_aq_ingestion(
    _auth: TokenPayload = Depends(require_officer),
    start_date: str = Query(..., description="Start date (ISO 8601)"),
    end_date: str = Query(..., description="End date (ISO 8601)"),
    parameter: str = Query("pm25", description="AQ parameter"),
    latitude: float = Query(31.5204, description="Latitude"),
    longitude: float = Query(74.3587, description="Longitude"),
) -> dict:
    """Trigger historical air quality ingestion from OpenAQ.

    Args:
        start_date: Start date (ISO 8601).
        end_date: End date (ISO 8601).
        parameter: AQ parameter name (pm25, pm10, no2, etc.).
        latitude: Location latitude.
        longitude: Location longitude.
    """
    settings = get_settings()
    db = await get_database()
    service = IngestionService(settings, db)

    provider = OpenAQProvider(settings)
    run = await service.ingest_historical_aq(
        provider=provider,
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameter=parameter,
    )

    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "operation": run.operation.value,
        "provider": "openaq",
        "total_records": run.total_records,
        "accepted_records": run.accepted_records,
        "rejected_records": run.rejected_records,
        "duration_seconds": run.duration_seconds,
    }


@router.post("/runs/aq/live")
async def trigger_live_aq_ingestion(
    _auth: TokenPayload = Depends(require_officer),
) -> dict:
    """Trigger real-time air quality ingestion from AQICN/WAQI.

    Fetches current readings from all known Lahore stations.
    """
    settings = get_settings()
    db = await get_database()
    service = IngestionService(settings, db)

    provider = AQICNProvider(settings)
    run = await service.ingest_live_aqicn(provider=provider)

    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "operation": run.operation.value,
        "provider": "aqicn",
        "total_records": run.total_records,
        "accepted_records": run.accepted_records,
        "rejected_records": run.rejected_records,
        "duration_seconds": run.duration_seconds,
    }


@router.get("/runs")
async def list_ingestion_runs(
    limit: int = Query(20, ge=1, le=100),
    provider: str | None = Query(None),
) -> dict:
    """List recent ingestion runs.

    Args:
        limit: Maximum number of runs to return.
        provider: Filter by provider name.
    """
    db = await get_database()

    if provider:
        results = db.fetch_all(
            """SELECT * FROM ingestion_runs
               WHERE provider = ?
               ORDER BY started_at DESC LIMIT ?""",
            [provider, limit],
        )
    else:
        results = db.fetch_all(
            """SELECT * FROM ingestion_runs
               ORDER BY started_at DESC LIMIT ?""",
            [limit],
        )

    return {
        "runs": results,
        "count": len(results),
    }


@router.get("/runs/{run_id}")
async def get_ingestion_run(run_id: str) -> dict:
    """Get details of a specific ingestion run.

    Args:
        run_id: The run identifier.
    """
    db = await get_database()
    result = db.fetch_one(
        "SELECT * FROM ingestion_runs WHERE run_id = ?",
        [run_id],
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return {"run": result}


@router.post("/refresh", summary="Refresh current data")
async def refresh_current_data(
    _auth: TokenPayload = Depends(require_officer),
    latitude: float = Query(31.5204, description="Latitude"),
    longitude: float = Query(74.3587, description="Longitude"),
    forecast_days: int = Query(3, ge=1, le=5, description="Days of forecast/recent data"),
    past_days: int = Query(3, ge=0, le=92, description="Recent past days to include for gap-filling"),
) -> dict:
    """Refresh the observation database with current data.

    Fetches recent weather and air quality data from available providers:
    - Open-Meteo Forecast API (weather variables, includes recent past)
    - Open-Meteo Air Quality API (CAMS reanalysis, includes recent past)
    - AQICN/WAQI real-time stations (ground-level AQ readings)

    This is the primary mechanism for keeping the database fresh
    enough for reliable predictions. After ingestion, the observation
    cache should be invalidated so subsequent predictions use the new data.

    Returns:
        Summary of all ingestion runs with acceptance counts.
    """
    settings = get_settings()
    db = await get_database()
    service = IngestionService(settings, db)

    results = {}

    # 1. Open-Meteo current weather
    try:
        meteo_provider = OpenMeteoProvider(settings)
        weather_run = await service.ingest_current_weather(
            provider=meteo_provider,
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            past_days=past_days,
        )
        results["weather"] = {
            "run_id": weather_run.run_id,
            "status": weather_run.status.value,
            "accepted": weather_run.accepted_records,
            "rejected": weather_run.rejected_records,
        }
    except Exception:
        results["weather"] = {"status": "failed", "error": "Weather ingestion failed"}

    # 2. Open-Meteo current air quality
    try:
        meteo_provider = OpenMeteoProvider(settings)
        aq_run = await service.ingest_current_air_quality(
            provider=meteo_provider,
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
            past_days=past_days,
        )
        results["air_quality"] = {
            "run_id": aq_run.run_id,
            "status": aq_run.status.value,
            "accepted": aq_run.accepted_records,
            "rejected": aq_run.rejected_records,
        }
    except Exception:
        results["air_quality"] = {"status": "failed", "error": "Air quality ingestion failed"}

    # 3. AQICN real-time stations
    try:
        aqicn_provider = AQICNProvider(settings)
        live_run = await service.ingest_live_aqicn(provider=aqicn_provider)
        results["aqicn_live"] = {
            "run_id": live_run.run_id,
            "status": live_run.status.value,
            "accepted": live_run.accepted_records,
            "rejected": live_run.rejected_records,
        }
    except Exception:
        results["aqicn_live"] = {"status": "failed", "error": "AQICN live ingestion failed"}

    # 4. Invalidate the observation cache so predictions use fresh data
    try:
        from ...modeling.serving.feature_assembly import _observation_cache
        _observation_cache.invalidate()
    except Exception:
        pass  # Non-fatal — cache will expire naturally

    # Compute totals
    total_accepted = sum(
        r.get("accepted", 0) for r in results.values() if isinstance(r, dict)
    )
    total_rejected = sum(
        r.get("rejected", 0) for r in results.values() if isinstance(r, dict)
    )
    failed = sum(
        1 for r in results.values() if isinstance(r, dict) and r.get("status") == "failed"
    )

    return {
        "status": "completed" if failed == 0 else "partial",
        "providers": results,
        "summary": {
            "total_accepted": total_accepted,
            "total_rejected": total_rejected,
            "providers_succeeded": len(results) - failed,
            "providers_failed": failed,
        },
    }
