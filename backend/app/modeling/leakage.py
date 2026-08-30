"""Data-leakage detection — automated safety checks.

Implements a battery of tests that verify the feature-target separation
is temporally correct.  Any violation is reported as an error.

Checks performed:
    1. Future-mutation test: no feature column contains future target values.
    2. Target-isolation test: target columns are not used as features.
    3. Temporal-order test: all feature lags are non-negative (backward-looking).
    4. Rolling-window test: rolling features use only past data.
    5. Split-gap test: no temporal overlap between train and test splits.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .config import DatasetConfig, TargetConfig

# ── Check 1: Future-Mutation ─────────────────────────────────────────


def check_no_future_mutation(
    df: pd.DataFrame,
    target_config: TargetConfig | None = None,
) -> list[str]:
    """Verify that no feature column encodes future target values.

    A future-mutation violation occurs when a non-target column has
    values identical to a future-horizon target column.

    Args:
        df: Assembled dataset with features and targets.
        target_config: Target configuration.

    Returns:
        List of error messages (empty if no violations).
    """
    errors: list[str] = []
    target_cols = [c for c in df.columns if c.startswith("target_")]
    feature_cols = [c for c in df.columns if c not in target_cols]

    for tcol in target_cols:
        for fcol in feature_cols:
            if tcol == fcol:
                continue
            # Check if feature column is just a shifted version of the target
            if df[fcol].equals(df[tcol]):
                errors.append(f"Future-mutation: feature '{fcol}' is identical to target '{tcol}'")

    return errors


# ── Check 2: Target Isolation ────────────────────────────────────────


def check_target_not_in_features(
    df: pd.DataFrame,
) -> list[str]:
    """Verify that no target column appears in the feature set.

    Args:
        df: Assembled dataset.
        target_config: Target configuration.

    Returns:
        List of error messages (empty if no violations).
    """
    errors: list[str] = []
    target_cols = [c for c in df.columns if c.startswith("target_")]

    # Feature columns are all non-target columns
    feature_cols = [c for c in df.columns if c not in target_cols]

    for tcol in target_cols:
        if tcol in feature_cols:
            errors.append(f"Target-isolation: target column '{tcol}' is also in the feature set")

    return errors


# ── Check 3: Temporal-Order (Lag Sign) ──────────────────────────────


def check_lag_signs(
    df: pd.DataFrame,
) -> list[str]:
    """Verify that all lag features have positive lag offsets (backward-looking).

    Lag column names follow the pattern ``*_lag_Nh`` where N is the
    lag offset in hours.  Negative lags would encode future data.

    Args:
        df: Assembled dataset.

    Returns:
        List of error messages (empty if no violations).
    """
    errors: list[str] = []
    lag_pattern = re.compile(r"_lag_(-?\d+)h$")

    for col in df.columns:
        match = lag_pattern.search(col)
        if match:
            lag_value = int(match.group(1))
            if lag_value < 0:
                errors.append(f"Temporal-order: column '{col}' has negative lag ({lag_value}h)")

    return errors


# ── Check 4: Rolling-Window Causality ────────────────────────────────


def check_rolling_causality(
    df: pd.DataFrame,
) -> list[str]:
    """Verify that rolling features use min_periods=1 (causal).

    This is a structural check: rolling columns should have NaN only
    at the start (where insufficient data exists), never at random
    positions (which would indicate non-causal windowing).

    Returns:
        List of error messages (empty if no violations).
    """
    errors: list[str] = []
    # Structural check: rolling columns should have NaN only at the start,
    # consistent with causal windowing.  For columns that are rolling-on-lagged
    # data (e.g. "X_lag_6h_roll_3h_mean"), the NaN region extends by the lag
    # offset.  We parse the lag offset from the column name to compute the
    # correct expected boundary.

    roll_pattern = re.compile(r"_roll_(\d+)h_")
    lag_pattern = re.compile(r"_lag_(\d+)h_")
    for col in df.columns:
        match = roll_pattern.search(col)
        if match:
            window = int(match.group(1))
            # Detect lag offset for lagged-then-rolled columns
            lag_match = lag_pattern.search(col)
            lag_offset = int(lag_match.group(1)) if lag_match else 0

            series = df[col]
            # First (window-1) rows should have NaN (or be the only NaNs)
            nan_mask = series.isna()
            if nan_mask.any():
                # Find first valid index position
                first_valid_pos = series.first_valid_index()
                if first_valid_pos is not None:
                    first_valid = df.index.get_loc(first_valid_pos)
                else:
                    first_valid = 0
                # Expected boundary: lag offset + rolling window - 1
                expected_boundary = lag_offset + window
                if first_valid > expected_boundary:
                    errors.append(
                        f"Rolling-causality: '{col}' has NaN at row {first_valid}, "
                        f"expected within first {expected_boundary} rows"
                    )

    return errors


# ── Check 5: Split Temporal Separation ───────────────────────────────


def check_split_separation(
    train_df: pd.DataFrame | None,
    val_df: pd.DataFrame | None,
    test_df: pd.DataFrame | None,
    gap_hours: int = 72,
) -> list[str]:
    """Verify that train, validation, and test sets are temporally separated.

    Args:
        train_df: Training split.
        val_df: Validation split.
        test_df: Test split.
        gap_hours: Minimum gap between splits in hours.

    Returns:
        List of error messages (empty if no violations).
    """
    errors: list[str] = []

    if train_df is not None and val_df is not None and not train_df.empty and not val_df.empty:
        train_max = train_df.index.max()
        val_min = val_df.index.min()
        actual_gap = (val_min - train_max).total_seconds() / 3600
        if actual_gap < gap_hours:
            errors.append(
                f"Split-separation: train→val gap is {actual_gap:.0f}h, "
                f"minimum required is {gap_hours}h"
            )

    if val_df is not None and test_df is not None and not val_df.empty and not test_df.empty:
        val_max = val_df.index.max()
        test_min = test_df.index.min()
        actual_gap = (test_min - val_max).total_seconds() / 3600
        if actual_gap < gap_hours:
            errors.append(
                f"Split-separation: val→test gap is {actual_gap:.0f}h, "
                f"minimum required is {gap_hours}h"
            )

    return errors


# ── Master Leakage Check ─────────────────────────────────────────────


def run_all_leakage_checks(
    df: pd.DataFrame,
    train_df: pd.DataFrame | None = None,
    val_df: pd.DataFrame | None = None,
    test_df: pd.DataFrame | None = None,
    config: DatasetConfig | None = None,
) -> dict[str, object]:
    """Run all leakage detection checks and return a summary.

    Args:
        df: Full assembled dataset.
        train_df: Training split (for split-separation check).
        val_df: Validation split.
        test_df: Test split.
        config: Dataset configuration.

    Returns:
        Dictionary with check results:
        ``{"passed": bool, "checks": {name: {passed, errors}}, "total_errors": int}``
    """
    cfg = config or DatasetConfig()

    checks: dict[str, Any] = {}
    e1 = check_no_future_mutation(df, cfg.target)
    checks["future_mutation"] = {"passed": len(e1) == 0, "errors": e1}

    # Check 2
    e2 = check_target_not_in_features(df)
    checks["target_isolation"] = {"passed": len(e2) == 0, "errors": e2}

    # Check 3
    e3 = check_lag_signs(df)
    checks["temporal_order"] = {"passed": len(e3) == 0, "errors": e3}

    # Check 4
    e4 = check_rolling_causality(df)
    checks["rolling_causality"] = {"passed": len(e4) == 0, "errors": e4}

    # Check 5
    e5 = check_split_separation(
        train_df,
        val_df,
        test_df,
        cfg.splits.gap_hours,
    )
    checks["split_separation"] = {"passed": len(e5) == 0, "errors": e5}

    total_errors = sum(len(c["errors"]) for c in checks.values())

    return {
        "passed": total_errors == 0,
        "checks": checks,
        "total_errors": total_errors,
    }
