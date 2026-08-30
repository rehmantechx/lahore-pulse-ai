"""Temporal alignment — resample observations to a regular hourly UTC grid.

Raw observations from different sources arrive at irregular timestamps.
This module aligns them to a consistent hourly UTC grid so that lag
and rolling features can be computed correctly.

Gap handling:
    - Short gaps (≤ max_gap_hours) are forward-filled.
    - Longer gaps are left as NaN (and flagged in the quality report).
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from .config import AlignmentConfig


def observations_to_dataframe(
    rows: list[dict],
) -> pd.DataFrame:
    """Convert a list of observation dicts (from the DB) into a DataFrame.

    Each dict is expected to have keys:
        ``observed_at`` (ISO string), ``parameter``, ``value``

    The returned DataFrame has a DatetimeIndex named ``time`` and one
    column per parameter.

    Args:
        rows: List of observation dicts.

    Returns:
        Wide-format DataFrame with DatetimeIndex.
    """
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    if "observed_at" not in df.columns:
        raise ValueError("Each observation dict must have an 'observed_at' key")

    df["time"] = pd.to_datetime(df["observed_at"], utc=True)
    df = df.set_index("time").sort_index()

    # Pivot to wide format: one column per parameter
    if "parameter" in df.columns and "value" in df.columns:
        wide = df.pivot(columns="parameter", values="value")
        # Remove MultiIndex from columns if present
        if isinstance(wide.columns, pd.MultiIndex):
            wide.columns = wide.columns.get_level_values(-1)
        return wide

    return df


def align_to_hourly_grid(
    df: pd.DataFrame,
    config: AlignmentConfig | None = None,
) -> pd.DataFrame:
    """Resample a DataFrame to a regular hourly UTC grid.

    Steps:
        1. Reindex to a complete hourly range from min to max timestamp.
        2. Forward-fill short gaps (≤ max_gap_hours).
        3. Report gap statistics.

    Args:
        df: DataFrame with DatetimeIndex (UTC).
        config: Alignment configuration.

    Returns:
        Resampled DataFrame on a regular hourly grid.
    """
    cfg = config or AlignmentConfig()

    if df.empty:
        return df

    # Ensure UTC index
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    # Create complete hourly range
    full_range = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq=cfg.freq,
        tz="UTC",
    )

    # Reindex to complete range
    aligned = df.reindex(full_range)
    aligned.index.name = "time"

    # Forward-fill short gaps
    gap_before = int(aligned.isna().all(axis=1).sum())
    aligned = aligned.ffill(limit=cfg.max_gap_hours)
    gap_after = int(aligned.isna().all(axis=1).sum())

    filled = gap_before - gap_after
    remaining = gap_after

    if filled > 0:
        logger.info(
            "Forward-filled gaps",
            filled=filled,
            remaining=remaining,
        )

    if remaining > 0:
        logger.warning(
            "Unfillable gaps remain",
            gap_count=remaining,
            max_gap_hours=cfg.max_gap_hours,
        )

    return aligned


def compute_alignment_stats(
    original: pd.DataFrame,
    aligned: pd.DataFrame,
) -> dict[str, object]:
    """Compute alignment quality statistics.

    Args:
        original: Pre-alignment DataFrame.
        aligned: Post-alignment DataFrame.

    Returns:
        Dictionary of alignment statistics.
    """
    stats: dict[str, object] = {
        "original_rows": len(original),
        "aligned_rows": len(aligned),
        "expansion_ratio": (round(len(aligned) / len(original), 2) if len(original) > 0 else 0),
    }

    if not original.empty and not aligned.empty:
        # Count NaN gaps per column
        gap_info: dict[str, dict[str, object]] = {}
        for col in aligned.columns:
            nan_mask = aligned[col].isna()
            total_nan = int(nan_mask.sum())
            # Find consecutive NaN runs
            runs = _consecutive_nan_runs(aligned[col])
            gap_info[col] = {
                "total_nan": total_nan,
                "gap_count": len(runs),
                "max_gap_length": max(runs) if runs else 0,
                "missing_ratio": round(total_nan / len(aligned), 4),
            }
        stats["per_column"] = gap_info

    return stats


def _consecutive_nan_runs(series: pd.Series) -> list[int]:
    """Find lengths of consecutive NaN runs in a Series."""
    is_nan = series.isna()
    runs: list[int] = []
    current_run = 0
    for val in is_nan:
        if val:
            current_run += 1
        else:
            if current_run > 0:
                runs.append(current_run)
            current_run = 0
    if current_run > 0:
        runs.append(current_run)
    return runs
