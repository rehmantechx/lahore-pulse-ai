"""Collect real historical data from Open-Meteo APIs.

This script fetches:
1. Weather data (16 hourly variables) from the Archive API
2. Air quality data (PM2.5, PM10, NO2, SO2, O3, CO) from the AQ API

for Lahore, Pakistan (31.5204°N, 74.3587°E).

Usage:
    cd backend
    python collect_real_data.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

# Ensure the app package is importable
sys.path.insert(0, ".")

from app.core.config import Settings
from app.infrastructure.database import Database
from app.modeling.collector import DataCollector


async def main() -> None:
    settings = Settings()
    # Database class expects a file path, not a sqlite:/// URL
    db_path = settings.database_url.replace("sqlite:///", "")
    db = Database(db_path)
    db.initialize()

    # Collect 60 days of historical data
    end_date = date.today() - timedelta(days=1)  # yesterday (today may be incomplete)
    start_date = end_date - timedelta(days=59)  # 60 days total

    print(f"=" * 70)
    print(f"Lahore Pulse AI — Real Data Collection")
    print(f"=" * 70)
    print(f"Location: Lahore ({settings.lahore_latitude}, {settings.lahore_longitude})")
    print(f"Date range: {start_date} → {end_date} (60 days)")
    print(f"Database: {settings.database_url}")
    print()

    collector = DataCollector(settings, db)

    # 1. Weather data
    print("─" * 40)
    print("Step 1: Collecting weather data...")
    try:
        weather_count = await collector.collect_weather_data(start_date, end_date)
        print(f"  ✅ Weather observations persisted: {weather_count:,}")
    except Exception as e:
        print(f"  ❌ Weather collection failed: {e}")
        weather_count = 0

    # 2. Air quality data
    print("─" * 40)
    print("Step 2: Collecting air quality data (PM2.5, PM10, etc.)...")
    try:
        aq_count = await collector.collect_aq_data(start_date, end_date)
        print(f"  ✅ AQ observations persisted: {aq_count:,}")
    except Exception as e:
        print(f"  ❌ AQ collection failed: {e}")
        aq_count = 0

    # 3. Summary
    print("─" * 40)
    print(f"Summary:")
    print(f"  Weather observations: {weather_count:,}")
    print(f"  AQ observations:      {aq_count:,}")
    print(f"  Total new:            {weather_count + aq_count:,}")

    # 4. Verify database state
    print()
    print("─" * 40)
    print("Verifying database state...")
    rows = db.fetch_all(
        "SELECT parameter, COUNT(*), MIN(observed_at), MAX(observed_at) "
        "FROM observations GROUP BY parameter ORDER BY parameter"
    )
    if rows:
        for row in rows:
            print(f"  {row['parameter']}: {row['COUNT(*)']:,} obs "
                  f"({row['MIN(observed_at)']} → {row['MAX(observed_at)']})")
    else:
        print("  No observations found")

    total = db.fetch_one("SELECT COUNT(*) as cnt FROM observations")
    print(f"\n  Total observations in DB: {total['cnt']:,}")

    db.close()
    print(f"\n{'=' * 70}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
