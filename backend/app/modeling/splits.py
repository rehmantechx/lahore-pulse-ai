"""Chronological train / validation / test splitting.

Splits are strictly chronological — never randomised — to prevent
any temporal information leakage.  A configurable gap between splits
prevents lag/rolling features from bridging the train-test boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import SplitConfig


@dataclass
class DatasetSplits:
    """Container for the three dataset partitions.

    Each attribute is a DataFrame (or None if the split was not created).
    """

    train: pd.DataFrame | None = None
    validation: pd.DataFrame | None = None
    test: pd.DataFrame | None = None
    gap_train_val: pd.DataFrame | None = None  # dropped gap rows
    gap_val_test: pd.DataFrame | None = None  # dropped gap rows

    @property
    def total_rows(self) -> int:
        """Sum of rows across all non-None splits."""
        count = 0
        for split in (self.train, self.validation, self.test):
            if split is not None:
                count += len(split)
        return count


def chronological_split(
    df: pd.DataFrame,
    config: SplitConfig | None = None,
) -> DatasetSplits:
    """Split a DataFrame into train / validation / test by time order.

    The split respects:
        1. Strict chronological ordering (train → gap → val → gap → test).
        2. A configurable gap (in hours) between splits to prevent
           lag/rolling features from leaking across boundaries.
        3. Minimum training set size.

    Args:
        df: DataFrame with DatetimeIndex, sorted chronologically.
        config: Split configuration.

    Returns:
        DatasetSplits with the three partitions.

    Raises:
        ValueError: If the dataset is too small for the configured splits.
    """
    cfg = config or SplitConfig()

    if df.empty:
        return DatasetSplits()

    n = len(df)

    # Compute split indices
    train_end = int(n * cfg.train_ratio)
    val_end = int(n * (cfg.train_ratio + cfg.val_ratio))

    # Apply gap buffer (in rows, assuming hourly data)
    gap_train_val_start = train_end
    gap_train_val_end = min(train_end + cfg.gap_hours, n)

    gap_val_test_start = val_end
    gap_val_test_end = min(val_end + cfg.gap_hours, n)

    # Check minimum training size
    if train_end < cfg.min_train_hours:
        msg = (
            f"Training set has {train_end} rows, "
            f"minimum required is {cfg.min_train_hours}. "
            f"Consider increasing the data collection window."
        )
        raise ValueError(msg)

    splits = DatasetSplits(
        train=df.iloc[:train_end].copy(),
        gap_train_val=df.iloc[gap_train_val_start:gap_train_val_end].copy(),
        validation=df.iloc[gap_train_val_end:gap_val_test_start].copy(),
        gap_val_test=df.iloc[gap_val_test_start:gap_val_test_end].copy(),
        test=df.iloc[gap_val_test_end:].copy(),
    )

    return splits


def describe_splits(
    splits: DatasetSplits,
) -> dict[str, dict[str, object]]:
    """Generate descriptive statistics for each split.

    Args:
        splits: The dataset partitions.

    Returns:
        Dictionary keyed by split name with statistics.
    """
    result: dict[str, dict[str, object]] = {}

    for name, split_df in [
        ("train", splits.train),
        ("validation", splits.validation),
        ("test", splits.test),
    ]:
        if split_df is None or split_df.empty:
            result[name] = {"rows": 0, "start": None, "end": None, "duration_hours": 0}
            continue

        duration = split_df.index.max() - split_df.index.min()
        result[name] = {
            "rows": len(split_df),
            "start": str(split_df.index.min()),
            "end": str(split_df.index.max()),
            "duration_hours": int(duration.total_seconds() / 3600),
        }

    # Gap descriptions
    for name, gap_df in [
        ("gap_train_val", splits.gap_train_val),
        ("gap_val_test", splits.gap_val_test),
    ]:
        if gap_df is not None and not gap_df.empty:
            result[name] = {
                "rows": len(gap_df),
                "start": str(gap_df.index.min()),
                "end": str(gap_df.index.max()),
            }

    return result
