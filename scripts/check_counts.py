"""Quick check of cloud DB row counts."""
from __future__ import annotations
import sys
from pathlib import Path
import psycopg

url = open(Path(__file__).resolve().parent.parent / ".layerbase_conn.txt").read().strip()
c = psycopg.connect(url)
c.autocommit = True
cur = c.cursor()

tables = [
    "data_sources", "ingestion_runs", "stations", "observations",
    "ingestion_records", "alert_preferences", "alert_history",
    "report_history", "saved_locations", "prediction_records",
    "verification_outcomes",
]
total = 0
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    n = cur.fetchone()[0]
    total += n
    print(f"  {t:30s} {n:>10,}")
print(f"  {'TOTAL':30s} {total:>10,}")

cur.close()
c.close()
