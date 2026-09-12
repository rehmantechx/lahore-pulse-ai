"""Quick check: row counts for every table in the local SQLite DB."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "backend" / "data" / "lahore_pulse.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()]
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
    print(f"  {t:30s} {count:>12,}")
conn.close()
