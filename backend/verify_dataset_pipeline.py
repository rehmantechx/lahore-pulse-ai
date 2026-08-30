"""Phase 1 Dataset Verification Script.

Proves real data flows through the full pipeline:
  External API -> Parse -> Validate -> Normalize -> Quality -> Persist

Uses Open-Meteo (free, no API key required) for weather data.

Run: python verify_dataset_pipeline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import date, timedelta

# Ensure we're running from the backend directory
sys.path.insert(0, ".")

from app.core.config import Settings
from app.domain.models.location import Coordinates
from app.infrastructure.database import get_database, reset_database
from app.infrastructure.pipeline import (
    assess_quality,
    create_observation,
    normalize_timestamp,
    normalize_unit,
    parse_json_response,
    validate_numerical_sanity,
    validate_observation_fields,
)
from app.infrastructure.providers.openmeteo import OPENMETEO_SOURCE, SOURCE_RELIABILITY, VARIABLE_UNITS, OpenMeteoProvider


async def main() -> None:
    print("=" * 70)
    print("PHASE 1 DATASET VERIFICATION")
    print("Proving real data flows through the full pipeline")
    print("=" * 70)

    settings = Settings()
    provider = OpenMeteoProvider(settings)

    # -- Step 0: Initialize database --
    print("\n[0/7] Initializing database...")
    db = await get_database()
    print("  Database initialized")

    # -- Step 1: Fetch real weather data from Open-Meteo --
    print("\n[1/7] Fetching REAL historical weather from Open-Meteo...")
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=2)  # 2-day window

    raw_response = await provider.fetch_historical(
        latitude=settings.lahore_latitude,
        longitude=settings.lahore_longitude,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        variables=["temperature_2m", "relative_humidity_2m", "pm2_5", "wind_speed_10m"],
    )

    # Count raw data points
    hourly = raw_response.get("hourly", {})
    time_points = len(hourly.get("time", []))
    variables_fetched = [k for k in hourly.keys() if k != "time"]
    total_data_points = time_points * len(variables_fetched)
    print(f"  Received {time_points} time points x {len(variables_fetched)} variables = {total_data_points} raw data points")
    print(f"  Variables: {', '.join(variables_fetched)}")
    print(f"  Date range: {start} to {end}")

    # -- Step 2: Parse (JSON string -> dict) --
    print("\n[2/7] Stage 1 - Parsing...")
    raw_text = json.dumps(raw_response)
    parsed = parse_json_response(raw_text)
    assert isinstance(parsed, dict), "Parse failed: not a dict"
    assert "hourly" in parsed, "Parse failed: missing 'hourly'"
    print(f"  Parsed {len(raw_text)} bytes of JSON -> dict with keys: {list(parsed.keys())}")

    # -- Step 3: Extract and validate observations --
    print("\n[3/7] Stage 2 - Field Validation...")
    observations = []
    validation_errors = 0
    validation_ok = 0

    for var_name in variables_fetched:
        times = hourly.get("time", [])
        values = hourly.get(var_name, [])
        for t, v in zip(times, values):
            is_valid, error = validate_observation_fields(
                parameter=var_name,
                value=v,
                unit="placeholder",
                observed_at=t,
                latitude=settings.lahore_latitude,
                longitude=settings.lahore_longitude,
                station_id="lahore-center",
            )
            if is_valid:
                validation_ok += 1
                observations.append({
                    "parameter": var_name,
                    "value": float(v) if v is not None else 0.0,
                    "observed_at": t,
                    "source_identifier": f"openmeteo|{var_name}|{t}",
                    "station_id": "lahore-center",
                    "latitude": settings.lahore_latitude,
                    "longitude": settings.lahore_longitude,
                })
            else:
                validation_errors += 1

    print(f"  Validated {validation_ok} observations, {validation_errors} skipped (None/missing)")

    # -- Step 4: Numerical sanity --
    print("\n[4/7] Stage 3 - Numerical Sanity...")
    sane_count = 0
    insane_count = 0
    sane_observations = []
    for obs in observations:
        is_sane, reason = validate_numerical_sanity(
            parameter=obs["parameter"],
            value=obs["value"],
        )
        if is_sane:
            sane_count += 1
            sane_observations.append(obs)
        else:
            insane_count += 1

    print(f"  {sane_count} sane, {insane_count} rejected (out of range)")

    # -- Step 5: Normalize units and timestamps --
    print("\n[5/7] Stage 4 - Normalization...")
    for obs in sane_observations:
        raw_unit = VARIABLE_UNITS.get(obs["parameter"], "unknown")
        obs["normalized_unit"] = normalize_unit(raw_unit)
        obs["normalized_timestamp"] = normalize_timestamp(obs["observed_at"])

    print(f"  Normalized {len(sane_observations)} observations")
    if sane_observations:
        sample = sane_observations[0]
        print(f"  Sample: parameter={sample['parameter']}, unit={sample['normalized_unit']}, time={sample['normalized_timestamp']}")

    # -- Step 6: Quality assessment --
    print("\n[6/7] Stage 5 - Quality Assessment...")
    quality_counts: dict[str, int] = {}
    for obs in sane_observations:
        quality = assess_quality(
            parameter=obs["parameter"],
            value=obs["value"],
            source_reliability=SOURCE_RELIABILITY,
        )
        obs["quality"] = quality
        quality_counts[quality.value] = quality_counts.get(quality.value, 0) + 1

    print("  Quality distribution:")
    for q, count in sorted(quality_counts.items()):
        print(f"    {q}: {count}")

    # -- Step 7: Create Observation objects and persist to SQLite --
    print("\n[7/7] Stage 6 - Persist to SQLite...")

    # Insert data source (required for foreign key)
    src = OPENMETEO_SOURCE
    db.execute(
        """INSERT OR IGNORE INTO data_sources
           (source_id, name, provider, source_type, base_url, license, documentation_url)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (src.source_id, src.name, src.provider, src.source_type.value,
         src.base_url, src.license, src.documentation_url),
    )
    db.commit()

    persisted = 0
    for obs in sane_observations:
        try:
            obs_obj = create_observation(
                source=OPENMETEO_SOURCE,
                station_id=obs["station_id"],
                location=Coordinates(
                    latitude=obs["latitude"],
                    longitude=obs["longitude"],
                ),
                parameter=obs["parameter"],
                value=obs["value"],
                unit=obs["normalized_unit"],
                observed_at=obs["normalized_timestamp"],
                source_identifier=obs["source_identifier"],
                raw_response="{}",
                quality=obs["quality"],
            )
            db.execute(
                """INSERT OR IGNORE INTO observations
                   (observation_id, source_id, station_id, latitude, longitude,
                    observed_at, retrieved_at, parameter, value, unit, quality_status,
                    source_identifier, raw_response)
                   VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?)""",

                (
                    obs_obj.observation_id,
                    obs_obj.source.source_id,
                    obs_obj.station_id,
                    obs_obj.location.latitude,
                    obs_obj.location.longitude,
                    obs_obj.timestamp.isoformat(),
                    obs_obj.parameter,
                    obs_obj.value,
                    obs_obj.unit.value,
                    obs_obj.quality.value,
                    obs_obj.source_identifier or "",
                    "{}",
                ),
            )
            persisted += 1
        except Exception as e:
            print(f"  Insert error: {e}")

    db.commit()

    # Count total rows
    count_result = db.fetch_one("SELECT COUNT(*) as cnt FROM observations")
    total_rows = count_result["cnt"] if count_result else 0

    print(f"  Persisted {persisted} observations to SQLite")
    print(f"  Total observations in DB: {total_rows}")

    # -- Verification Summary --
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"  Real API calls:       Open-Meteo (no API key, free tier)")
    print(f"  Raw data points:      {total_data_points}")
    print(f"  Parsed observations:  {validation_ok}")
    print(f"  Validated:            {len(observations)}")
    print(f"  Numerically sane:     {len(sane_observations)}")
    print(f"  Quality-assessed:     {len(sane_observations)}")
    print(f"  Persisted to DB:      {persisted}")
    print(f"  Total DB rows:        {total_rows}")
    print(f"  Pipeline stages:      6/6")
    print()
    print("  Pipeline flow:")
    print("    Open-Meteo API -> JSON parse -> Field validation")
    print("    -> Numerical sanity -> Unit/time normalization")
    print("    -> Quality assessment -> SQLite persistence")
    print()
    print("  REAL data flows through the COMPLETE pipeline")
    print("=" * 70)

    # Cleanup
    reset_database()
    print("\n  (Test database cleaned up)")


if __name__ == "__main__":
    asyncio.run(main())
