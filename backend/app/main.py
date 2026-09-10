"""Lahore Pulse AI — Application Factory.

Creates and configures the FastAPI application instance.
Uses the factory pattern for:
- Testability (can create app with different configurations)
- Environment-specific setup
- Clean initialization order

Usage:
    # Direct execution
    uvicorn app.main:app --reload

    # Programmatic
    app = create_app()
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.errors import register_error_handlers
from .middleware.security_headers import SecurityHeadersMiddleware
from .api.v1.router import api_v1_router
from .core.config import Settings, get_settings
from .core.logging import setup_logging

# Auto-refresh interval: 30 minutes
AUTO_REFRESH_INTERVAL_SECONDS = 30 * 60


async def _auto_refresh_loop() -> None:
    """Background task that periodically refreshes observation data.

    Keeps the database fresh for forecasting without requiring
    manual API calls. Logs success/failure but never crashes.
    """
    from loguru import logger

    _refresh_running = False

    while True:
        try:
            await asyncio.sleep(AUTO_REFRESH_INTERVAL_SECONDS)

            # Guard against overlapping refresh jobs
            if _refresh_running:
                logger.warning("Auto-refresh skipped: previous refresh still running")
                continue
            _refresh_running = True

            try:
                # Import here to avoid circular imports at module level
                from .application.services.ingestion import IngestionService
                from .infrastructure.database import get_database
                from .infrastructure.providers.aqicn import AQICNProvider
                from .infrastructure.providers.openmeteo import OpenMeteoProvider

                settings = get_settings()
                db = await get_database()
                service = IngestionService(settings, db)

                latitude = 31.5204
                longitude = 74.3587
                forecast_days = 3
                past_days = 3
                total_accepted = 0
                total_rejected = 0

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
                    total_accepted += weather_run.accepted_records
                    total_rejected += weather_run.rejected_records
                except Exception as e:
                    logger.warning("Auto-refresh weather failed", error=str(e))

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
                    total_accepted += aq_run.accepted_records
                    total_rejected += aq_run.rejected_records
                except Exception as e:
                    logger.warning("Auto-refresh air quality failed", error=str(e))

                # 3. AQICN real-time stations
                try:
                    aqicn_provider = AQICNProvider(settings)
                    live_run = await service.ingest_live_aqicn(provider=aqicn_provider)
                    total_accepted += live_run.accepted_records
                    total_rejected += live_run.rejected_records
                except Exception as e:
                    logger.warning("Auto-refresh AQICN failed", error=str(e))

                # 4. Invalidate the observation cache
                try:
                    from .modeling.serving.feature_assembly import _observation_cache
                    _observation_cache.invalidate()
                except Exception:
                    pass  # Non-fatal

                logger.info(
                    "Auto-refresh completed",
                    accepted=total_accepted,
                    rejected=total_rejected,
                )
            finally:
                _refresh_running = False

        except asyncio.CancelledError:
            logger.info("Auto-refresh loop cancelled")
            break
        except Exception as exc:
            logger.warning("Auto-refresh failed", error=str(exc))
            # Sleep a shorter interval before retrying on error
            await asyncio.sleep(5 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start auto-refresh background task."""
    from loguru import logger

    logger.info("Starting auto-refresh background task")
    task = asyncio.create_task(_auto_refresh_loop())
    try:
        yield
    finally:
        logger.info("Shutting down auto-refresh background task")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Creates a fully configured FastAPI application instance.

    Args:
        settings: Optional settings override (used in testing).
                  If None, loads from environment variables.

    Returns:
        Configured FastAPI application ready to serve.
    """
    if settings is None:
        settings = get_settings()

    # Configure logging before anything else
    setup_logging(log_level=settings.log_level)

    # Create application
    app = FastAPI(
        title="Lahore Pulse AI",
        description=(
            "Predictive city-intelligence platform for Lahore. "
            "Provides advance warning for air quality, heat, and "
            "flood-related problems using historical and real-time data."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Store settings on app state for access in endpoints
    app.state.settings = settings

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Versioned API routes
    app.include_router(api_v1_router, prefix="/api/v1")

    # Error handlers (must be registered after routes)
    register_error_handlers(app)

    # ── Frontend static file serving + SPA fallback ─────────────
    # Serve the React production build from frontend/dist/.
    # Only active if the build output exists (skipped in tests/dev
    # when frontend has not been built).
    _frontend_dist = (
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    )
    if _frontend_dist.is_dir():
        # Mount hashed asset bundles (JS, CSS) under /assets/
        _assets_dir = _frontend_dist / "assets"
        if _assets_dir.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=str(_assets_dir)),
                name="static-assets",
            )

        # Mount landmark SVGs/images
        _landmarks_dir = _frontend_dist / "landmarks"
        if _landmarks_dir.is_dir():
            app.mount(
                "/landmarks",
                StaticFiles(directory=str(_landmarks_dir)),
                name="static-landmarks",
            )

        # SPA fallback: serve index.html for all non-API, non-asset paths.
        # This catch-all route is registered AFTER the /api/v1 router,
        # but we must still guard against intercepting unknown /api/ paths
        # so that the API's own 404 behavior is preserved.
        from fastapi.responses import JSONResponse

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _serve_spa(full_path: str):
            # Let API 404s propagate — never serve HTML for /api/ paths
            if full_path.startswith("api/"):
                return JSONResponse(
                    {"detail": "Not Found"}, status_code=404
                )
            # If the request matches a real file in dist, serve it directly
            # (favicon.svg, robots.txt, manifest.json, etc.)
            file_path = _frontend_dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(str(file_path))
            # Otherwise serve index.html — React Router handles client routing
            return FileResponse(str(_frontend_dist / "index.html"))

    return app


# Module-level app instance for uvicorn
# Usage: uvicorn app.main:app --reload
app = create_app()
