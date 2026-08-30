"""Phase 5.5 Baseline Benchmark.

Profiles the actual latency breakdown of the prediction pipeline.
Run this before making any changes to establish the baseline.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import pandas as pd

# Ensure we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

DB_PATH = Path(__file__).resolve().parent / "data" / "lahore_pulse.db"
MODELS_DIR = Path(__file__).resolve().parent / "data" / "models"


def get_required_params() -> list[str]:
    """Get the exact parameter list used by feature assembly."""
    from app.modeling.models import WEATHER_FEATURES
    from app.modeling.dataset_loader import MISSING_PARAMS
    return (
        WEATHER_FEATURES
        + ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "ozone", "carbon_monoxide"]
        + MISSING_PARAMS
    )


def bench_sql_only(db_path: Path, as_of: datetime, params: list[str], runs: int = 5) -> dict:
    """Benchmark: raw SQL query only."""
    lookback_hours = 96
    start_time = as_of - pd.Timedelta(hours=lookback_hours)
    start_iso = start_time.isoformat()
    placeholders = ",".join(["?"] * len(params))

    sql = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND parameter IN ({placeholders})
        ORDER BY observed_at
    """
    params_list = [start_iso, *params]

    times = []
    row_counts = []
    for _ in range(runs):
        t0 = time.perf_counter()
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(sql, params_list).fetchall()
        conn.close()
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        row_counts.append(len(rows))

    return {
        "metric": "sql_query",
        "runs": runs,
        "cold_s": round(times[0], 3),
        "median_s": round(median(times), 3),
        "min_s": round(min(times), 3),
        "max_s": round(max(times), 3),
        "avg_rows": int(median(row_counts)),
    }


def bench_sql_no_order(db_path: Path, as_of: datetime, params: list[str], runs: int = 5) -> dict:
    """Benchmark: SQL query without ORDER BY."""
    lookback_hours = 96
    start_time = as_of - pd.Timedelta(hours=lookback_hours)
    start_iso = start_time.isoformat()
    placeholders = ",".join(["?"] * len(params))

    sql = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND parameter IN ({placeholders})
    """
    params_list = [start_iso, *params]

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(sql, params_list).fetchall()
        conn.close()
        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    return {
        "metric": "sql_query_no_order",
        "runs": runs,
        "cold_s": round(times[0], 3),
        "median_s": round(median(times), 3),
        "min_s": round(min(times), 3),
        "max_s": round(max(times), 3),
    }


def bench_dataframe_pivot(db_path: Path, as_of: datetime, params: list[str], runs: int = 5) -> dict:
    """Benchmark: SQL + DataFrame construction + pivot."""
    lookback_hours = 96
    start_time = as_of - pd.Timedelta(hours=lookback_hours)
    start_iso = start_time.isoformat()
    placeholders = ",".join(["?"] * len(params))
    sql = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND parameter IN ({placeholders})
        ORDER BY observed_at
    """
    params_list = [start_iso, *params]

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(sql, params_list).fetchall()
        conn.close()
        # DataFrame construction
        df = pd.DataFrame(rows, columns=["observed_at", "parameter", "value"])
        df["time"] = pd.to_datetime(df["observed_at"], format="mixed", utc=True)
        df = df.set_index("time").sort_index()
        df = df.drop(columns=["observed_at"])
        if df.index.duplicated().any():
            df = df.groupby(["time", "parameter"])["value"].mean().reset_index()
            df = df.set_index("time").sort_index()
        wide = df.pivot(columns="parameter", values="value")
        if isinstance(wide.columns, pd.MultiIndex):
            wide.columns = wide.columns.get_level_values(-1)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    return {
        "metric": "sql_and_pivot",
        "runs": runs,
        "cold_s": round(times[0], 3),
        "median_s": round(median(times), 3),
        "min_s": round(min(times), 3),
        "max_s": round(max(times), 3),
    }


def bench_full_assembly(db_path: Path, as_of: datetime, horizon: int, runs: int = 3) -> dict:
    """Benchmark: full feature assembly pipeline."""
    from app.modeling.serving.feature_assembly import assemble_prediction_features
    from app.modeling.serving.model_store import ModelStore

    store = ModelStore(MODELS_DIR)
    store.load_all()
    cached = store.get(horizon)
    feature_names = cached.metadata.feature_names

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = assemble_prediction_features(
            db_path=db_path,
            as_of=as_of,
            target_horizon=horizon,
            model_feature_names=feature_names,
        )
        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    return {
        "metric": "full_assembly",
        "horizon": horizon,
        "runs": runs,
        "cold_s": round(times[0], 3),
        "median_s": round(median(times), 3),
        "min_s": round(min(times), 3),
        "max_s": round(max(times), 3),
        "feature_count": len(feature_names) if not result.feature_row.empty else 0,
    }


def bench_full_prediction(db_path: Path, as_of: datetime, horizon: int, runs: int = 3) -> dict:
    """Benchmark: end-to-end prediction."""
    from app.modeling.serving.model_store import ModelStore
    from app.modeling.serving.prediction_service import PredictionService

    store = ModelStore(MODELS_DIR)
    service = PredictionService(model_store=store, db_path=str(db_path), auto_load=True)

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = service.predict(horizon=horizon, as_of=as_of, record_to_db=False)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    return {
        "metric": "full_prediction",
        "horizon": horizon,
        "runs": runs,
        "cold_s": round(times[0], 3),
        "median_s": round(median(times), 3),
        "min_s": round(min(times), 3),
        "max_s": round(max(times), 3),
        "predicted_pm25": result.predicted_pm25,
    }


def bench_all_horizons(db_path: Path, as_of: datetime, runs: int = 2) -> dict:
    """Benchmark: predict_all_horizons (current sequential implementation)."""
    from app.modeling.serving.model_store import ModelStore
    from app.modeling.serving.prediction_service import PredictionService

    store = ModelStore(MODELS_DIR)
    service = PredictionService(model_store=store, db_path=str(db_path), auto_load=True)

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        results = service.predict_all_horizons(as_of=as_of, record_to_db=False)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)

    return {
        "metric": "all_horizons_sequential",
        "runs": runs,
        "cold_s": round(times[0], 3),
        "median_s": round(median(times), 3),
        "min_s": round(min(times), 3),
        "max_s": round(max(times), 3),
        "horizons_succeeded": sum(1 for r in results.values() if r.is_successful),
    }


def profile_sql_query_plan(db_path: Path, as_of: datetime, params: list[str]) -> dict:
    """Get the actual SQLite query plan."""
    lookback_hours = 96
    start_time = as_of - pd.Timedelta(hours=lookback_hours)
    start_iso = start_time.isoformat()
    placeholders = ",".join(["?"] * len(params))

    sql = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND parameter IN ({placeholders})
        ORDER BY observed_at
    """
    params_list = [start_iso, *params]

    conn = sqlite3.connect(str(db_path))
    # Get query plan
    plan_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params_list).fetchall()
    plan_text = [dict(row) if hasattr(row, 'keys') else str(row) for row in plan_rows]

    # Get table stats
    total_obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    obs_in_range = conn.execute(
        "SELECT COUNT(*) FROM observations WHERE observed_at >= ?",
        (start_iso,)
    ).fetchone()[0]
    param_counts = {}
    for p in params[:5]:  # sample first 5 params
        cnt = conn.execute(
            "SELECT COUNT(*) FROM observations WHERE observed_at >= ? AND parameter = ?",
            (start_iso, p)
        ).fetchone()[0]
        param_counts[p] = cnt

    # Check existing indexes
    indexes = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='observations'"
    ).fetchall()

    # Check pragmas
    pragmas = {}
    for pragma_name in ["journal_mode", "synchronous", "cache_size", "mmap_size", "page_size", "pages"]:
        row = conn.execute(f"PRAGMA {pragma_name}").fetchone()
        pragmas[pragma_name] = row[0] if row else None

    conn.close()

    return {
        "query_plan": plan_text,
        "total_observations": total_obs,
        "observations_in_range": obs_in_range,
        "param_counts_sample": param_counts,
        "indexes": [(name, sql) for name, sql in indexes],
        "pragmas": pragmas,
    }


def main():
    print("=" * 70)
    print("PHASE 5.5 BASELINE BENCHMARK")
    print("=" * 70)

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    # Use current time as reference
    as_of = datetime.now(UTC)
    params = get_required_params()
    print(f"\nReference time: {as_of.isoformat()}")
    print(f"Required parameters: {len(params)}")
    print(f"Database size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    results = []

    # 1. Query plan analysis
    print("\n--- Query Plan Analysis ---")
    plan = profile_sql_query_plan(DB_PATH, as_of, params)
    print(f"Total observations: {plan['total_observations']:,}")
    print(f"Observations in 96h window: {plan['observations_in_range']:,}")
    print(f"Sample param counts: {plan['param_counts_sample']}")
    print(f"\nIndexes on observations table:")
    for name, sql in plan['indexes']:
        print(f"  {name}: {sql}")
    print(f"\nQuery plan:")
    for row in plan['query_plan']:
        print(f"  {row}")
    print(f"\nSQLite pragmas: {plan['pragmas']}")
    results.append(("query_plan", plan))

    # 2. SQL query benchmark
    print("\n--- SQL Query Benchmark (with ORDER BY) ---")
    r = bench_sql_only(DB_PATH, as_of, params, runs=5)
    print(f"  Cold:  {r['cold_s']:.3f}s")
    print(f"  Median: {r['median_s']:.3f}s")
    print(f"  Min:   {r['min_s']:.3f}s")
    print(f"  Max:   {r['max_s']:.3f}s")
    print(f"  Rows:  {r['avg_rows']:,}")
    results.append(("sql_with_order", r))

    # 3. SQL without ORDER BY
    print("\n--- SQL Query Benchmark (NO ORDER BY) ---")
    r = bench_sql_no_order(DB_PATH, as_of, params, runs=5)
    print(f"  Cold:  {r['cold_s']:.3f}s")
    print(f"  Median: {r['median_s']:.3f}s")
    print(f"  Min:   {r['min_s']:.3f}s")
    print(f"  Max:   {r['max_s']:.3f}s")
    results.append(("sql_no_order", r))

    # 4. SQL + pivot
    print("\n--- SQL + DataFrame Pivot Benchmark ---")
    r = bench_dataframe_pivot(DB_PATH, as_of, params, runs=5)
    print(f"  Cold:  {r['cold_s']:.3f}s")
    print(f"  Median: {r['median_s']:.3f}s")
    print(f"  Min:   {r['min_s']:.3f}s")
    print(f"  Max:   {r['max_s']:.3f}s")
    results.append(("sql_and_pivot", r))

    # 5. Full assembly
    print("\n--- Full Feature Assembly Benchmark ---")
    r = bench_full_assembly(DB_PATH, as_of, horizon=6, runs=3)
    print(f"  Cold:  {r['cold_s']:.3f}s")
    print(f"  Median: {r['median_s']:.3f}s")
    print(f"  Min:   {r['min_s']:.3f}s")
    print(f"  Max:   {r['max_s']:.3f}s")
    print(f"  Features: {r['feature_count']}")
    results.append(("full_assembly", r))

    # 6. Full prediction
    print("\n--- Full Prediction Benchmark (horizon=6) ---")
    r = bench_full_prediction(DB_PATH, as_of, horizon=6, runs=3)
    print(f"  Cold:  {r['cold_s']:.3f}s")
    print(f"  Median: {r['median_s']:.3f}s")
    print(f"  Min:   {r['min_s']:.3f}s")
    print(f"  Max:   {r['max_s']:.3f}s")
    print(f"  PM2.5: {r['predicted_pm25']}")
    results.append(("full_prediction", r))

    # 7. All horizons
    print("\n--- All Horizons Benchmark (sequential) ---")
    r = bench_all_horizons(DB_PATH, as_of, runs=2)
    print(f"  Cold:  {r['cold_s']:.3f}s")
    print(f"  Median: {r['median_s']:.3f}s")
    print(f"  Min:   {r['min_s']:.3f}s")
    print(f"  Max:   {r['max_s']:.3f}s")
    print(f"  Horizons succeeded: {r['horizons_succeeded']}")
    results.append(("all_horizons", r))

    # Summary
    print("\n" + "=" * 70)
    print("BASELINE SUMMARY")
    print("=" * 70)
    for name, r in results:
        if isinstance(r, dict) and "median_s" in r:
            print(f"  {name:30s} median={r['median_s']:.3f}s  cold={r['cold_s']:.3f}s")
        elif isinstance(r, dict) and "observations_in_range" in r:
            print(f"  {name:30s} {r['observations_in_range']:,} rows in window")
    print("=" * 70)


if __name__ == "__main__":
    main()
