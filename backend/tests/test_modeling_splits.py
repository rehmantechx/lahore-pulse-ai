"""Tests for chronological dataset splitting.

Verifies that splits are strictly chronological, respect gap buffers,
and raise errors for insufficient data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.modeling.config import SplitConfig
from app.modeling.splits import chronological_split, describe_splits


def _make_dataset(hours: int = 1500) -> pd.DataFrame:
    """Create a deterministic hourly dataset."""
    idx = pd.date_range("2024-01-01", periods=hours, freq="1h", tz="UTC")
    t = np.arange(hours, dtype=float)
    df = pd.DataFrame(
        {
            "pm2_5": 50 + 30 * np.sin(2 * np.pi * t / 24),
            "temperature_2m": 20 + 10 * np.sin(2 * np.pi * t / 24),
        },
        index=idx,
    )
    df.index.name = "time"
    return df


class TestChronologicalSplit:
    """Tests for chronological_split()."""

    def test_basic_split(self) -> None:
        df = _make_dataset(1500)
        splits = chronological_split(df)
        assert splits.train is not None
        assert splits.validation is not None
        assert splits.test is not None

    def test_chronological_order(self) -> None:
        df = _make_dataset(1500)
        splits = chronological_split(df)
        assert splits.train is not None
        assert splits.validation is not None
        assert splits.test is not None
        # All train timestamps < all val timestamps < all test timestamps
        assert splits.train.index.max() < splits.validation.index.min()
        assert splits.validation.index.max() < splits.test.index.min()

    def test_split_sizes(self) -> None:
        df = _make_dataset(1500)
        cfg = SplitConfig(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, gap_hours=0)
        splits = chronological_split(df, cfg)
        assert splits.train is not None
        assert splits.validation is not None
        assert splits.test is not None
        total = len(splits.train) + len(splits.validation) + len(splits.test)
        assert total == 1500

    def test_gap_buffer(self) -> None:
        df = _make_dataset(1500)
        cfg = SplitConfig(gap_hours=72)
        splits = chronological_split(df, cfg)
        assert splits.gap_train_val is not None
        assert splits.gap_val_test is not None
        assert len(splits.gap_train_val) == 72

    def test_insufficient_data_raises(self) -> None:
        df = _make_dataset(100)  # less than min_train_hours=720
        with pytest.raises(ValueError, match="minimum required"):
            chronological_split(df)

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        splits = chronological_split(df)
        assert splits.train is None
        assert splits.validation is None
        assert splits.test is None

    def test_total_rows(self) -> None:
        df = _make_dataset(1500)
        splits = chronological_split(df)
        assert splits.total_rows > 0


class TestDescribeSplits:
    """Tests for describe_splits()."""

    def test_basic_description(self) -> None:
        df = _make_dataset(1500)
        splits = chronological_split(df)
        desc = describe_splits(splits)
        assert "train" in desc
        assert "validation" in desc
        assert "test" in desc
        assert desc["train"]["rows"] > 0
        assert desc["validation"]["rows"] > 0
        assert desc["test"]["rows"] > 0

    def test_gap_description(self) -> None:
        df = _make_dataset(1500)
        splits = chronological_split(df)
        desc = describe_splits(splits)
        assert "gap_train_val" in desc
        assert "gap_val_test" in desc
