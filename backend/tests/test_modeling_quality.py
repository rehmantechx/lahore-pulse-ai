"""Tests for data quality assessment and report generation.

Verifies that quality metrics are correctly computed and that
reports are generated in both Markdown and JSON formats.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.modeling.dataset import DatasetBundle
from app.modeling.quality import (
    assess_column_quality,
    filter_target_rows,
    generate_quality_report,
)
from app.modeling.report import generate_json_report, generate_markdown_report


def _make_dataset_with_targets(hours: int = 200) -> pd.DataFrame:
    """Create a dataset with features and targets."""
    idx = pd.date_range("2024-01-01", periods=hours, freq="1h", tz="UTC")
    t = np.arange(hours, dtype=float)
    df = pd.DataFrame(
        {
            "pm2_5": 50 + 30 * np.sin(2 * np.pi * t / 24),
            "temperature_2m": 20 + 10 * np.sin(2 * np.pi * t / 24),
            "pm2_5_lag_1h": np.concatenate([[np.nan], 50 + 30 * np.sin(2 * np.pi * t[:-1] / 24)]),
            "target_pm2_5_t+1": np.concatenate(
                [50 + 30 * np.sin(2 * np.pi * t[:-1] / 24), [np.nan]]
            ),
            "target_pm2_5_t+6": np.concatenate(
                [50 + 30 * np.sin(2 * np.pi * t[:-6] / 24), [np.nan] * 6]
            ),
        },
        index=idx,
    )
    df.index.name = "time"
    return df


class TestColumnQuality:
    """Tests for assess_column_quality()."""

    def test_basic_metrics(self) -> None:
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], name="test")
        cq = assess_column_quality(s)
        assert cq.total_rows == 5
        assert cq.non_null == 5
        assert cq.null_count == 0
        assert cq.mean == pytest.approx(3.0)
        assert cq.std > 0

    def test_missing_data(self) -> None:
        s = pd.Series([1.0, np.nan, 3.0, np.nan, 5.0], name="test")
        cq = assess_column_quality(s)
        assert cq.null_count == 2
        assert cq.missing_ratio == pytest.approx(0.4)

    def test_outlier_detection(self) -> None:
        values = [1.0] * 20 + [1000.0]  # one extreme outlier
        s = pd.Series(values, name="test")
        cq = assess_column_quality(s, outlier_zscore=3.0)
        assert cq.outlier_count >= 1

    def test_empty_series(self) -> None:
        s = pd.Series(dtype=float, name="empty")
        cq = assess_column_quality(s)
        assert cq.total_rows == 0
        assert cq.missing_ratio == 1.0


class TestQualityReport:
    """Tests for generate_quality_report()."""

    def test_basic_report(self) -> None:
        df = _make_dataset_with_targets()
        report = generate_quality_report(df)
        assert report.total_rows == 200
        assert report.total_columns > 0
        assert report.quality_score > 0

    def test_target_columns_identified(self) -> None:
        df = _make_dataset_with_targets()
        report = generate_quality_report(df)
        assert len(report.target_columns_present) == 2

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        report = generate_quality_report(df)
        assert report.total_rows == 0
        assert "DataFrame is empty" in report.errors

    def test_quality_score_range(self) -> None:
        df = _make_dataset_with_targets()
        report = generate_quality_report(df)
        assert 0.0 <= report.quality_score <= 1.0


class TestFilterTargetRows:
    """Tests for filter_target_rows()."""

    def test_removes_nan_targets(self) -> None:
        df = _make_dataset_with_targets()
        filtered = filter_target_rows(df, "target_pm2_5_t+1")
        assert not filtered["target_pm2_5_t+1"].isna().any()

    def test_missing_column(self) -> None:
        df = _make_dataset_with_targets()
        filtered = filter_target_rows(df, "nonexistent_column")
        assert len(filtered) == len(df)


class TestReportGeneration:
    """Tests for Markdown and JSON report generation."""

    def _make_bundle(self) -> DatasetBundle:
        df = _make_dataset_with_targets()
        from app.modeling.config import DatasetConfig

        cfg = DatasetConfig()
        return DatasetBundle(
            config=cfg,
            full_dataset=df,
            train=df.iloc[:140],
            validation=df.iloc[140:170],
            test=df.iloc[170:200],
            leakage_report={"passed": True, "checks": {}, "total_errors": 0},
            quality_report=generate_quality_report(df),
            split_description={},
            metadata={"test": True},
        )

    def test_markdown_report(self) -> None:
        bundle = self._make_bundle()
        report = generate_markdown_report(bundle)
        assert "# Phase 2" in report
        assert "Executive Summary" in report
        assert "Feature Inventory" in report
        assert "Leakage Detection" in report

    def test_json_report(self) -> None:
        bundle = self._make_bundle()
        report = generate_json_report(bundle)
        assert "summary" in report
        assert "leakage_report" in report
        assert "column_quality" in report
        # Should be JSON-serializable
        json_str = json.dumps(report, default=str)
        assert len(json_str) > 0

    def test_json_serializable(self) -> None:
        bundle = self._make_bundle()
        report = generate_json_report(bundle)
        # Should not raise
        serialized = json.dumps(report, default=str)
        assert isinstance(serialized, str)
