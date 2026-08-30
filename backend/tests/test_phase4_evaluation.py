"""Tests for Phase 4 evaluation — temporal splits, walk-forward, error analysis.

Covers:
    - Chronological train/val/test split
    - Walk-forward expanding window backtest
    - Error analysis by time, season, pollution level
    - Evaluation result aggregation
    - No temporal overlap between splits
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.modeling.evaluation import (
    ChronologicalSplit,
    ErrorAnalysis,
    WalkForwardFold,
    WalkForwardResult,
    analyze_errors,
    chronological_train_val_test_split,
    walk_forward_backtest,
)
from app.modeling.models import build_ridge_pipeline, compute_metrics


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_xy(n: int = 1000) -> tuple[pd.DataFrame, pd.Series]:
    """Create deterministic X, y with temporal index."""
    rng = np.random.default_rng(42)
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    X = pd.DataFrame(
        rng.standard_normal((n, 5)),
        columns=[f"f{i}" for i in range(5)],
        index=idx,
    )
    y = pd.Series(
        50 + 10 * np.sin(2 * np.pi * np.arange(n) / 24) + rng.standard_normal(n) * 5,
        index=idx,
        name="pm2_5",
    )
    return X, y


# ── Chronological Split Tests ────────────────────────────────────────


class TestChronologicalSplit:
    def test_split_sizes(self) -> None:
        X, y = _make_xy(1000)
        split = chronological_train_val_test_split(X, y, train_ratio=0.7, val_ratio=0.15, gap_hours=72)
        total = len(split.X_train) + len(split.X_val) + len(split.X_test)
        # Some rows lost to gap and target shift
        assert total <= 1000
        assert len(split.X_train) > 0
        assert len(split.X_val) > 0
        assert len(split.X_test) > 0

    def test_temporal_ordering(self) -> None:
        """Train < Val < Test with gaps."""
        X, y = _make_xy(1000)
        split = chronological_train_val_test_split(X, y, train_ratio=0.7, val_ratio=0.15, gap_hours=72)
        # Train ends before Val starts (with gap)
        train_end = split.X_train.index[-1]
        val_start = split.X_val.index[0]
        assert train_end < val_start
        # Val ends before Test starts (with gap)
        val_end = split.X_val.index[-1]
        test_start = split.X_test.index[0]
        assert val_end < test_start

    def test_gap_respected(self) -> None:
        X, y = _make_xy(2000)
        gap = 48
        split = chronological_train_val_test_split(X, y, train_ratio=0.7, val_ratio=0.15, gap_hours=gap)
        train_end = split.X_train.index[-1]
        val_start = split.X_val.index[0]
        actual_gap = (val_start - train_end).total_seconds() / 3600
        assert actual_gap >= gap

    def test_no_data_leakage_between_splits(self) -> None:
        """No index overlap between train, val, test."""
        X, y = _make_xy(1000)
        split = chronological_train_val_test_split(X, y, train_ratio=0.7, val_ratio=0.15, gap_hours=72)
        train_idx = set(split.X_train.index)
        val_idx = set(split.X_val.index)
        test_idx = set(split.X_test.index)
        assert len(train_idx & val_idx) == 0
        assert len(train_idx & test_idx) == 0
        assert len(val_idx & test_idx) == 0

    def test_describe(self) -> None:
        X, y = _make_xy(1000)
        split = chronological_train_val_test_split(X, y)
        desc = split.describe()
        assert "train_rows" in desc
        assert "val_rows" in desc
        assert "test_rows" in desc
        assert "train_period" in desc

    def test_different_ratios(self) -> None:
        X, y = _make_xy(2000)
        split = chronological_train_val_test_split(X, y, train_ratio=0.5, val_ratio=0.25, gap_hours=24)
        assert len(split.X_train) > len(split.X_val)


# ── Walk-Forward Backtest Tests ──────────────────────────────────────


class TestWalkForward:
    def test_returns_multiple_folds(self) -> None:
        X, y = _make_xy(2000)
        result = walk_forward_backtest(
            X, y,
            pipeline_factory=build_ridge_pipeline,
            n_folds=3,
            min_train_rows=500,
            gap_hours=24,
        )
        assert len(result.folds) == 3

    def test_expanding_window(self) -> None:
        """Each fold should have more training data than the previous."""
        X, y = _make_xy(3000)
        result = walk_forward_backtest(
            X, y,
            pipeline_factory=build_ridge_pipeline,
            n_folds=4,
            min_train_rows=500,
            gap_hours=24,
        )
        train_sizes = [f.train_rows for f in result.folds]
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] >= train_sizes[i - 1]

    def test_aggregate_metrics(self) -> None:
        X, y = _make_xy(2000)
        result = walk_forward_backtest(
            X, y,
            pipeline_factory=build_ridge_pipeline,
            n_folds=3,
            min_train_rows=500,
            gap_hours=24,
        )
        agg = result.aggregate_metrics
        assert "mae" in agg
        assert "rmse" in agg
        assert agg["mae"] > 0
        assert result.stability_score >= 0

    def test_fold_has_test_predictions(self) -> None:
        X, y = _make_xy(2000)
        result = walk_forward_backtest(
            X, y,
            pipeline_factory=build_ridge_pipeline,
            n_folds=2,
            min_train_rows=500,
            gap_hours=24,
        )
        for fold in result.folds:
            assert fold.predictions is not None
            assert fold.actuals is not None
            assert len(fold.predictions) > 0
            assert len(fold.actuals) > 0
            assert len(fold.predictions) == len(fold.actuals)


# ── Error Analysis Tests ─────────────────────────────────────────────


class TestErrorAnalysis:
    def test_analyze_errors(self) -> None:
        rng = np.random.default_rng(42)
        n = 500
        idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
        y_true = pd.Series(rng.uniform(10, 200, n), index=idx)
        y_pred = y_true + rng.normal(0, 5, n)

        analysis = analyze_errors(y_true.values, y_pred.values, idx)
        assert isinstance(analysis, ErrorAnalysis)
        assert "mae" in analysis.overall_metrics
        assert "mean_bias" in analysis.bias_analysis

    def test_seasonal_breakdown(self) -> None:
        rng = np.random.default_rng(42)
        n = 8760  # full year
        idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
        y_true = pd.Series(rng.uniform(10, 200, n), index=idx)
        y_pred = y_true + rng.normal(0, 5, n)

        analysis = analyze_errors(y_true.values, y_pred.values, idx)
        # Should have breakdowns for multiple seasons
        assert len(analysis.errors_by_season) > 0

    def test_error_analysis_fields(self) -> None:
        rng = np.random.default_rng(42)
        n = 200
        idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
        y_true = pd.Series(rng.uniform(10, 200, n), index=idx)
        y_pred = y_true + rng.normal(0, 5, n)

        analysis = analyze_errors(y_true.values, y_pred.values, idx)
        assert "mae" in analysis.overall_metrics
        assert "rmse" in analysis.overall_metrics
        assert "mean_bias" in analysis.bias_analysis
        assert analysis.overall_metrics["n_samples"] == n
