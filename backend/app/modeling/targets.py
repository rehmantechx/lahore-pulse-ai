"""Target variable construction.

Builds the forecasting target y(t+h) — PM2.5 concentration h hours
into the future — from a time-indexed DataFrame of observations.

Constraints:
    - Target values come from REAL observations only (no interpolation
      for the target itself).
    - Forward-looking windows must not leak into features.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from .config import TargetConfig

if TYPE_CHECKING:
    pass


def build_targets(
    observations: pd.DataFrame,
    config: TargetConfig | None = None,
) -> pd.DataFrame:
    """Construct future-horizon PM2.5 targets from an hourly observation DataFrame.

    The input DataFrame must have:
      - DatetimeIndex named ``time`` (UTC, hourly, monotonically increasing)
      - A column named ``pm2_5`` (or the parameter specified in config)

    For each horizon h in ``config.horizons_hours``, a column
    ``target_pm2_5_t+h`` is created containing the PM2.5 value h hours
    into the future.

    Args:
        observations: Hourly observation DataFrame with DatetimeIndex.
        config: Target configuration.  Uses defaults when ``None``.

    Returns:
        DataFrame with added target columns.  Rows where the target
        cannot be computed (insufficient future data) are set to NaN.
    """
    cfg = config or TargetConfig()
    df = observations.copy()

    param_col = cfg.parameter
    if param_col not in df.columns:
        msg = f"Target parameter '{param_col}' not found in columns: {list(df.columns)}"
        raise ValueError(msg)

    for h in cfg.horizons_hours:
        col_name = f"target_{param_col}_t+{h}"
        # shift(-h) moves future values into the current row
        df[col_name] = df[param_col].shift(-h)

    return df


def validate_targets(
    df: pd.DataFrame,
    config: TargetConfig | None = None,
) -> dict[str, object]:
    """Validate target construction quality.

    Checks:
      1. Missing ratio is below threshold.
      2. No values are negative.
      3. No values exceed the PM2.5 physical bound (1000 μg/m³).
      4. Outlier count is reported (z-score > threshold).

    Args:
        df: DataFrame with ``target_pm2_5_t+h`` columns.
        config: Target configuration.

    Returns:
        Dictionary with validation results:
        ``{"valid": bool, "details": {horizon: {...}, ...}, "errors": [...]}``
    """
    cfg = config or TargetConfig()
    errors: list[str] = []
    details: dict[str, dict[str, object]] = {}

    target_cols = [c for c in df.columns if c.startswith(f"target_{cfg.parameter}")]

    if not target_cols:
        return {"valid": False, "details": {}, "errors": ["No target columns found"]}

    for col in target_cols:
        series = df[col]
        total = len(series)
        missing = int(series.isna().sum())
        missing_ratio = missing / total if total > 0 else 1.0

        valid_values = series.dropna()
        negative_count = int((valid_values < 0).sum())
        too_high_count = int((valid_values > 1000).sum())  # PM2.5 bound

        # Z-score outliers
        if len(valid_values) > 2:
            zscores = (valid_values - valid_values.mean()) / valid_values.std()
            outlier_count = int((zscores.abs() > cfg.outlier_zscore_threshold).sum())
        else:
            outlier_count = 0

        col_details: dict[str, object] = {
            "total_rows": total,
            "missing": missing,
            "missing_ratio": round(missing_ratio, 4),
            "negative_values": negative_count,
            "exceeds_1000": too_high_count,
            "outlier_count": outlier_count,
            "mean": round(float(valid_values.mean()), 2) if len(valid_values) > 0 else None,
            "std": round(float(valid_values.std()), 2) if len(valid_values) > 0 else None,
            "min": round(float(valid_values.min()), 2) if len(valid_values) > 0 else None,
            "max": round(float(valid_values.max()), 2) if len(valid_values) > 0 else None,
        }
        details[col] = col_details

        if missing_ratio > cfg.max_missing_ratio:
            errors.append(
                f"{col}: missing ratio {missing_ratio:.2%} exceeds "
                f"threshold {cfg.max_missing_ratio:.2%}"
            )
        if negative_count > 0:
            errors.append(f"{col}: {negative_count} negative value(s)")
        if too_high_count > 0:
            errors.append(f"{col}: {too_high_count} value(s) exceed 1000 μg/m³")

    return {"valid": len(errors) == 0, "details": details, "errors": errors}
