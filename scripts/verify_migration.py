"""Verify local DB untouched + cloud DB data integrity sample."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DB = ROOT / "backend" / "data" / "lahore_pulse.db"
CONN_FILE = ROOT / ".layerbase_conn.txt"


def main() -> None:
    # ── Local DB intact? ───────────────────────────────────────────────
    print("── Local SQLite ──────────────────────────────")
    local = sqlite3.connect(f"file:{LOCAL_DB}?mode=ro", uri=True)
    size_mb = LOCAL_DB.stat().st_size / (1024 * 1024)
    print(f"  File: {LOCAL_DB}")
    print(f"  Size: {size_mb:,.1f} MB (should be ~1004.9 MB)")
    cur = local.execute("SELECT COUNT(*) FROM observations")
    print(f"  observations: {cur.fetchone()[0]:,}")
    cur = local.execute("SELECT COUNT(*) FROM data_sources")
    print(f"  data_sources: {cur.fetchone()[0]:,}")

    # ── Cloud DB samples ───────────────────────────────────────────────
    print("\n── Cloud Layerbase samples ────────────────────")
    url = CONN_FILE.read_text().strip()
    cloud = psycopg.connect(url)
    cloud.autocommit = True
    c = cloud.cursor()

    # Sample data_sources
    c.execute("SELECT source_id, name, provider, documentation_url FROM data_sources")
    for row in c.fetchall():
        print(f"  data_sources: {row}")

    # Sample observations (first 3)
    c.execute("SELECT observation_id, parameter, value, unit, observed_at, quality_status FROM observations LIMIT 3")
    for row in c.fetchall():
        print(f"  observation: {row}")

    # Sample prediction_records (first 3)
    c.execute("SELECT prediction_id, model_version, algorithm, predicted_value FROM prediction_records LIMIT 3")
    for row in c.fetchall():
        print(f"  prediction: {row}")

    # Check for any NULL documentation_url (should have data)
    c.execute("SELECT COUNT(*) FROM data_sources WHERE documentation_url IS NOT NULL")
    print(f"\n  data_sources with documentation_url: {c.fetchone()[0]}")

    # Check observation time range
    c.execute("SELECT MIN(observed_at), MAX(observed_at), COUNT(DISTINCT parameter) FROM observations")
    row = c.fetchone()
    print(f"  observations time range: {row[0]} to {row[1]}")
    print(f"  distinct parameters: {row[2]}")

    # Check for any obviously wrong data
    c.execute("SELECT COUNT(*) FROM observations WHERE value IS NULL")
    print(f"  observations with NULL value: {c.fetchone()[0]}")

    c.close()
    cloud.close()
    local.close()
    print("\n✅ Integrity check complete.")


if __name__ == "__main__":
    main()
