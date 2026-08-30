"""Evaluation — temporal validation, walk-forward backtesting, error analysis.

Implements chronological evaluation strategies that respect the temporal
ordering of time-series data. No future information is allowed to leak
into any training window.

Evaluation strategies:
    1. Fixed chronological split (train / val / test)
    2. Walk-forward (rolling origin) backtesting
    3. Error analysis by time, season, and pollution level
    4. Extreme-event (high-pollution) performance assessment
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.pipeline import Pipeline

from .models import (
    compute_metrics,
    load_model_artifact,
    predict_model,
    train_model,
)


# ── Chronological Split ──────────────────────────────────────────────


@dataclass
class ChronologicalSplit:
    """Container for chronologically-split datasets."""

    X_train: pd.DataFrame | None = None
    y_train: pd.Series | None = None
    X_val: pd.DataFrame | None = None
    y_val: pd.Series | None = None
    X_test: pd.DataFrame | None = None
    y_test: pd.Series | None = None

    # Time boundaries
    train_start: str = ""
    train_end: str = ""
    val_start: str = ""
    val_end: str = ""
    test_start: str = ""
    test_end: str = ""

    # Gap info
    gap_train_val_hours: int = 0
    gap_val_test_hours: int = 0

    @property
    def total_rows(self) -> int:
        """Sum of rows across all splits."""
        count = 0
        for df in [self.X_train, self.X_val, self.X_test]:
            if df is not None:
                count += len(df)
        return count

    def describe(self) -> dict[str, Any]:
        """Describe the split."""
        return {
            "train_rows": len(self.X_train) if self.X_train is not None else 0,
            "val_rows": len(self.X_val) if self.X_val is not None else 0,
            "test_rows": len(self.X_test) if self.X_test is not None else 0,
            "total_rows": self.total_rows,
            "train_period": f"{self.train_start} → {self.train_end}",
            "val_period": f"{self.val_start} → {self.val_end}",
            "test_period": f"{self.test_start} → {self.test_end}",
            "gap_train_val_hours": self.gap_train_val_hours,
            "gap_val_test_hours": self.gap_val_test_hours,
        }


def chronological_train_val_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    gap_hours: int = 72,
) -> ChronologicalSplit:
    """Split X, y into chronological train / validation / test.

    The split respects:
        - Strict chronological ordering
        - A gap between splits to prevent lag-feature leakage
        - No shuffling

    Args:
        X: Feature DataFrame with DatetimeIndex.
        y: Target Series with matching DatetimeIndex.
        train_ratio: Fraction of data for training.
        val_ratio: Fraction for validation (test gets the rest).
        gap_hours: Buffer between splits (in hours).

    Returns:
        ChronologicalSplit with all partitions.
    """
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    # Apply gap buffer
    gap_tv_start = train_end
    gap_tv_end = min(train_end + gap_hours, n)

    gap_vt_start = val_end
    gap_vt_end = min(val_end + gap_hours, n)

    split = ChronologicalSplit(
        X_train=X.iloc[:train_end].copy(),
        y_train=y.iloc[:train_end].copy(),
        X_val=X.iloc[gap_tv_end:gap_vt_start].copy(),
        y_val=y.iloc[gap_tv_end:gap_vt_start].copy(),
        X_test=X.iloc[gap_vt_end:].copy(),
        y_test=y.iloc[gap_vt_end:].copy(),
        train_start=str(X.index[0]),
        train_end=str(X.index[train_end - 1]) if train_end > 0 else "",
        val_start=str(X.index[gap_tv_end]) if gap_tv_end < gap_vt_start else "",
        val_end=str(X.index[gap_vt_start - 1]) if gap_vt_start > gap_tv_end else "",
        test_start=str(X.index[gap_vt_end]) if gap_vt_end < n else "",
        test_end=str(X.index[-1]),
        gap_train_val_hours=gap_tv_end - gap_tv_start,
        gap_val_test_hours=gap_vt_end - gap_vt_start,
    )

    logger.info(
        "Chronological split created",
        train=len(split.X_train),
        val=len(split.X_val),
        test=len(split.X_test),
        gap_tv=split.gap_train_val_hours,
        gap_vt=split.gap_val_test_hours,
    )

    return split


# ── Walk-Forward Backtesting ─────────────────────────────────────────


@dataclass
class WalkForwardFold:
    """Single fold from walk-forward backtesting."""

    fold_id: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_rows: int
    test_rows: int
    metrics: dict[str, float] = field(default_factory=dict)
    predictions: np.ndarray | None = None
    actuals: np.ndarray | None = None


@dataclass
class WalkForwardResult:
    """Aggregated results from walk-forward backtesting."""

    folds: list[WalkForwardFold] = field(default_factory=list)
    aggregate_metrics: dict[str, float] = field(default_factory=dict)
    fold_metrics: list[dict[str, float]] = field(default_factory=list)
    stability_score: float = 0.0  # coefficient of variation of MAE across folds

    def describe(self) -> dict[str, Any]:
        """Describe the walk-forward results."""
        return {
            "n_folds": len(self.folds),
            "aggregate_metrics": self.aggregate_metrics,
            "stability_score": self.stability_score,
            "fold_metrics": self.fold_metrics,
        }


def walk_forward_backtest(
    X: pd.DataFrame,
    y: pd.Series,
    pipeline_factory: callable,
    n_folds: int = 6,
    min_train_rows: int = 5000,
    test_window_rows: int | None = None,
    gap_hours: int = 72,
    model_name: str = "model",
) -> WalkForwardResult:
    """Perform walk-forward (rolling origin) backtesting.

    Strategy:
        Fold 1: Train on rows 0..t1, test on rows t1+gap..t2
        Fold 2: Train on rows 0..t2, test on rows t2+gap..t3
        ...
        Fold N: Train on rows 0..tN, test on rows tN+gap..end

    Each fold expands the training window (expanding window).

    Args:
        X: Full feature DataFrame with DatetimeIndex.
        y: Full target Series.
        pipeline_factory: Callable that returns a fresh sklearn Pipeline.
        n_folds: Number of walk-forward folds.
        min_train_rows: Minimum training set size.
        test_window_rows: Rows per test fold (auto-calculated if None).
        gap_hours: Gap between train and test in each fold.
        model_name: Name for logging.

    Returns:
        WalkForwardResult with per-fold and aggregate metrics.
    """
    n = len(X)

    if test_window_rows is None:
        # Available test rows after accounting for min train + gaps
        available_for_test = n - min_train_rows - (n_folds * gap_hours)
        test_window_rows = max(available_for_test // n_folds, 100)

    logger.info(
        "Walk-forward backtest starting",
        total_rows=n,
        n_folds=n_folds,
        test_window_rows=test_window_rows,
        min_train_rows=min_train_rows,
    )

    result = WalkForwardResult()
    all_mae = []

    for fold_id in range(n_folds):
        # Training window: from start to the start of this fold's test window
        train_end_idx = min_train_rows + fold_id * test_window_rows
        test_start_idx = train_end_idx + gap_hours
        test_end_idx = min(test_start_idx + test_window_rows, n)

        if test_start_idx >= n or train_end_idx >= n:
            break

        if test_end_idx - test_start_idx < 50:
            break  # Insufficient test data for this fold

        X_train_fold = X.iloc[:train_end_idx]
        y_train_fold = y.iloc[:train_end_idx]
        X_test_fold = X.iloc[test_start_idx:test_end_idx]
        y_test_fold = y.iloc[test_start_idx:test_end_idx]

        # Train fresh model
        pipeline = pipeline_factory()
        train_info = train_model(pipeline, X_train_fold, y_train_fold, f"{model_name}_fold{fold_id}")

        # Predict
        pred_info = predict_model(pipeline, X_test_fold, f"{model_name}_fold{fold_id}")
        y_pred = pred_info["predictions"]

        # Evaluate
        metrics = compute_metrics(y_test_fold.values, y_pred)

        fold = WalkForwardFold(
            fold_id=fold_id,
            train_start=str(X.index[0]),
            train_end=str(X.index[train_end_idx - 1]),
            test_start=str(X.index[test_start_idx]),
            test_end=str(X.index[test_end_idx - 1]),
            train_rows=train_end_idx,
            test_rows=test_end_idx - test_start_idx,
            metrics=metrics,
            predictions=y_pred,
            actuals=y_test_fold.values,
        )

        result.folds.append(fold)
        result.fold_metrics.append(metrics)
        all_mae.append(metrics["mae"])

        logger.info(
            f"Walk-forward fold {fold_id}",
            train_rows=train_end_idx,
            test_rows=test_end_idx - test_start_idx,
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            r2=metrics["r2"],
        )

    # Aggregate metrics (mean across folds)
    if result.fold_metrics:
        agg: dict[str, float] = {}
        for key in result.fold_metrics[0]:
            if key == "n_samples":
                agg[key] = sum(m[key] for m in result.fold_metrics)
            else:
                agg[key] = round(
                    float(np.mean([m[key] for m in result.fold_metrics])), 4
                )
        result.aggregate_metrics = agg

        # Stability: coefficient of variation of MAE across folds
        if len(all_mae) > 1:
            mae_std = float(np.std(all_mae))
            mae_mean = float(np.mean(all_mae))
            result.stability_score = round(
                mae_std / mae_mean if mae_mean > 0 else 0.0, 4
            )

    logger.info(
        "Walk-forward backtest complete",
        n_folds=len(result.folds),
        mean_mae=result.aggregate_metrics.get("mae", 0),
        stability=result.stability_score,
    )

    return result


# ── Error Analysis ───────────────────────────────────────────────────


@dataclass
class ErrorAnalysis:
    """Detailed error analysis of model predictions."""

    # Overall metrics
    overall_metrics: dict[str, float] = field(default_factory=dict)

    # By hour of day
    errors_by_hour: dict[int, dict[str, float]] = field(default_factory=dict)

    # By month
    errors_by_month: dict[str, dict[str, float]] = field(default_factory=dict)

    # By season (Lahore-specific)
    errors_by_season: dict[str, dict[str, float]] = field(default_factory=dict)

    # By pollution level
    errors_by_pollution_level: dict[str, dict[str, float]] = field(default_factory=dict)

    # Systematic bias
    bias_analysis: dict[str, Any] = field(default_factory=dict)

    # High-pollution event detection
    extreme_event_analysis: dict[str, Any] = field(default_factory=dict)


def _lahore_season(month: int) -> str:
    """Map month to Lahore season."""
    if month in (11, 12, 1, 2):
        return "winter"
    elif month in (3, 4):
        return "spring"
    elif month in (5, 6):
        return "summer"
    elif month in (7, 8):
        return "monsoon"
    else:  # 9, 10
        return "post_monsoon"


def analyze_errors(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    index: pd.DatetimeIndex | None = None,
    pm25_current: np.ndarray | pd.Series | None = None,
    high_pollution_threshold: float = 75.0,
) -> ErrorAnalysis:
    """Perform comprehensive error analysis.

    Analyzes model errors across:
        - Hour of day
        - Month
        - Season
        - Pollution level
        - Systematic bias (over/under-prediction)
        - Extreme event detection

    Args:
        y_true: Actual values.
        y_pred: Predicted values.
        index: DatetimeIndex for temporal analysis.
        pm25_current: Current PM2.5 values (for conditional analysis).
        high_pollution_threshold: Threshold for "high pollution" classification.

    Returns:
        ErrorAnalysis with all breakdowns.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    residuals = y_true - y_pred

    analysis = ErrorAnalysis()
    analysis.overall_metrics = compute_metrics(y_true, y_pred)

    if index is None or len(index) != len(y_true):
        return analysis

    # ── By hour of day ────────────────────────────────────────────────
    for hour in range(24):
        mask = index.hour == hour
        if mask.sum() > 10:
            analysis.errors_by_hour[hour] = compute_metrics(y_true[mask], y_pred[mask])

    # ── By month ──────────────────────────────────────────────────────
    for month in range(1, 13):
        mask = index.month == month
        if mask.sum() > 10:
            analysis.errors_by_month[f"{month:02d}"] = compute_metrics(
                y_true[mask], y_pred[mask]
            )

    # ── By season ─────────────────────────────────────────────────────
    seasons = ["winter", "spring", "summer", "monsoon", "post_monsoon"]
    for season in seasons:
        mask = pd.Series([_lahore_season(m) for m in index.month]) == season
        mask = mask.values
        if mask.sum() > 10:
            analysis.errors_by_season[season] = compute_metrics(
                y_true[mask], y_pred[mask]
            )

    # ── By pollution level ────────────────────────────────────────────
    levels = {
        "low_0_30": (0, 30),
        "moderate_30_75": (30, 75),
        "high_75_150": (75, 150),
        "very_high_150_plus": (150, float("inf")),
    }
    for level_name, (low, high) in levels.items():
        mask = (y_true >= low) & (y_true < high)
        if mask.sum() > 10:
            analysis.errors_by_pollution_level[level_name] = compute_metrics(
                y_true[mask], y_pred[mask]
            )

    # ── Bias analysis ─────────────────────────────────────────────────
    mean_bias = float(np.mean(residuals))
    analysis.bias_analysis = {
        "mean_bias": round(mean_bias, 4),
        "mean_absolute_bias": round(float(np.mean(np.abs(residuals))), 4),
        "over_prediction_fraction": round(float(np.mean(residuals < 0)), 4),
        "under_prediction_fraction": round(float(np.mean(residuals > 0)), 4),
        "bias_interpretation": (
            "model over-predicts PM2.5 on average"
            if mean_bias < 0
            else "model under-predicts PM2.5 on average"
            if mean_bias > 0
            else "no systematic bias"
        ),
    }

    # ── Extreme event analysis ────────────────────────────────────────
    high_mask = y_true >= high_pollution_threshold
    if high_mask.sum() > 0:
        high_metrics = compute_metrics(y_true[high_mask], y_pred[high_mask])
        # Detection: how many actual high-pollution events were predicted as high?
        high_predicted = y_pred >= high_pollution_threshold
        true_positives = int(np.sum(high_mask & high_predicted))
        false_negatives = int(np.sum(high_mask & ~high_predicted))
        false_positives = int(np.sum(~high_mask & high_predicted))

        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        analysis.extreme_event_analysis = {
            "threshold_ug_m3": high_pollution_threshold,
            "actual_high_events": int(high_mask.sum()),
            "predicted_high_events": int(high_predicted.sum()),
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "false_positives": false_positives,
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "f1": round(f1, 4),
            "metrics_on_high_events": high_metrics,
        }
    else:
        analysis.extreme_event_analysis = {
            "threshold_ug_m3": high_pollution_threshold,
            "actual_high_events": 0,
            "note": "No high-pollution events in the evaluation period",
        }

    return analysis


# ── Full Evaluation Pipeline ─────────────────────────────────────────


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single model."""

    model_name: str
    horizon: int

    # Split metrics
    train_metrics: dict[str, float] = field(default_factory=dict)
    val_metrics: dict[str, float] = field(default_factory=dict)
    test_metrics: dict[str, float] = field(default_factory=dict)

    # Walk-forward
    walk_forward: WalkForwardResult | None = None

    # Error analysis
    error_analysis: ErrorAnalysis | None = None

    # Baseline comparison
    baseline_metrics: dict[str, dict[str, float]] = field(default_factory=dict)

    # Training info
    train_time_seconds: float = 0.0
    predict_time_ms: float = 0.0

    def describe(self) -> dict[str, Any]:
        """Describe the evaluation result."""
        result = {
            "model_name": self.model_name,
            "horizon": self.horizon,
            "val_mae": self.val_metrics.get("mae", 0),
            "val_rmse": self.val_metrics.get("rmse", 0),
            "val_r2": self.val_metrics.get("r2", 0),
            "test_mae": self.test_metrics.get("mae", 0),
            "test_rmse": self.test_metrics.get("rmse", 0),
            "test_r2": self.test_metrics.get("r2", 0),
        }
        if self.walk_forward:
            result["wf_mae"] = self.walk_forward.aggregate_metrics.get("mae", 0)
            result["wf_stability"] = self.walk_forward.stability_score
        return result


def evaluate_model_full(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
    horizon: int,
    baseline_metrics: dict[str, dict[str, float]] | None = None,
    run_walk_forward: bool = True,
    walk_forward_factory: callable | None = None,
    n_wf_folds: int = 6,
) -> EvaluationResult:
    """Run full evaluation of a model.

    Steps:
        1. Train the model
        2. Predict on train/val/test
        3. Compute metrics for each split
        4. Run walk-forward backtest (optional)
        5. Run error analysis on test set
        6. Package results

    Args:
        pipeline: sklearn Pipeline to evaluate.
        X_train, y_train: Training data.
        X_val, y_val: Validation data.
        X_test, y_test: Test data.
        model_name: Model name for identification.
        horizon: Forecast horizon.
        baseline_metrics: Baseline metrics for comparison.
        run_walk_forward: Whether to run walk-forward backtest.
        walk_forward_factory: Factory for creating pipelines in walk-forward.
        n_wf_folds: Number of walk-forward folds.

    Returns:
        EvaluationResult with all metrics and analyses.
    """
    logger.info(f"Evaluating model: {model_name} (horizon={horizon}h)")

    # Train
    train_info = train_model(pipeline, X_train, y_train, model_name)

    # Predict on all splits
    train_pred = predict_model(pipeline, X_train, model_name)
    val_pred = predict_model(pipeline, X_val, model_name)
    test_pred = predict_model(pipeline, X_test, model_name)

    # Compute metrics
    train_metrics = compute_metrics(y_train.values, train_pred["predictions"])
    val_metrics = compute_metrics(y_val.values, val_pred["predictions"])
    test_metrics = compute_metrics(y_test.values, test_pred["predictions"])

    # Walk-forward backtesting
    walk_forward_result = None
    if run_walk_forward and walk_forward_factory is not None:
        # Combine train+val for walk-forward (test set remains untouched)
        X_wf = pd.concat([X_train, X_val])
        y_wf = pd.concat([y_train, y_val])

        walk_forward_result = walk_forward_backtest(
            X=X_wf,
            y=y_wf,
            pipeline_factory=walk_forward_factory,
            n_folds=n_wf_folds,
            model_name=model_name,
        )

    # Error analysis on test set
    error_analysis_result = analyze_errors(
        y_true=y_test.values,
        y_pred=test_pred["predictions"],
        index=y_test.index,
    )

    result = EvaluationResult(
        model_name=model_name,
        horizon=horizon,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        walk_forward=walk_forward_result,
        error_analysis=error_analysis_result,
        baseline_metrics=baseline_metrics or {},
        train_time_seconds=train_info["train_time_seconds"],
        predict_time_ms=round(test_pred["predict_time_seconds"] * 1000, 2),
    )

    logger.info(
        f"Evaluation complete: {model_name}",
        val_mae=val_metrics["mae"],
        test_mae=test_metrics["mae"],
        test_r2=test_metrics["r2"],
    )

    return result
