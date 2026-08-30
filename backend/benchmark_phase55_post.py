"""Phase 5.5 post-optimization benchmark.

Measures latency after all optimizations:
  - ANALYZE statistics
  - Read-optimized PRAGMAs
  - Connection reuse
  - Observation caching
  - Multi-horizon shared feature assembly

Compare against baseline numbers from benchmark_phase55.py:
  - Baseline SQL:     17.6s
  - Baseline pivot:   18.3s
  - Baseline full:    18.6s
  - Baseline all-horizon: 89.4s
"""

from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

# ── Configuration ─────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "lahore_pulse.db"
REPORTS_DIR = DATA_DIR / "reports"
MODELS_DIR = DATA_DIR / "models"

ITERATIONS = 5
HORIZONS = [1, 3, 6, 12, 24]


def benchmark():
    from app.modeling.serving.feature_assembly import (
        _load_recent_observations,
        _align_to_hourly,
        assemble_features,
        assemble_prediction_features,
        assemble_shared_features,
        _observation_cache,
    )
    from app.modeling.serving.model_store import ModelStore
    from app.modeling.serving.prediction_service import PredictionService

    print("=" * 70)
    print("PHASE 5.5 POST-OPTIMIZATION BENCHMARK")
    print("=" * 70)

    as_of = datetime.now(UTC)

    # ── 1. SQL query benchmark ────────────────────────────────────
    print("\n--- BENCHMARK 1: SQL Query Latency ---")
    _observation_cache.invalidate()
    sql_times = []
    for i in range(ITERATIONS):
        _observation_cache.invalidate()
        t0 = time.perf_counter()
        df = _load_recent_observations(DB_PATH, as_of, use_cache=False)
        elapsed = time.perf_counter() - t0
        sql_times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s  rows={len(df)}")

    sql_median = statistics.median(sql_times)
    print(f"  Median: {sql_median:.3f}s")
    print(f"  Baseline was: 17.6s → improvement: {17.6/sql_median:.0f}x")

    # ── 2. Pivot + alignment benchmark ────────────────────────────
    print("\n--- BENCHMARK 2: Pivot + Alignment ---")
    _observation_cache.invalidate()
    pivot_times = []
    for i in range(ITERATIONS):
        _observation_cache.invalidate()
        raw = _load_recent_observations(DB_PATH, as_of, use_cache=False)
        t0 = time.perf_counter()
        aligned = _align_to_hourly(raw)
        elapsed = time.perf_counter() - t0
        pivot_times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s")

    pivot_median = statistics.median(pivot_times)
    print(f"  Median: {pivot_median:.3f}s")

    # ── 3. Full prediction benchmark ──────────────────────────────
    print("\n--- BENCHMARK 3: Single-Horizon Prediction ---")
    _observation_cache.invalidate()
    pred_times = []
    for i in range(ITERATIONS):
        _observation_cache.invalidate()
        store = ModelStore(MODELS_DIR)
        service = PredictionService(
            model_store=store,
            db_path=DB_PATH,
            auto_load=True,
        )
        t0 = time.perf_counter()
        result = service.predict(horizon=6, as_of=as_of, record_to_db=False)
        elapsed = time.perf_counter() - t0
        pred_times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s  pm25={result.predicted_pm25:.2f}")

    pred_median = statistics.median(pred_times)
    print(f"  Median: {pred_median:.3f}s")
    print(f"  Baseline was: 18.6s → improvement: {18.6/pred_median:.0f}x")
    print(f"  Target: <5s → {'PASS' if pred_median < 5 else 'FAIL'}")

    # ── 4. All-horizon prediction benchmark ───────────────────────
    print("\n--- BENCHMARK 4: All-Horizon Prediction ---")
    all_times = []
    for i in range(ITERATIONS):
        _observation_cache.invalidate()
        store = ModelStore(MODELS_DIR)
        service = PredictionService(
            model_store=store,
            db_path=DB_PATH,
            auto_load=True,
        )
        t0 = time.perf_counter()
        results = service.predict_all_horizons(as_of=as_of, record_to_db=False)
        elapsed = time.perf_counter() - t0
        all_times.append(elapsed)
        successful = sum(1 for r in results.values() if r.is_successful)
        print(f"  Run {i+1}: {elapsed:.3f}s  successful={successful}/5")

    all_median = statistics.median(all_times)
    print(f"  Median: {all_median:.3f}s")
    print(f"  Baseline was: 89.4s → improvement: {89.4/all_median:.0f}x")
    print(f"  Target: <15s → {'PASS' if all_median < 15 else 'FAIL'}")

    # ── 5. Cache effectiveness benchmark ──────────────────────────
    print("\n--- BENCHMARK 5: Cache Effectiveness ---")
    _observation_cache.invalidate()

    # Cold: first call
    t0 = time.perf_counter()
    _load_recent_observations(DB_PATH, as_of, use_cache=True)
    cold_time = time.perf_counter() - t0

    # Warm: second call (cached)
    t0 = time.perf_counter()
    _load_recent_observations(DB_PATH, as_of, use_cache=True)
    warm_time = time.perf_counter() - t0

    print(f"  Cold (no cache): {cold_time:.3f}s")
    print(f"  Warm (cached):   {warm_time:.3f}s")
    print(f"  Cache speedup:   {cold_time/warm_time:.0f}x")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<35} {'Before':>10} {'After':>10} {'Speedup':>10}")
    print("-" * 70)
    print(f"{'SQL query (median)':<35} {'17.6s':>10} {sql_median:>9.3f}s {17.6/sql_median:>9.0f}x")
    print(f"{'Single prediction (median)':<35} {'18.6s':>10} {pred_median:>9.3f}s {18.6/pred_median:>9.0f}x")
    print(f"{'All-horizon (median)':<35} {'89.4s':>10} {all_median:>9.3f}s {89.4/all_median:>9.0f}x")
    print(f"{'Cache hit (warm)':<35} {'N/A':>10} {warm_time:>9.3f}s {'N/A':>10}")
    print("-" * 70)
    print(f"{'Target: single <5s':<35} {'':>10} {'PASS' if pred_median < 5 else 'FAIL':>10}")
    print(f"{'Target: all-horizon <15s':<35} {'':>10} {'PASS' if all_median < 15 else 'FAIL':>10}")
    print("=" * 70)

    # Save results
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "benchmark": "phase55_post_optimization",
        "iterations": ITERATIONS,
        "results": {
            "sql_query_median_s": round(sql_median, 4),
            "pivot_median_s": round(pivot_median, 4),
            "single_prediction_median_s": round(pred_median, 4),
            "all_horizon_median_s": round(all_median, 4),
            "cache_cold_s": round(cold_time, 4),
            "cache_warm_s": round(warm_time, 4),
        },
        "baseline": {
            "sql_query_s": 17.6,
            "single_prediction_s": 18.6,
            "all_horizon_s": 89.4,
        },
        "targets": {
            "single_prediction_under_5s": pred_median < 5,
            "all_horizon_under_15s": all_median < 15,
        },
    }
    report_path = REPORTS_DIR / "phase55_benchmark_results.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nResults saved to {report_path}")


if __name__ == "__main__":
    benchmark()
