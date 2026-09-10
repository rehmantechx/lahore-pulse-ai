"""API v1 router.

Aggregates all v1 endpoint routers into a single versioned router.
New endpoint modules should be imported and included here.
"""

from __future__ import annotations

from fastapi import APIRouter

from .accuracy import router as accuracy_router
from ..auth import router as auth_router
from .alerts import router as alerts_router
from .datasources import router as datasources_router
from .episode import router as episode_router
from .favorites import router as favorites_router
from .forecast import router as forecast_router
from .health import router as health_router
from .ingestion import router as ingestion_router
from .investigation import router as investigation_router
from .observations import router as observations_router
from .reports import router as reports_router
from .replay import router as replay_router
from .stations import router as stations_router
from .verification import router as verification_router
from .weather import router as weather_router

api_v1_router = APIRouter()

# Authentication endpoints
api_v1_router.include_router(auth_router)

# Health & system endpoints
api_v1_router.include_router(health_router)

# Phase 1: Data layer endpoints
api_v1_router.include_router(datasources_router)
api_v1_router.include_router(ingestion_router)
api_v1_router.include_router(observations_router)
api_v1_router.include_router(stations_router)

# Phase 5: Forecast/serving endpoints
api_v1_router.include_router(forecast_router)

# Phase 8: Accuracy tracking endpoints
api_v1_router.include_router(accuracy_router)

# Episode Intelligence endpoint
api_v1_router.include_router(episode_router)

# Alerts & Reports endpoints
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(reports_router)

# Favorites (My Lahore) endpoints
api_v1_router.include_router(favorites_router)

# Historical Replay endpoint
api_v1_router.include_router(replay_router)

# Investigation Evidence Assembler endpoint
api_v1_router.include_router(investigation_router)

# Investigation Verification (Phase 5 — Learning Loop)
api_v1_router.include_router(verification_router)

# Weather (current conditions from observations)
api_v1_router.include_router(weather_router)
