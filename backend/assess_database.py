"""Database assessment script — Phase 3 baseline.

Calculates actual data metrics from the real database.
No synthetic data, no estimates — real values only.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/lahore_pulse.db")


def main() -> None:
    if not DB_PATH.exists():
        print("ERROR: Database does not exist at", DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ── Total observations ────────────────────────────────────────
    row = conn.execute("SELECT COUNT(*) as cnt FROM observations").fetchone()
    total = row["cnt"]
    print(f"Total observations: {total:,}")

    # ── By parameter ──────────────────────────────────────────────
    print("\n=== By Parameter ===")
    for r in conn.execute(
        """SELECT parameter, COUNT(*) as cnt,
           MIN(observed_at) as earliest, MAX(observed_at) as latest,
           COUNT(DISTINCT substr(observed_at, 1, 7)) as months
           FROM observations GROUP BY parameter ORDER BY parameter"""
    ):
        print(
            f"  {r['parameter']}: {r['cnt']:,} records, "
            f"{r['months']} months ({r['earliest']} to {r['latest']})"
        )

    # ── By source ─────────────────────────────────────────────────
    print("\n=== By Source ===")
    for r in conn.execute(
        "SELECT source_id, COUNT(*) as cnt FROM observations GROUP BY source_id"
    ):
        print(f"  {r['source_id']}: {r['cnt']:,}")

    # ── Date range ────────────────────────────────────────────────
    print("\n=== Date Range ===")
    r = conn.execute(
        "SELECT MIN(observed_at) as earliest, MAX(observed_at) as latest FROM observations"
    ).fetchone()
    print(f"  Earliest: {r['earliest']}")
    print(f"  Latest:   {r['latest']}")

    # ── Stations ──────────────────────────────────────────────────
    print("\n=== Stations ===")
    for r in conn.execute(
        "SELECT station_id, name, latitude, longitude FROM stations"
    ):
        print(f"  {r['station_id']}: {r['name']} ({r['latitude']}, {r['longitude']})")
    station_count = conn.execute("SELECT COUNT(*) as cnt FROM stations").fetchone()["cnt"]
    if station_count == 0:
        print("  (none — grid-cell data only)")

    # ── Data sources ──────────────────────────────────────────────
    print("\n=== Data Sources ===")
    for r in conn.execute(
        "SELECT source_id, name, provider, source_type FROM data_sources"
    ):
        print(f"  {r['source_id']}: {r['name']} ({r['provider']}, {r['source_type']})")

    # ── Ingestion runs ────────────────────────────────────────────
    print("\n=== Ingestion Runs ===")
    for r in conn.execute(
        """SELECT run_id, provider, operation, status,
           records_received, records_accepted, records_rejected,
           records_duplicated, started_at, finished_at
           FROM ingestion_runs ORDER BY started_at"""
    ):
        print(
            f"  {r['run_id'][:8]}... {r['provider']}/{r['operation']}: "
            f"{r['status']} (received={r['records_received']}, "
            f"accepted={r['records_accepted']}, rejected={r['records_rejected']}, "
            f"duplicated={r['records_duplicated']})"
        )

    # ── Monthly coverage ──────────────────────────────────────────
    print("\n=== Monthly Coverage ===")
    for r in conn.execute(
        """SELECT substr(observed_at, 1, 7) as month,
           COUNT(*) as cnt,
           COUNT(DISTINCT parameter) as params,
           MIN(observed_at) as first_obs,
           MAX(observed_at) as last_obs
           FROM observations
           GROUP BY month ORDER BY month"""
    ):
        print(
            f"  {r['month']}: {r['cnt']:,} records, "
            f"{r['params']} parameters "
            f"({r['first_obs'][:10]} to {r['last_obs'][:10]})"
        )

    # ── Hourly coverage per day ───────────────────────────────────
    print("\n=== Daily Coverage ===")
    for r in conn.execute(
        """SELECT substr(observed_at, 1, 10) as day,
           COUNT(*) as records,
           COUNT(DISTINCT parameter) as params
           FROM observations
           GROUP BY day ORDER BY day"""
    ):
        print(f"  {r['day']}: {r['records']:,} records, {r['params']} params")

    # ── Duplicate check ───────────────────────────────────────────
    print("\n=== Duplicate Check ===")
    r = conn.execute(
        """SELECT COUNT(*) as total,
           COUNT(DISTINCT source_id || '|' || COALESCE(station_id, '') || '|' || parameter || '|' || observed_at) as unique_records
           FROM observations"""
    ).fetchone()
    print(f"  Total rows: {r['total']:,}")
    print(f"  Unique key combinations: {r['unique_records']:,}")
    print(f"  Duplicates: {r['total'] - r['unique_records']:,}")

    # ── Missing/null values in raw_response ───────────────────────
    print("\n=== Raw Response Availability ===")
    r = conn.execute(
        """SELECT
           COUNT(*) as total,
           SUM(CASE WHEN raw_response IS NOT NULL THEN 1 ELSE 0 END) as with_raw,
           SUM(CASE WHEN raw_response IS NULL THEN 1 ELSE 0 END) as without_raw
           FROM observations"""
    ).fetchone()
    print(f"  With raw_response: {r['with_raw']:,}")
    print(f"  Without raw_response: {r['without_raw']:,}")

    # ── Quality status distribution ───────────────────────────────
    print("\n=== Quality Status Distribution ===")
    for r in conn.execute(
        "SELECT quality_status, COUNT(*) as cnt FROM observations GROUP BY quality_status"
    ):
        print(f"  {r['quality_status']}: {r['cnt']:,}")

    # ── Geographic coverage ───────────────────────────────────────
    print("\n=== Geographic Coverage ===")
    r = conn.execute(
        """SELECT MIN(latitude) as min_lat, MAX(latitude) as max_lat,
           MIN(longitude) as min_lon, MAX(longitude) as max_lon,
           COUNT(DISTINCT latitude || ',' || longitude) as unique_locations
           FROM observations"""
    ).fetchone()
    print(f"  Latitude range:  {r['min_lat']} to {r['max_lat']}")
    print(f"  Longitude range: {r['min_lon']} to {r['max_lon']}")
    print(f"  Unique grid points: {r['unique_locations']}")

    # ── DB file size ──────────────────────────────────────────────
    print(f"\n=== Database Size ===")
    print(f"  {DB_PATH}: {DB_PATH.stat().st_size / 1024:.1f} KB")

    conn.close()
    print("\n=== Assessment Complete ===")


if __name__ == "__main__":
    main()
