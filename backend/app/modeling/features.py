"""Feature engineering — lag, rolling, weather, and temporal features.

All feature construction is strictly causal: features at time t use
only observations from t or earlier.  No future information leaks
into the feature matrix.

Feature categories:
    1. Weather features — raw meteorological variables
    2. Lag features    — x(t-k) for k in LAG_OFFSETS
    3. Rolling features — rolling statistics over windows
    4. Temporal features — cyclical hour/day/month encodings
    5. Derived features — wind decomposition, heat index
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig

# ── Weather Features ─────────────────────────────────────────────────


def add_weather_features(
    df: pd.DataFrame,
    config: FeatureConfig | None = None,
) -> pd.DataFrame:
    """Select and optionally derive weather features from raw observations.

    Args:
        df: DataFrame with DatetimeIndex and weather variable columns.
        config: Feature configuration.

    Returns:
        DataFrame with selected weather columns (unmodified copies).
    """
    cfg = config or FeatureConfig()
    out = df.copy()

    # Ensure requested weather columns exist
    for var in cfg.weather.variables:
        if var not in out.columns:
            out[var] = np.nan

    return out


# ── Wind Decomposition ───────────────────────────────────────────────


def encode_wind(
    df: pd.DataFrame,
    speed_col: str = "wind_speed_10m",
    direction_col: str = "wind_direction_10m",
) -> pd.DataFrame:
    """Decompose wind speed + direction into (speed, sin, cos) triple.

    Args:
        df: DataFrame with wind speed and direction columns.
        speed_col: Column name for wind speed.
        direction_col: Column name for wind direction (degrees).

    Returns:
        DataFrame with added ``wind_dir_sin`` and ``wind_dir_cos`` columns.
    """
    out = df.copy()
    if direction_col in out.columns:
        dir_rad = np.deg2rad(out[direction_col])
        out["wind_dir_sin"] = np.sin(dir_rad)
        out["wind_dir_cos"] = np.cos(dir_rad)
    else:
        out["wind_dir_sin"] = np.nan
        out["wind_dir_cos"] = np.nan
    return out


# ── Lag Features ─────────────────────────────────────────────────────


def add_lag_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    lags: tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48, 72),
) -> pd.DataFrame:
    """Create lagged versions of specified columns.

    For each column c and lag k, creates ``c_lag_kh`` = c(t-k).

    Args:
        df: DataFrame with DatetimeIndex.
        columns: Column names to lag.  If None, lags all numeric columns.
        lags: Lag offsets in hours.

    Returns:
        DataFrame with added lag columns.
    """
    out = df.copy()
    if columns is None:
        columns = [c for c in out.select_dtypes(include=[np.number]).columns]

    for col in columns:
        for lag in lags:
            lag_col = f"{col}_lag_{lag}h"
            out[lag_col] = out[col].shift(lag)

    return out


# ── Rolling Features ─────────────────────────────────────────────────


def add_rolling_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    windows: tuple[int, ...] = (3, 6, 12, 24),
    operations: tuple[str, ...] = ("mean", "std", "min", "max"),
) -> pd.DataFrame:
    """Create rolling-window statistics for specified columns.

    For each column c, window w, and operation op, creates
    ``c_roll_{w}h_{op}`` using a trailing window of w hours.

    Args:
        df: DataFrame with DatetimeIndex.
        columns: Column names to compute rolling stats for.
        windows: Window sizes in hours.
        operations: Aggregation functions.

    Returns:
        DataFrame with added rolling columns.
    """
    out = df.copy()
    if columns is None:
        columns = [c for c in out.select_dtypes(include=[np.number]).columns]

    for col in columns:
        for window in windows:
            rolling = out[col].rolling(window=window, min_periods=1)
            for op in operations:
                roll_col = f"{col}_roll_{window}h_{op}"
                if op == "mean":
                    out[roll_col] = rolling.mean()
                elif op == "std":
                    out[roll_col] = rolling.std()
                elif op == "min":
                    out[roll_col] = rolling.min()
                elif op == "max":
                    out[roll_col] = rolling.max()
                elif op == "median":
                    out[roll_col] = rolling.median()

    return out


# ── Temporal Features ────────────────────────────────────────────────


def add_temporal_features(
    df: pd.DataFrame,
    encode_hour: bool = True,
    encode_dow: bool = True,
    encode_month: bool = True,
) -> pd.DataFrame:
    """Add cyclical time-of-day, day-of-week, and month-of-year encodings.

    Uses sin/cos transformation to preserve cyclical nature:
        sin(2π × hour / 24), cos(2π × hour / 24), etc.

    Args:
        df: DataFrame with DatetimeIndex.
        encode_hour: Whether to encode hour-of-day.
        encode_dow: Whether to encode day-of-week.
        encode_month: Whether to encode month-of-year.

    Returns:
        DataFrame with added temporal feature columns.
    """
    out = df.copy()
    idx = out.index

    if encode_hour:
        hours = idx.hour + idx.minute / 60.0  # fractional hour
        out["hour_sin"] = np.sin(2 * np.pi * hours / 24)
        out["hour_cos"] = np.cos(2 * np.pi * hours / 24)

    if encode_dow:
        dow = idx.dayofweek  # Monday=0, Sunday=6
        out["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        out["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    if encode_month:
        month = idx.month - 1  # 0-indexed
        out["month_sin"] = np.sin(2 * np.pi * month / 12)
        out["month_cos"] = np.cos(2 * np.pi * month / 12)

    return out


# ── Derived Features ─────────────────────────────────────────────────


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add physically-motivated derived weather features.

    Derived features:
        - ``heat_index``: Apparent temperature proxy using temp + humidity.
        - ``temp_humidity_interaction``: temperature × humidity/100.
        - ``pressure_change``: Hour-over-hour pressure change (ΔP).
        - ``precipitation_accumulated_3h``: 3-hour precipitation sum.

    Args:
        df: DataFrame with DatetimeIndex and weather columns.

    Returns:
        DataFrame with added derived columns.
    """
    out = df.copy()

    # Heat index approximation (simplified Rothfusz regression)
    if "temperature_2m" in out.columns and "relative_humidity_2m" in out.columns:
        t = out["temperature_2m"]
        rh = out["relative_humidity_2m"]
        # Simple heat index: only applies when T > 27°C and RH > 40%
        hi = t.copy()
        mask = (t > 27) & (rh > 40)
        hi[mask] = (
            -8.784695
            + 1.61139411 * t[mask]
            + 2.33854900 * rh[mask]
            - 0.14611601 * t[mask] * rh[mask]
            - 0.012308094 * t[mask] ** 2
            - 0.016424828 * rh[mask] ** 2
            + 0.002211732 * t[mask] ** 2 * rh[mask]
            + 0.00072546 * t[mask] * rh[mask] ** 2
            - 0.000003582 * t[mask] ** 2 * rh[mask] ** 2
        )
        out["heat_index"] = hi
        out["temp_humidity_interaction"] = t * rh / 100.0

    # Pressure change
    if "pressure_msl" in out.columns:
        out["pressure_change"] = out["pressure_msl"].diff(1)

    # Accumulated precipitation
    if "precipitation" in out.columns:
        out["precipitation_accumulated_3h"] = (
            out["precipitation"].rolling(window=3, min_periods=1).sum()
        )

    return out


# ── Master Feature Builder ───────────────────────────────────────────


def build_features(
    df: pd.DataFrame,
    config: FeatureConfig | None = None,
) -> pd.DataFrame:
    """Apply the full feature engineering pipeline.

    Order of operations:
        1. Weather feature selection
        2. Wind decomposition (sin/cos)
        3. Derived features
        4. Lag features (all numeric columns)
        5. Rolling features (all numeric columns)
        6. Temporal features (cyclical encodings)

    Args:
        df: DataFrame with DatetimeIndex and raw weather/AQ columns.
        config: Feature engineering configuration.

    Returns:
        DataFrame with all engineered features.
    """
    cfg = config or FeatureConfig()

    # Step 1: Weather features (selection only)
    out = add_weather_features(df, cfg)

    # Step 2: Wind decomposition
    if cfg.weather.wind_encode:
        out = encode_wind(out)

    # Step 3: Derived features
    if cfg.weather.derived:
        out = add_derived_features(out)

    # Step 4: Lag features (on all numeric columns available)
    lag_columns = [c for c in out.select_dtypes(include=[np.number]).columns]
    out = add_lag_features(out, columns=lag_columns, lags=cfg.lags.offsets)

    # Step 5: Rolling features (on all numeric columns available)
    roll_columns = [c for c in out.select_dtypes(include=[np.number]).columns]
    out = add_rolling_features(
        out,
        columns=roll_columns,
        windows=cfg.rolling.windows,
        operations=cfg.rolling.operations,
    )

    # Step 6: Temporal features
    out = add_temporal_features(
        out,
        encode_hour=cfg.temporal.encode_hour,
        encode_dow=cfg.temporal.encode_dow,
        encode_month=cfg.temporal.encode_month,
    )

    return out
