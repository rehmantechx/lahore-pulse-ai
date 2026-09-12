"""Dataset loader — loads modeling data directly from SQLite.

Replaces the async DataCollector-based path with a direct SQL query
that constructs the modeling dataset for the overlap period
(Aug 2022 onwards) where all 19 parameters are co-available.

Design principles:
    - Reads REAL data only from the existing database
    - Aligns to hourly UTC grid
    - No imputation for the target (PM2.5); drops rows with NaN targets
    - Forward-fills short weather gaps (≤3h)
    - Documents every transformation
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from .config import DatasetConfig
from ..core.db import get_db_connection, is_cloud_db

# ── Constants ────────────────────────────────────────────────────────

# Overlap period: where AQ + weather are simultaneously available
OVERLAP_START = "2022-08-01"

# Weather parameters in the database
WEATHER_PARAMS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "soil_temperature_0_to_7cm",
]

# AQ parameters in the database
AQ_PARAMS = [
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "carbon_monoxide",
]

# Parameters NOT in DB but in config (will be NaN)
MISSING_PARAMS = [
    "wind_direction_10m",
    "vapour_pressure_deficit",
    "soil_moisture_0_to_7cm",
]

ALL_PARAMS = WEATHER_PARAMS + AQ_PARAMS


# ── Database Loading ─────────────────────────────────────────────────


def load_observations_from_db(
    db_path: str | Path,
    start_date: str = OVERLAP_START,
    parameters: list[str] | None = None,
) -> pd.DataFrame:
    """Load observations from the SQLite database for the overlap period.

    Queries the database directly and returns a wide-format DataFrame
    with one column per parameter and a DatetimeIndex (UTC, hourly).

    Args:
        db_path: Path to the SQLite database file.
        start_date: Only load observations from this date onwards (ISO format).
        parameters: Parameters to load. If None, loads all available.

    Returns:
        Wide-format DataFrame with DatetimeIndex named 'time' (UTC).
    """
    db_path = Path(db_path)
    if not is_cloud_db() and not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    params_to_load = parameters or ALL_PARAMS
    placeholders = ",".join(["?"] * len(params_to_load))

    conn = get_db_connection(read_only=True)
    try:
        sql = f"""
            SELECT observed_at, parameter, value
            FROM observations
            WHERE observed_at >= ?
            AND parameter IN ({placeholders})
            AND observation_type = 'observation'
            ORDER BY observed_at
        """
        rows = conn.execute(sql, [start_date, *params_to_load]).fetchall()
    finally:
        conn.close()

    if not rows:
        logger.warning("No observations found for the requested period")
        return pd.DataFrame()

    logger.info(
        "Loaded observations from database",
        rows=len(rows),
        start_date=start_date,
        db_path=str(db_path),
    )

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=["observed_at", "parameter", "value"])
    df["time"] = pd.to_datetime(df["observed_at"], format="mixed", utc=True)
    df = df.set_index("time").sort_index()
    df = df.drop(columns=["observed_at"])

    # Pivot to wide format (handle potential duplicates by averaging)
    if df.index.duplicated().any():
        logger.warning(
            "Duplicate timestamps found, aggregating by mean",
            duplicates=int(df.index.duplicated().sum()),
        )
        # Group by time and parameter, take mean of duplicates
        df = df.groupby(["time", "parameter"])["value"].mean().reset_index()
        df = df.set_index("time").sort_index()

    wide = df.pivot(columns="parameter", values="value")
    if isinstance(wide.columns, pd.MultiIndex):
        wide.columns = wide.columns.get_level_values(-1)

    # Add missing parameters as NaN
    for p in MISSING_PARAMS:
        if p not in wide.columns:
            wide[p] = np.nan

    return wide


def align_to_hourly_grid(
    df: pd.DataFrame,
    max_gap_hours: int = 3,
) -> pd.DataFrame:
    """Resample observations to a regular hourly UTC grid.

    - Creates complete hourly range from min to max timestamp
    - Forward-fills short gaps (≤ max_gap_hours)
    - Drops rows still all-NaN after filling

    Args:
        df: Wide-format DataFrame with DatetimeIndex.
        max_gap_hours: Maximum gap length to forward-fill.

    Returns:
        Aligned DataFrame on regular hourly grid.
    """
    if df.empty:
        return df

    # Ensure UTC
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    # Create complete hourly range
    full_range = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="1h",
        tz="UTC",
    )

    aligned = df.reindex(full_range)
    aligned.index.name = "time"

    # Forward-fill short gaps
    n_before = int(aligned.isna().all(axis=1).sum())
    aligned = aligned.ffill(limit=max_gap_hours)
    n_after = int(aligned.isna().all(axis=1).sum())

    logger.info(
        "Aligned to hourly grid",
        original_rows=len(df),
        aligned_rows=len(aligned),
        gaps_filled=n_before - n_after,
        gaps_remaining=n_after,
    )

    return aligned


def describe_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Describe the loaded dataset with summary statistics.

    Args:
        df: Wide-format DataFrame.

    Returns:
        Dictionary with dataset description.
    """
    if df.empty:
        return {"rows": 0, "columns": 0}

    desc: dict[str, Any] = {
        "rows": len(df),
        "columns": len(df.columns),
        "date_range_start": str(df.index.min()),
        "date_range_end": str(df.index.max()),
        "duration_hours": int((df.index.max() - df.index.min()).total_seconds() / 3600),
        "parameters": list(df.columns),
        "parameter_count": len(df.columns),
        "missing_by_param": {},
    }

    for col in df.columns:
        non_null = df[col].notna().sum()
        desc["missing_by_param"][col] = {
            "non_null": int(non_null),
            "total": len(df),
            "coverage": round(non_null / len(df), 4),
        }

    return desc


# ── Target-Aware Dataset Preparation ────────────────────────────────


def prepare_modeling_dataset(
    db_path: str | Path,
    config: DatasetConfig | None = None,
) -> dict[str, Any]:
    """Full pipeline: load → align → describe.

    Returns the aligned DataFrame plus metadata. Feature engineering
    and target construction are handled by the training pipeline.

    Args:
        db_path: Path to the SQLite database.
        config: Dataset configuration (optional, for parameter overrides).

    Returns:
        Dictionary with:
            - 'df': Aligned hourly DataFrame (all parameters)
            - 'description': Dataset summary statistics
            - 'config': The DatasetConfig used
    """
    cfg = config or DatasetConfig()

    # Load from database
    df = load_observations_from_db(
        db_path=db_path,
        start_date=OVERLAP_START,
    )

    if df.empty:
        return {"df": df, "description": {}, "config": cfg}

    # Align to hourly grid
    aligned = align_to_hourly_grid(df, cfg.alignment.max_gap_hours)

    # Describe
    desc = describe_dataset(aligned)

    logger.info(
        "Modeling dataset prepared",
        rows=desc["rows"],
        parameters=desc["parameter_count"],
        duration_hours=desc["duration_hours"],
    )

    return {"df": aligned, "description": desc, "config": cfg}
