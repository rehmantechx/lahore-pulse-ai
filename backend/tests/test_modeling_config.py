"""Tests for modeling configuration.

Verifies that all config dataclasses are frozen, valid, and
produce the expected default values.
"""

from __future__ import annotations

import pytest

from app.modeling.config import (
    AlignmentConfig,
    DatasetConfig,
    LagConfig,
    RollingConfig,
    SplitConfig,
    TargetConfig,
)


class TestTargetConfig:
    """Tests for TargetConfig."""

    def test_default_parameter(self) -> None:
        cfg = TargetConfig()
        assert cfg.parameter == "pm2_5"

    def test_default_unit(self) -> None:
        cfg = TargetConfig()
        assert cfg.unit == "ug/m3"

    def test_default_horizons(self) -> None:
        cfg = TargetConfig()
        assert cfg.horizons_hours == (1, 3, 6, 12, 24)

    def test_frozen(self) -> None:
        cfg = TargetConfig()
        with pytest.raises(AttributeError):
            cfg.parameter = "pm10"  # type: ignore[misc]

    def test_missing_ratio_bounds(self) -> None:
        cfg = TargetConfig(max_missing_ratio=0.05)
        assert cfg.max_missing_ratio == 0.05


class TestLagConfig:
    """Tests for LagConfig."""

    def test_default_offsets(self) -> None:
        cfg = LagConfig()
        assert 1 in cfg.offsets
        assert 24 in cfg.offsets
        assert 72 in cfg.offsets

    def test_all_positive(self) -> None:
        cfg = LagConfig()
        assert all(k > 0 for k in cfg.offsets)


class TestRollingConfig:
    """Tests for RollingConfig."""

    def test_default_windows(self) -> None:
        cfg = RollingConfig()
        assert cfg.windows == (3, 6, 12, 24)

    def test_default_operations(self) -> None:
        cfg = RollingConfig()
        assert "mean" in cfg.operations
        assert "std" in cfg.operations
        assert "min" in cfg.operations
        assert "max" in cfg.operations


class TestSplitConfig:
    """Tests for SplitConfig."""

    def test_default_ratios(self) -> None:
        cfg = SplitConfig()
        assert cfg.train_ratio == 0.70
        assert cfg.val_ratio == 0.15
        assert cfg.test_ratio == 0.15

    def test_ratios_sum_to_one(self) -> None:
        cfg = SplitConfig()
        total = cfg.train_ratio + cfg.val_ratio + cfg.test_ratio
        assert abs(total - 1.0) < 1e-6

    def test_invalid_ratios(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            SplitConfig(train_ratio=0.5, val_ratio=0.3, test_ratio=0.3)

    def test_gap_hours(self) -> None:
        cfg = SplitConfig(gap_hours=48)
        assert cfg.gap_hours == 48


class TestAlignmentConfig:
    """Tests for AlignmentConfig."""

    def test_default_freq(self) -> None:
        cfg = AlignmentConfig()
        assert cfg.freq == "1h"

    def test_default_timezone(self) -> None:
        cfg = AlignmentConfig()
        assert cfg.timezone == "Asia/Karachi"


class TestDatasetConfig:
    """Tests for DatasetConfig (master config)."""

    def test_schema_version(self) -> None:
        cfg = DatasetConfig()
        assert cfg.schema_version == "1.0.0"

    def test_all_feature_names_count(self) -> None:
        cfg = DatasetConfig()
        names = cfg.all_feature_names
        assert len(names) > 0
        # Should have weather + lag + rolling + temporal features
        assert any("lag" in n for n in names)
        assert any("roll" in n for n in names)
        assert any("sin" in n for n in names)

    def test_frozen(self) -> None:
        cfg = DatasetConfig()
        with pytest.raises(AttributeError):
            cfg.schema_version = "2.0.0"  # type: ignore[misc]

    def test_target_config_inherited(self) -> None:
        cfg = DatasetConfig()
        assert cfg.target.parameter == "pm2_5"

    def test_collection_config_defaults(self) -> None:
        cfg = DatasetConfig()
        assert cfg.collection.latitude == 31.5204
        assert cfg.collection.longitude == 74.3587
