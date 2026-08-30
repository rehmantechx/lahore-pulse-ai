"""Tests for the dataset builder (orchestrator).

Verifies end-to-end dataset construction from a pre-existing DataFrame,
including feature engineering, target construction, splitting, and
leakage detection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.modeling.config import DatasetConfig, SplitConfig
from app.modeling.dataset import DatasetBuilder


def _make_raw_dataset(hours: int = 2000) -> pd.DataFrame:
    """Create a realistic raw weather + AQ dataset."""
    idx = pd.date_range("2024-01-01", periods=hours, freq="1h", tz="UTC")
    t = np.arange(hours, dtype=float)

    df = pd.DataFrame(
        {
            "temperature_2m": 20 + 10 * np.sin(2 * np.pi * t / 24),
            "relative_humidity_2m": 60 + 20 * np.sin(2 * np.pi * t / 24 + np.pi),
            "dew_point_2m": 10 + 5 * np.sin(2 * np.pi * t / 24),
            "apparent_temperature": 22 + 8 * np.sin(2 * np.pi * t / 24),
            "precipitation": np.maximum(0, np.sin(2 * np.pi * t / 72) * 2),
            "rain": np.maximum(0, np.sin(2 * np.pi * t / 72) * 1.8),
            "cloud_cover": 50 + 30 * np.sin(2 * np.pi * t / 48),
            "pressure_msl": 1013 + 5 * np.sin(2 * np.pi * t / 48),
            "surface_pressure": 1010 + 5 * np.sin(2 * np.pi * t / 48),
            "wind_speed_10m": 5 + 3 * np.sin(2 * np.pi * t / 12),
            "wind_direction_10m": (180 + 90 * np.sin(2 * np.pi * t / 24)) % 360,
            "wind_gusts_10m": 8 + 4 * np.sin(2 * np.pi * t / 12),
            "shortwave_radiation": np.maximum(0, 300 * np.sin(2 * np.pi * (t % 24 - 6) / 24)),
            "vapour_pressure_deficit": 1.0 + 0.5 * np.sin(2 * np.pi * t / 24),
            "soil_temperature_0_to_7cm": 15 + 8 * np.sin(2 * np.pi * t / 24),
            "soil_moisture_0_to_7cm": 0.3 + 0.1 * np.sin(2 * np.pi * t / 48),
            "pm2_5": 50 + 30 * np.sin(2 * np.pi * t / 24) + 10 * np.sin(2 * np.pi * t / (24 * 7)),
            "pm10": 80 + 40 * np.sin(2 * np.pi * t / 24),
            "nitrogen_dioxide": 20 + 10 * np.sin(2 * np.pi * t / 24),
        },
        index=idx,
    )
    df.index.name = "time"
    return df


class TestDatasetBuilder:
    """Tests for DatasetBuilder.build_from_dataframe()."""

    def test_basic_build(self) -> None:
        df = _make_raw_dataset(2000)
        builder = DatasetBuilder(
            config=DatasetConfig(
                splits=SplitConfig(gap_hours=24, min_train_hours=500),
            )
        )
        bundle = builder.build_from_dataframe(df)
        assert bundle.full_dataset is not None
        assert len(bundle.full_dataset) > 0

    def test_features_engineered(self) -> None:
        df = _make_raw_dataset(2000)
        builder = DatasetBuilder(
            config=DatasetConfig(
                splits=SplitConfig(gap_hours=24, min_train_hours=500),
            )
        )
        bundle = builder.build_from_dataframe(df)
        # Should have many more columns than input
        assert len(bundle.full_dataset.columns) > len(df.columns)

    def test_targets_present(self) -> None:
        df = _make_raw_dataset(2000)
        builder = DatasetBuilder(
            config=DatasetConfig(
                splits=SplitConfig(gap_hours=24, min_train_hours=500),
            )
        )
        bundle = builder.build_from_dataframe(df)
        target_cols = [c for c in bundle.full_dataset.columns if c.startswith("target_")]
        assert len(target_cols) > 0

    def test_splits_created(self) -> None:
        df = _make_raw_dataset(2000)
        builder = DatasetBuilder(
            config=DatasetConfig(
                splits=SplitConfig(gap_hours=24, min_train_hours=500),
            )
        )
        bundle = builder.build_from_dataframe(df)
        assert bundle.train is not None
        assert bundle.validation is not None
        assert bundle.test is not None

    def test_leakage_check_run(self) -> None:
        df = _make_raw_dataset(2000)
        builder = DatasetBuilder(
            config=DatasetConfig(
                splits=SplitConfig(gap_hours=24, min_train_hours=500),
            )
        )
        bundle = builder.build_from_dataframe(df)
        assert "passed" in bundle.leakage_report
        assert "checks" in bundle.leakage_report

    def test_quality_report_generated(self) -> None:
        df = _make_raw_dataset(2000)
        builder = DatasetBuilder(
            config=DatasetConfig(
                splits=SplitConfig(gap_hours=24, min_train_hours=500),
            )
        )
        bundle = builder.build_from_dataframe(df)
        assert bundle.quality_report.total_rows > 0
        assert bundle.quality_report.quality_score > 0

    def test_deterministic(self) -> None:
        df = _make_raw_dataset(2000)
        cfg = DatasetConfig(splits=SplitConfig(gap_hours=24, min_train_hours=500))
        b1 = DatasetBuilder(config=cfg)
        b2 = DatasetBuilder(config=cfg)
        bundle1 = b1.build_from_dataframe(df)
        bundle2 = b2.build_from_dataframe(df)
        pd.testing.assert_frame_equal(bundle1.full_dataset, bundle2.full_dataset)

    def test_empty_input(self) -> None:
        df = pd.DataFrame()
        builder = DatasetBuilder()
        bundle = builder.build_from_dataframe(df)
        assert bundle.full_dataset.empty
