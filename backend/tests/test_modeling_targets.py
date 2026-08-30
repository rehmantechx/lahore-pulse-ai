"""Tests for target variable construction.

Verifies that future-horizon PM2.5 targets are correctly built
and validated from an hourly observation DataFrame.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.modeling.config import TargetConfig
from app.modeling.targets import build_targets, validate_targets


def _make_hourly_df(hours: int = 100, pm25_values: list[float] | None = None) -> pd.DataFrame:
    """Create a synthetic hourly DataFrame with a pm2_5 column."""
    idx = pd.date_range("2024-01-01", periods=hours, freq="1h", tz="UTC")
    if pm25_values is None:
        # Deterministic sine wave + trend (NOT random)
        t = np.arange(hours, dtype=float)
        values = 50 + 30 * np.sin(2 * np.pi * t / 24) + 0.1 * t
        pm25_values = values.tolist()
    df = pd.DataFrame({"pm2_5": pm25_values}, index=idx)
    df.index.name = "time"
    return df


class TestBuildTargets:
    """Tests for build_targets()."""

    def test_basic_target_columns_created(self) -> None:
        df = _make_hourly_df(100)
        result = build_targets(df, TargetConfig(horizons_hours=(1, 6, 24)))
        assert "target_pm2_5_t+1" in result.columns
        assert "target_pm2_5_t+6" in result.columns
        assert "target_pm2_5_t+24" in result.columns

    def test_target_shifted_correctly(self) -> None:
        df = _make_hourly_df(10)
        result = build_targets(df, TargetConfig(horizons_hours=(1,)))
        # target at t=0 should be value at t=1
        assert result["target_pm2_5_t+1"].iloc[0] == pytest.approx(df["pm2_5"].iloc[1])
        # Last row should be NaN (no future data)
        assert pd.isna(result["target_pm2_5_t+1"].iloc[-1])

    def test_missing_parameter_raises(self) -> None:
        df = pd.DataFrame({"temperature": [1, 2, 3]})
        with pytest.raises(ValueError, match="not found"):
            build_targets(df)

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame({"pm2_5": pd.Series(dtype=float)})
        result = build_targets(df)
        assert len(result) == 0

    def test_no_horizons(self) -> None:
        df = _make_hourly_df(10)
        result = build_targets(df, TargetConfig(horizons_hours=()))
        target_cols = [c for c in result.columns if c.startswith("target_")]
        assert len(target_cols) == 0


class TestValidateTargets:
    """Tests for validate_targets()."""

    def test_valid_targets_pass(self) -> None:
        df = _make_hourly_df(100)
        result = build_targets(df, TargetConfig(horizons_hours=(1,)))
        validation = validate_targets(result)
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_high_missing_fails(self) -> None:
        df = _make_hourly_df(100)
        result = build_targets(df, TargetConfig(horizons_hours=(1,)))
        # Force many NaN in target
        result.loc[result.index[:80], "target_pm2_5_t+1"] = np.nan
        validation = validate_targets(result, TargetConfig(max_missing_ratio=0.10))
        assert validation["valid"] is False

    def test_negative_values_flagged(self) -> None:
        df = _make_hourly_df(100)
        result = build_targets(df, TargetConfig(horizons_hours=(1,)))
        result.loc[result.index[5], "target_pm2_5_t+1"] = -10.0
        validation = validate_targets(result)
        assert validation["valid"] is False
        assert any("negative" in e for e in validation["errors"])

    def test_exceeds_bound_flagged(self) -> None:
        df = _make_hourly_df(100)
        result = build_targets(df, TargetConfig(horizons_hours=(1,)))
        result.loc[result.index[5], "target_pm2_5_t+1"] = 1500.0
        validation = validate_targets(result)
        assert validation["valid"] is False
        assert any("1000" in e for e in validation["errors"])

    def test_outlier_detection(self) -> None:
        df = _make_hourly_df(100)
        result = build_targets(df, TargetConfig(horizons_hours=(1,)))
        # Insert extreme outlier
        result.loc[result.index[5], "target_pm2_5_t+1"] = 5000.0
        validation = validate_targets(result, TargetConfig(outlier_zscore_threshold=3.0))
        assert validation["valid"] is False

    def test_no_target_columns(self) -> None:
        df = pd.DataFrame({"temperature": range(100)})
        df.index = pd.date_range("2024-01-01", periods=100, freq="1h", tz="UTC")
        df.index.name = "time"
        validation = validate_targets(df)
        assert validation["valid"] is False
