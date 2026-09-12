"""Feature assembly — constructs real-time features from the database.

At prediction time we must build the exact same feature vector the
model was trained on, using only data available at the current moment.
This module reuses the authoritative feature-engineering functions
from app.modeling.models (lags, rolling, temporal, derived) but
reads the raw data from SQLite rather than from the full training set.

Design principles:
    - Reuses existing feature pipeline — no new feature code
    - Only reads real data from the database
    - Honest about data freshness: reports gaps, staleness, coverage
    - Fails loudly if required features cannot be constructed
    - No imputation of the target variable (PM2.5)

Performance (Phase 5.5):
    - Reads only required parameters (not all columns)
    - Uses a bounded in-process observation cache (TTL 60s)
    - Connection uses read-optimized PRAGMAs (cache_size, mmap, temp_store)
    - ANALYZE must have been run on the DB for optimal query planning
"""

from __future__ import annotations

import sqlite3
import threading
import time as _time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from ...core.db import get_db_connection, is_cloud_db

from ..dataset_loader import OVERLAP_START, MISSING_PARAMS
from ..models import (
    TARGET_LAGS,
    TARGET_ROLLING_OPS,
    TARGET_ROLLING_WINDOWS,
    WEATHER_FEATURES,
    WEATHER_ROLLING_OPS,
    WEATHER_ROLLING_WINDOWS,
    build_derived_features,
    build_target_lags,
    build_target_rolling,
    build_temporal_features,
    build_weather_rolling,
    get_feature_columns,
)


# ── Configuration ─────────────────────────────────────────────────

# Maximum lookback in hours needed to build all features.
# Lags go up to 72h, so we need at least 73h of data (72 + current).
LOOKBACK_HOURS = 96  # 72h lag + 24h margin

# Data freshness thresholds
STALENESS_WARNING_HOURS = 6  # Warn if latest obs is older than this
STALENESS_CRITICAL_HOURS = 12  # Error if latest obs is older than this

# Observation cache configuration
_OBS_CACHE_TTL_S = 60.0  # Cache valid for 60 seconds
_OBS_CACHE_MAX_ENTRIES = 4  # Bounded: hold at most 4 recent windows


# ── Read-Optimised SQLite Connection ──────────────────────────────


def _get_read_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open a read-optimized connection (SQLite or PostgreSQL).

    PRAGMA rationale (SQLite only):
    - cache_size=-64000: 64 MB page cache (default 2 MB is too small)
    - temp_store=MEMORY: avoids disk spills for ORDER BY / GROUP BY
    - mmap_size=268435456: 256 MB memory-mapped I/O for large reads
    - journal_mode=WAL: safe for concurrent readers
    - synchronous=NORMAL: acceptable durability for read-only queries
    """
    if is_cloud_db():
        return get_db_connection(read_only=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


# ── In-Process Observation Cache ──────────────────────────────────


class _ObservationCache:
    """Bounded in-process cache for recent observation DataFrames.

    Caches the aligned wide-format DataFrame keyed by the
    (db_path, hour-truncated as_of, lookback_hours) tuple.
    This avoids re-querying the database when multiple horizons
    share the same underlying observation window.

    Safety:
    - TTL-based expiry (default 60s)
    - Bounded entry count (default 4)
    - Thread-safe via lock
    - Never bypasses freshness checks (freshness is checked downstream)
    """

    def __init__(self, ttl_s: float = _OBS_CACHE_TTL_S, max_entries: int = _OBS_CACHE_MAX_ENTRIES):
        self._ttl_s = ttl_s
        self._max_entries = max_entries
        self._cache: dict[tuple, tuple[float, pd.DataFrame]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple) -> pd.DataFrame | None:
        """Return cached DataFrame if valid, else None."""
        with self._lock:
            if key in self._cache:
                ts, df = self._cache[key]
                if _time.monotonic() - ts < self._ttl_s:
                    logger.debug("Observation cache hit", key=str(key)[:80])
                    return df
                # Expired — remove
                del self._cache[key]
        return None

    def put(self, key: tuple, df: pd.DataFrame) -> None:
        """Cache a DataFrame with current timestamp."""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_entries:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest_key]
            self._cache[key] = (_time.monotonic(), df)

    def invalidate(self) -> None:
        """Clear the entire cache (e.g., after new data arrives)."""
        with self._lock:
            self._cache.clear()
            logger.debug("Observation cache invalidated")


_observation_cache = _ObservationCache()


# ── Data structures ───────────────────────────────────────────────


@dataclass
class FeatureAssemblyResult:
    """Result of feature assembly for a single prediction timestamp.

    Attributes:
        timestamp: The prediction target timestamp.
        feature_row: Single-row DataFrame with all features.
        data_timestamp: When the most recent observation used was.
        freshness_hours: Hours between latest observation and prediction time.
        raw_observations_used: Number of raw DB rows loaded.
        missing_features: Features that could not be constructed.
        warnings: Human-readable freshness/coverage warnings.
        horizon: Forecast horizon in hours (set during multi-horizon assembly).
    """

    timestamp: datetime
    feature_row: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    data_timestamp: datetime | None = None
    freshness_hours: float = 0.0
    raw_observations_used: int = 0
    missing_features: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    horizon: int = 0

    @property
    def is_usable(self) -> bool:
        """True if the feature row is non-empty and has no critical missing features."""
        return (
            not self.feature_row.empty
            and len(self.missing_features) == 0
        )


# ── Database Reading ──────────────────────────────────────────────


def _load_recent_observations(
    db_path: str | Path | None,
    as_of: datetime,
    lookback_hours: int = LOOKBACK_HOURS,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Load recent observations from the database as a wide-format DataFrame.

    Uses a bounded in-process cache to avoid re-querying the database
    when multiple horizons share the same observation window.

    Args:
        db_path: SQLite file path or None (cloud mode uses LAYERBASE_DB_URL).
        as_of: Reference timestamp (prediction time).
        lookback_hours: How many hours of history to load.
        use_cache: Whether to use the observation cache.

    Returns:
        Wide-format DataFrame with DatetimeIndex (UTC) and one column
        per parameter.
    """
    is_cloud = is_cloud_db()
    if not is_cloud:
        db_path = Path(db_path)
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

    # Truncate as_of to the hour for cache key stability
    as_of_hour = as_of.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    cache_key = ("cloud" if is_cloud else str(db_path), as_of_hour.isoformat(), lookback_hours)

    # Check cache
    if use_cache:
        cached = _observation_cache.get(cache_key)
        if cached is not None:
            return cached.copy()

    start_time = as_of - timedelta(hours=lookback_hours)
    start_iso = start_time.isoformat()

    # Parameters we need for features (19 stored params + 3 missing = 22)
    all_params = (
        WEATHER_FEATURES
        + ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "ozone", "carbon_monoxide"]
        + MISSING_PARAMS
    )
    placeholders = ",".join(["?"] * len(all_params))

    sql = f"""
        SELECT observed_at, parameter, value
        FROM observations
        WHERE observed_at >= ?
        AND observed_at <= ?
        AND parameter IN ({placeholders})
        ORDER BY observed_at
    """

    conn = _get_read_connection(db_path)
    try:
        # Upper bound: as_of + 1h margin to avoid future forecast data
        end_iso = (as_of + timedelta(hours=1)).isoformat()
        rows = conn.execute(sql, [start_iso, end_iso, *all_params]).fetchall()
    finally:
        conn.close()

    if not rows:
        logger.warning("No observations found for feature assembly", start=start_iso)
        return pd.DataFrame()

    # Build wide-format DataFrame efficiently
    # Unpack directly into arrays to avoid intermediate DataFrame
    times_raw = [r[0] for r in rows]
    params_raw = [r[1] for r in rows]
    values_raw = [r[2] for r in rows]

    df = pd.DataFrame({
        "time": pd.to_datetime(times_raw, format="mixed", utc=True),
        "parameter": params_raw,
        "value": values_raw,
    })
    df = df.set_index("time").sort_index()

    # Handle duplicates
    if df.index.duplicated().any():
        df = df.groupby(["time", "parameter"])["value"].mean().reset_index()
        df = df.set_index("time").sort_index()

    # Pivot to wide format
    wide = df.pivot(columns="parameter", values="value")
    if isinstance(wide.columns, pd.MultiIndex):
        wide.columns = wide.columns.get_level_values(-1)

    # Add missing parameters as NaN
    for p in MISSING_PARAMS:
        if p not in wide.columns:
            wide[p] = np.nan

    # Cache the result
    if use_cache:
        _observation_cache.put(cache_key, wide)

    logger.info(
        "Recent observations loaded",
        rows=len(wide),
        parameters=len(wide.columns),
        start=str(start_time),
        end=str(as_of),
    )
    return wide


def _align_to_hourly(df: pd.DataFrame, max_gap_hours: int = 3) -> pd.DataFrame:
    """Resample to hourly UTC grid with forward-fill for short gaps."""
    if df.empty:
        return df

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    full_range = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="1h",
        tz="UTC",
    )
    aligned = df.reindex(full_range)
    aligned.index.name = "time"
    aligned = aligned.ffill(limit=max_gap_hours)
    return aligned


# ── Feature Construction ──────────────────────────────────────────


def assemble_features(
    df: pd.DataFrame,
    target_horizon: int,
    target_col: str = "pm2_5",
) -> tuple[pd.DataFrame, list[str]]:
    """Build the full feature row from raw aligned observations.

    Uses the same feature engineering pipeline as training:
        1. Target lags (PM2.5 history)
        2. Target rolling stats
        3. Weather rolling stats
        4. Temporal features
        5. Derived features

    Args:
        df: Aligned hourly DataFrame with raw parameters.
        target_horizon: Forecast horizon in hours.
        target_col: Target column name.

    Returns:
        Tuple of (feature DataFrame with one row, feature column names).
    """
    out = df.copy()

    # Step 1: Target lags
    out = build_target_lags(out, target_col, TARGET_LAGS)

    # Step 2: Target rolling stats
    out = build_target_rolling(out, target_col, TARGET_ROLLING_WINDOWS, TARGET_ROLLING_OPS)

    # Step 3: Weather rolling stats
    out = build_weather_rolling(out)

    # Step 4: Temporal features
    out = build_temporal_features(out)

    # Step 5: Derived features
    out = build_derived_features(out)

    # Step 6: Select feature columns
    feature_cols = get_feature_columns(out)

    # Step 7: Take the LAST row (most recent time)
    last_row = out[feature_cols].iloc[[-1]].copy()

    return last_row, feature_cols


def check_freshness(
    df: pd.DataFrame,
    as_of: datetime,
) -> tuple[float, list[str]]:
    """Check data freshness and report warnings.

    Args:
        df: Aligned DataFrame with observations.
        as_of: Prediction target time.

    Returns:
        Tuple of (freshness_hours, list of warning messages).
    """
    warnings: list[str] = []

    if df.empty:
        return float("inf"), ["No data available"]

    # Ensure UTC comparison
    if df.index.tz is None:
        latest_data = df.index.max()
    else:
        latest_data = df.index.max()

    if as_of.tzinfo is None:
        as_of_utc = as_of.replace(tzinfo=UTC)
    else:
        as_of_utc = as_of

    freshness_hours = (as_of_utc - latest_data).total_seconds() / 3600

    if freshness_hours > STALENESS_CRITICAL_HOURS:
        warnings.append(
            f"CRITICAL: Latest observation is {freshness_hours:.1f}h old "
            f"(threshold: {STALENESS_CRITICAL_HOURS}h)"
        )
    elif freshness_hours > STALENESS_WARNING_HOURS:
        warnings.append(
            f"WARNING: Latest observation is {freshness_hours:.1f}h old "
            f"(threshold: {STALENESS_WARNING_HOURS}h)"
        )

    return freshness_hours, warnings


def check_feature_coverage(
    feature_row: pd.DataFrame,
    required_features: list[str],
) -> list[str]:
    """Check which required features are missing or NaN.

    Args:
        feature_row: Single-row DataFrame.
        required_features: Features the model expects.

    Returns:
        List of missing/NaN feature names.
    """
    missing: list[str] = []
    for col in required_features:
        if col not in feature_row.columns:
            missing.append(col)
        elif pd.isna(feature_row[col].iloc[0]):
            missing.append(col)
    return missing


# ── Main Assembly Function ────────────────────────────────────────


def assemble_prediction_features(
    db_path: str | Path,
    as_of: datetime,
    target_horizon: int,
    model_feature_names: list[str],
    lookback_hours: int = LOOKBACK_HOURS,
) -> FeatureAssemblyResult:
    """End-to-end feature assembly for a prediction request.

    This is the single entry point for feature construction.
    It loads data, builds features, checks freshness, and
    validates feature coverage.

    Args:
        db_path: Path to SQLite database.
        as_of: Prediction target timestamp (UTC).
        target_horizon: Forecast horizon in hours.
        model_feature_names: Feature names the model expects.
        lookback_hours: Hours of history to load.

    Returns:
        FeatureAssemblyResult with assembled features and diagnostics.
    """
    # 1. Load recent observations
    raw_df = _load_recent_observations(db_path, as_of, lookback_hours)
    if raw_df.empty:
        return FeatureAssemblyResult(
            timestamp=as_of,
            warnings=["No observations found in database"],
        )

    # 2. Align to hourly grid
    aligned = _align_to_hourly(raw_df)

    # 3. Check freshness
    freshness_hours, freshness_warnings = check_freshness(aligned, as_of)

    # 4. Build features
    try:
        feature_row, _ = assemble_features(aligned, target_horizon)
    except Exception as exc:
        logger.error("Feature construction failed", error=str(exc))
        return FeatureAssemblyResult(
            timestamp=as_of,
            data_timestamp=aligned.index.max() if not aligned.empty else None,
            freshness_hours=freshness_hours,
            raw_observations_used=len(aligned),
            warnings=freshness_warnings + [f"Feature construction failed: {exc}"],
        )

    # 5. Check feature coverage
    missing = check_feature_coverage(feature_row, model_feature_names)

    if missing:
        logger.warning(
            "Missing features detected",
            missing_count=len(missing),
            missing=missing[:10],  # Log first 10
        )

    # 6. Build result
    result = FeatureAssemblyResult(
        timestamp=as_of,
        feature_row=feature_row,
        data_timestamp=aligned.index.max() if not aligned.empty else None,
        freshness_hours=freshness_hours,
        raw_observations_used=len(aligned),
        missing_features=missing,
        warnings=freshness_warnings,
    )

    logger.info(
        "Features assembled",
        as_of=str(as_of),
        horizon=target_horizon,
        features_total=len(model_feature_names),
        features_missing=len(missing),
        freshness_hours=round(freshness_hours, 1),
        is_usable=result.is_usable,
    )

    return result


# ── Multi-Horizon Shared Assembly ─────────────────────────────────


def assemble_shared_features(
    db_path: str | Path,
    as_of: datetime,
    horizons: list[int],
    model_feature_names_map: dict[int, list[str]],
    lookback_hours: int = LOOKBACK_HOURS,
    use_cache: bool = True,
) -> dict[int, FeatureAssemblyResult]:
    """Assemble features for multiple horizons using ONE database query.

    This is the primary Phase 5.5 optimization: instead of querying the
    database once per horizon (5 queries × 17s = 85s), we query once
    and build features for all horizons from the same data.

    Feature construction is horizon-independent: lags, rolling stats,
    and temporal features use the same lookback window regardless of
    forecast horizon. The horizon only determines which row is used
    for prediction, and all horizons use the last row.

    Args:
        db_path: Path to SQLite database.
        as_of: Prediction target timestamp (UTC).
        horizons: List of forecast horizons to build for.
        model_feature_names_map: Dict mapping horizon → list of feature names.
        lookback_hours: Hours of history to load.
        use_cache: Whether to use the observation cache.

    Returns:
        Dict mapping horizon → FeatureAssemblyResult.
    """
    t0 = _time.perf_counter()

    # 1. Single database query — shared across all horizons
    raw_df = _load_recent_observations(db_path, as_of, lookback_hours, use_cache=use_cache)
    if raw_df.empty:
        return {
            h: FeatureAssemblyResult(
                timestamp=as_of,
                warnings=["No observations found in database"],
            )
            for h in horizons
        }

    # 2. Align to hourly grid — shared across all horizons
    aligned = _align_to_hourly(raw_df)

    # 3. Check freshness — shared across all horizons
    freshness_hours, freshness_warnings = check_freshness(aligned, as_of)

    # 4. Build features — shared across all horizons
    # Feature construction is horizon-independent: lags, rolling stats,
    # and temporal features use the same lookback window regardless of
    # forecast horizon. We build once and reuse.
    try:
        feature_row, _ = assemble_features(aligned, target_horizon=1)
    except Exception as exc:
        logger.error("Feature construction failed", error=str(exc))
        return {
            h: FeatureAssemblyResult(
                timestamp=as_of,
                data_timestamp=aligned.index.max() if not aligned.empty else None,
                freshness_hours=freshness_hours,
                raw_observations_used=len(aligned),
                warnings=freshness_warnings + [f"Feature construction failed: {exc}"],
            )
            for h in horizons
        }

    # 5. Build results for each horizon
    results = {}
    for horizon in horizons:
        model_feature_names = model_feature_names_map.get(horizon, [])
        missing = check_feature_coverage(feature_row, model_feature_names)

        if missing:
            logger.warning(
                "Missing features detected",
                horizon=horizon,
                missing_count=len(missing),
                missing=missing[:10],
            )

        results[horizon] = FeatureAssemblyResult(
            timestamp=as_of,
            feature_row=feature_row.copy(),
            data_timestamp=aligned.index.max() if not aligned.empty else None,
            freshness_hours=freshness_hours,
            raw_observations_used=len(aligned),
            missing_features=missing,
            warnings=freshness_warnings,
            horizon=horizon,
        )

    elapsed_ms = (_time.perf_counter() - t0) * 1000
    logger.info(
        "Shared feature assembly completed",
        horizons=horizons,
        elapsed_ms=round(elapsed_ms, 2),
        rows=len(aligned),
        parameters=len(aligned.columns),
    )

    return results
