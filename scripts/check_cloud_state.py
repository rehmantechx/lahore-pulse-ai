"""Check current Layerbase cloud database state."""
from __future__ import annotations
import sys
from pathlib import Path
import psycopg


def main() -> None:
    url = open(Path(__file__).resolve().parent.parent / ".layerbase_conn.txt").read().strip()
    print("Connecting to Layerbase via PostgreSQL wire protocol...")
    
    conn = psycopg.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    
    cur.execute("SELECT current_database(), version()")
    db, ver = cur.fetchone()
    print(f"Database: {db}")
    print(f"Server: {ver}")
    
    # pgsqlite uses SQLite under the hood - no pg_tables
    # Try sqlite_master instead, or just query information_schema
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
    except Exception:
        try:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            tables = [r[0] for r in cur.fetchall()]
        except Exception:
            tables = []
    
    print(f"\nTables ({len(tables)}): {tables}")
    
    for t in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            print(f"  {t}: {cur.fetchone()[0]:,} rows")
        except Exception as e:
            print(f"  {t}: ERROR counting rows: {e}")
    
    # Show columns via sqlite_master DDL
    print("\n--- Table schemas ---")
    for t in tables:
        try:
            cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'")
            row = cur.fetchone()
            if row:
                print(f"\n  {t}:")
                print(f"    {row[0][:300]}")
        except Exception as e:
            print(f"  {t}: ERROR: {e}")
    
    # Test: what happens with INSERT and URL values on the real data_sources table?
    print("\n--- Testing INSERT with CAST workaround ---")
    try:
        cur.execute(
            "INSERT INTO data_sources (source_id, name, provider, source_type, base_url, license, documentation_url, created_at) "
            "VALUES (CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT))",
            ("test_source_1", "Test Source", "test_provider", "api",
             "https://api.test.com", "MIT", "https://open-meteo.com",
             "2026-08-14 12:55:24")
        )
        cur.execute("SELECT * FROM data_sources WHERE source_id = CAST(%s AS TEXT)", ("test_source_1",))
        row = cur.fetchone()
        print(f"  CAST INSERT+SELECT OK: {row}")
        cur.execute("DELETE FROM data_sources WHERE source_id = CAST(%s AS TEXT)", ("test_source_1",))
        print(f"  Cleanup OK")
    except Exception as e:
        print(f"  CAST INSERT FAILED: {e}")
    
    # Test: executemany with CAST
    print("\n--- Testing executemany with CAST ---")
    try:
        test_rows = [
            ("test_src_a", "Test A", "prov", "api", "https://a.com", "MIT", "https://open-meteo.com", "2026-08-14 12:55:24"),
            ("test_src_b", "Test B", "prov", "api", "https://b.com", "MIT", "https://docs.test.org", "2026-08-15 10:00:00"),
        ]
        cur.executemany(
            "INSERT INTO data_sources (source_id, name, provider, source_type, base_url, license, documentation_url, created_at) "
            "VALUES (CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT), CAST(%s AS TEXT))",
            test_rows
        )
        cur.execute("SELECT COUNT(*) FROM data_sources")
        count = cur.fetchone()[0]
        print(f"  CAST executemany OK - {count} rows inserted")
        cur.execute("DELETE FROM data_sources WHERE source_id LIKE CAST(%s AS TEXT)", ("test_src_%",))
        print(f"  Cleanup OK")
    except Exception as e:
        print(f"  CAST executemany FAILED: {e}")
        try:
            cur.execute("DELETE FROM data_sources WHERE source_id LIKE CAST(%s AS TEXT)", ("test_src_%",))
        except:
            pass
    
    # Test: string parameter formatting as literal
    print("\n--- Testing String adapter approach ---")
    try:
        from psycopg.types.string import TextAdapter
        # Register adapter that forces text encoding
        psycopg.adapters.register_adapter(str, lambda x: TextAdapter(x, cur._conn))
        cur.execute(
            "INSERT INTO data_sources (source_id, name, provider, source_type, base_url, license, documentation_url, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            ("test_source_str", "Test Str", "prov", "api",
             "https://str.test.com", "MIT", "https://str-docs.test.org",
             "2026-08-14 12:55:24")
        )
        cur.execute("SELECT * FROM data_sources WHERE source_id = %s", ("test_source_str",))
        row = cur.fetchone()
        print(f"  TextAdapter INSERT+SELECT OK: {row}")
        cur.execute("DELETE FROM data_sources WHERE source_id = %s", ("test_source_str",))
        print(f"  Cleanup OK")
    except Exception as e:
        print(f"  TextAdapter approach FAILED: {e}")
        try:
            cur.execute("DELETE FROM data_sources WHERE source_id = %s", ("test_source_str",))
        except:
            pass
    
    # Test COPY capability
    print("\n--- Testing COPY capability ---")
    try:
        cur.execute("DROP TABLE IF EXISTS _copy_test")
        cur.execute("CREATE TABLE _copy_test (id TEXT, url TEXT, ts TEXT, val REAL)")
        
        with cur.copy("COPY _copy_test (id, url, ts, val) FROM STDIN") as copy:
            copy.write_row(("1", "https://open-meteo.com", "2026-08-14 12:55:24", 3.14))
            copy.write_row(("2", "https://example.com/path?q=hello", "2026-01-01 00:00:00", None))
        
        cur.execute("SELECT * FROM _copy_test ORDER BY id")
        for row in cur.fetchall():
            print(f"  COPY row: {row}")
        
        print("  COPY test PASSED - no TIMESTAMP inference issue!")
        cur.execute("DROP TABLE _copy_test")
    except Exception as e:
        print(f"  COPY test FAILED: {e}")
    
    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
