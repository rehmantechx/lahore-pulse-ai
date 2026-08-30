"""Phase 5.5 Query Diagnostics.

Tests different SQLite pragmas, indexes, and query plans to find
the root cause of the 15-17s query latency.
"""
from __future__ import annotations

import sqlite3
import time
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

DB_PATH = Path(__file__).resolve().parent / "data" / "lahore_pulse.db"


def get_required_params() -> list[str]:
    from app.modeling.models import WEATHER_FEATURES
    from app.modeling.dataset_loader import MISSING_PARAMS
    return (
        WEATHER_FEATURES
        + ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "ozone", "carbon_monoxide"]
        + MISSING_PARAMS
    )


def main():
    params = get_required_params()
    as_of = datetime.now(UTC)
    start = as_of - timedelta(hours=96)
    start_iso = start.isoformat()
    placeholders = ",".join(["?"] * len(params))

    sql_with_order = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND parameter IN ({placeholders})
        ORDER BY observed_at
    """
    sql_no_order = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND parameter IN ({placeholders})
    """
    params_list = [start_iso, *params]

    conn = sqlite3.connect(str(DB_PATH))

    # ── 1. Current state ──
    print("=" * 70)
    print("DIAGNOSTIC 1: Current query plan (before ANALYZE)")
    print("=" * 70)
    for label, sql in [("with_order", sql_with_order), ("no_order", sql_no_order)]:
        plan = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params_list).fetchall()
        print(f"\n  {label}:")
        for row in plan:
            print(f"    {row}")

    # ── 2. Run ANALYZE ──
    print("\n" + "=" * 70)
    print("DIAGNOSTIC 2: Running ANALYZE")
    print("=" * 70)
    t0 = time.perf_counter()
    conn.execute("ANALYZE")
    conn.commit()
    print(f"  ANALYZE took: {time.perf_counter() - t0:.2f}s")

    # Check stats
    try:
        stats = conn.execute("SELECT idx, stat FROM sqlite_stat1 WHERE tbl='observations'").fetchall()
        print("\n  Index statistics:")
        for idx, stat in stats:
            print(f"    {idx}: {stat}")
    except Exception as e:
        print(f"  Stats not available: {e}")

    # ── 3. Query plan after ANALYZE ──
    print("\n" + "=" * 70)
    print("DIAGNOSTIC 3: Query plan after ANALYZE")
    print("=" * 70)
    for label, sql in [("with_order", sql_with_order), ("no_order", sql_no_order)]:
        plan = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params_list).fetchall()
        print(f"\n  {label}:")
        for row in plan:
            print(f"    {row}")

    # ── 4. Test pragma variations ──
    print("\n" + "=" * 70)
    print("DIAGNOSTIC 4: PRAGMA variations")
    print("=" * 70)

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # Test cache_size
    print("\n  cache_size variations:")
    for cs in [-2000, -8000, -32000, -64000, -131072]:
        conn.execute(f"PRAGMA cache_size={cs}")
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            conn.execute(sql_with_order, params_list).fetchall()
            times.append(time.perf_counter() - t0)
        from statistics import median
        print(f"    cache_size={cs:>8}: median={median(times):.3f}s")

    # Test mmap
    print("\n  mmap_size variations:")
    for mm in [0, 67108864, 268435456, 1073741824]:
        conn.execute(f"PRAGMA mmap_size={mm}")
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            conn.execute(sql_with_order, params_list).fetchall()
            times.append(time.perf_counter() - t0)
        print(f"    mmap_size={mm:>12}: median={median(times):.3f}s")

    # Test temp_store
    print("\n  temp_store=MEMORY:")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-64000")
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        conn.execute(sql_with_order, params_list).fetchall()
        times.append(time.perf_counter() - t0)
    print(f"    temp_store=MEMORY + cache=-64000: median={median(times):.3f}s")

    # ── 5. Index impact ──
    print("\n" + "=" * 70)
    print("DIAGNOSTIC 5: Test new indexes")
    print("=" * 70)

    # Test a parameter-first composite index
    print("\n  Testing index (parameter, observed_at, value)...")
    t0 = time.perf_counter()
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_obs_test_param_time
        ON observations(parameter, observed_at, value)
    """)
    conn.commit()
    print(f"  Index creation: {time.perf_counter() - t0:.2f}s")

    # Check plan with new index
    plan = conn.execute(f"EXPLAIN QUERY PLAN {sql_with_order}", params_list).fetchall()
    print("  Plan with (parameter, observed_at, value):")
    for row in plan:
        print(f"    {row}")

    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        conn.execute(sql_with_order, params_list).fetchall()
        times.append(time.perf_counter() - t0)
    print(f"  Performance: median={median(times):.3f}s")

    # Drop test index
    conn.execute("DROP INDEX IF EXISTS idx_obs_test_param_time")
    conn.commit()

    # Test (observed_at DESC) for the ORDER BY
    print("\n  Testing index (observed_at DESC, parameter, value)...")
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_obs_test_time_desc
        ON observations(observed_at DESC, parameter, value)
    """)
    conn.commit()

    plan = conn.execute(f"EXPLAIN QUERY PLAN {sql_with_order}", params_list).fetchall()
    print("  Plan:")
    for row in plan:
        print(f"    {row}")

    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        conn.execute(sql_with_order, params_list).fetchall()
        times.append(time.perf_counter() - t0)
    print(f"  Performance: median={median(times):.3f}s")

    conn.execute("DROP INDEX IF EXISTS idx_obs_test_time_desc")
    conn.commit()

    # ── 6. Test: what if we read with a covering approach? ──
    print("\n" + "=" * 70)
    print("DIAGNOSTIC 6: Test parameter-by-parameter approach")
    print("=" * 70)

    # Instead of IN(...), try individual queries per parameter
    print("\n  Method: individual parameter queries + merge")
    t0 = time.perf_counter()
    all_rows = []
    conn2 = sqlite3.connect(str(DB_PATH))
    conn2.execute("PRAGMA cache_size=-64000")
    conn2.execute("PRAGMA temp_store=MEMORY")
    for p in params:
        rows = conn2.execute(
            "SELECT observed_at, parameter, value FROM observations WHERE observed_at >= ? AND parameter = ?",
            (start_iso, p)
        ).fetchall()
        all_rows.extend(rows)
    conn2.close()
    individual_time = time.perf_counter() - t0
    print(f"    Time: {individual_time:.3f}s  rows: {len(all_rows)}")

    # ── 7. Test: single-parameter IN with small set ──
    print("\n  Method: small IN clause (5 params at a time)")
    t0 = time.perf_counter()
    all_rows = []
    conn3 = sqlite3.connect(str(DB_PATH))
    conn3.execute("PRAGMA cache_size=-64000")
    for chunk_start in range(0, len(params), 5):
        chunk = params[chunk_start:chunk_start + 5]
        ph = ",".join(["?"] * len(chunk))
        sql_chunk = f"""
            SELECT observed_at, parameter, value
            FROM observations
            WHERE observed_at >= ? AND parameter IN ({ph})
        """
        rows = conn3.execute(sql_chunk, [start_iso, *chunk]).fetchall()
        all_rows.extend(rows)
    conn3.close()
    chunked_time = time.perf_counter() - t0
    print(f"    Time: {chunked_time:.3f}s  rows: {len(all_rows)}")

    # ── 8. Verify feature assembly still works ──
    print("\n" + "=" * 70)
    print("DIAGNOSTIC 7: Feature equivalence baseline")
    print("=" * 70)

    from app.modeling.serving.feature_assembly import assemble_prediction_features
    from app.modeling.serving.model_store import ModelStore

    MODELS_DIR = Path(__file__).resolve().parent / "data" / "models"
    store = ModelStore(MODELS_DIR)
    store.load_all()
    cached = store.get(6)
    feature_names = cached.metadata.feature_names

    result = assemble_prediction_features(
        db_path=DB_PATH,
        as_of=as_of,
        target_horizon=6,
        model_feature_names=feature_names,
    )
    print(f"  Features: {len(result.feature_row.columns)}")
    print(f"  Freshness: {result.freshness_hours:.2f}h")
    print(f"  Missing: {result.missing_features}")
    print(f"  PM2.5 lag_1h value: {result.feature_row['pm2_5_lag_1h'].iloc[0] if 'pm2_5_lag_1h' in result.feature_row.columns else 'N/A'}")

    # Save feature values for comparison later
    feature_values = result.feature_row.iloc[0].to_dict()
    import json
    with open("data/reports/baseline_features.json", "w") as f:
        # Convert non-serializable values
        serializable = {}
        for k, v in feature_values.items():
            try:
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                serializable[k] = float(v)
        json.dump(serializable, f, indent=2)
    print("  Saved baseline features to data/reports/baseline_features.json")

    # Save baseline prediction
    from app.modeling.serving.prediction_service import PredictionService
    service = PredictionService(model_store=store, db_path=str(DB_PATH), auto_load=False)
    result = service.predict(horizon=6, as_of=as_of, record_to_db=False)
    print(f"  Baseline prediction: {result.predicted_pm25:.6f}")
    with open("data/reports/baseline_prediction.json", "w") as f:
        json.dump({"predicted_pm25": result.predicted_pm25, "horizon": 6, "as_of": as_of.isoformat()}, f, indent=2)
    print("  Saved baseline prediction to data/reports/baseline_prediction.json")

    conn.close()
    print("\n" + "=" * 70)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
