"""Data sources API endpoints.

Lists registered data sources and their health status.
Phase 1: Read-only, no CRUD operations.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/data-sources", tags=["data-sources"])

# ── Registered Data Sources (Phase 1) ─────────────────────────────────

REGISTERED_SOURCES = [
    {
        "source_id": "openmeteo",
        "name": "Open-Meteo",
        "type": "weather",
        "provider": "Open-Meteo GmbH",
        "base_url": "https://open-meteo.com",
        "license": "CC-BY 4.0",
        "reliability": 5,
        "capabilities": ["historical_weather", "weather_forecast", "air_quality"],
        "status": "registered",
    },
    {
        "source_id": "openaq",
        "name": "OpenAQ",
        "type": "air_quality",
        "provider": "OpenAQ",
        "base_url": "https://api.openaq.org",
        "license": "OpenAQ Terms of Use",
        "reliability": 4,
        "capabilities": ["historical_measurements", "station_discovery"],
        "status": "registered",
    },
    {
        "source_id": "aqicn",
        "name": "WAQI / AQICN",
        "type": "air_quality",
        "provider": "World Air Quality Index Project",
        "base_url": "https://api.waqi.info",
        "license": "CC BY-NC-SA 2.5",
        "reliability": 3,
        "capabilities": ["realtime_feed", "station_search"],
        "status": "registered",
    },
]


@router.get("")
async def list_data_sources() -> dict:
    """List all registered data sources.

    Returns a list of all data sources that the system can ingest from.
    Each entry includes metadata about the source, its capabilities,
    and its current registration status.
    """
    return {
        "sources": REGISTERED_SOURCES,
        "count": len(REGISTERED_SOURCES),
    }


@router.get("/{source_id}")
async def get_data_source(source_id: str) -> dict:
    """Get details of a specific data source.

    Args:
        source_id: The source identifier (e.g., 'openmeteo', 'openaq', 'aqicn').
    """
    for source in REGISTERED_SOURCES:
        if source["source_id"] == source_id:
            return {"source": source}
    return {"error": f"Data source '{source_id}' not found", "sources": REGISTERED_SOURCES}
