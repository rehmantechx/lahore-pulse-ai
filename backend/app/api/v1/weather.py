"""Weather API endpoint.

Returns the most recent real weather observations from the database.
Data originates from Open-Meteo (ECMWF IFS 9km reanalysis) and is
ingested via the standard data pipeline — no external API calls at
request time.

Endpoints:
    GET /api/v1/weather/current
        → Latest temperature, humidity, wind, PM10, etc.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...infrastructure.database import get_database

router = APIRouter(prefix="/weather", tags=["weather"])

# Weather parameters to return, mapped to friendly output names
_WEATHER_PARAMS = {
    "temperature_2m": "temperature",
    "relative_humidity_2m": "humidity",
    "wind_speed_10m": "wind_speed",
    "wind_direction_10m": "wind_direction",
    "dew_point_2m": "dew_point",
    "cloud_cover": "cloud_cover",
    "apparent_temperature": "apparent_temperature",
    "precipitation": "precipitation",
    "pressure_msl": "pressure",
}


@router.get(
    "/current",
    summary="Get current weather",
    description=(
        "Returns the most recent weather observations stored in the "
        "database. All values come from the Open-Meteo ingestion "
        "pipeline — no synthetic or hardcoded data."
    ),
)
async def get_current_weather() -> dict:
    """Get latest real weather observations from the database.

    Returns temperature, humidity, wind speed/direction, and other
    weather variables from the most recent Open-Meteo observation.
    """
    db = await get_database()

    weather: dict = {}
    for db_param, output_key in _WEATHER_PARAMS.items():
        row = db.fetch_one(
            """SELECT value, unit, observed_at
               FROM observations
               WHERE parameter = ?
               ORDER BY observed_at DESC
               LIMIT 1""",
            (db_param,),
        )
        if row:
            weather[output_key] = {
                "value": row["value"],
                "unit": row["unit"],
                "observed_at": row["observed_at"],
            }
        else:
            weather[output_key] = None

    # Also get PM10 for the selected location context
    pm10_row = db.fetch_one(
        """SELECT value, unit, observed_at
           FROM observations
           WHERE parameter = 'pm10'
           ORDER BY observed_at DESC
           LIMIT 1""",
    )
    weather["pm10"] = (
        {"value": pm10_row["value"], "unit": pm10_row["unit"], "observed_at": pm10_row["observed_at"]}
        if pm10_row
        else None
    )

    return {"weather": weather}
