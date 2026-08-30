"""Data quality assessment — missing data, outliers, and dataset statistics.

Provides comprehensive quality metrics for the assembled dataset.
Does NOT modify data — only inspects and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import TargetConfig


@dataclass
class ColumnQuality:
    """Quality metrics for a single column."""

    name: str
    total_rows: int = 0
    non_null: int = 0
    null_count: int = 0
    missing_ratio: float = 0.0
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    p25: float = 0.0
    p50: float = 0.0
    p75: float = 0.0
    negative_count: int = 0
    zero_count: int = 0
    unique_count: int = 0
    outlier_count: int = 0  # z-score > 4


@dataclass
class DatasetQualityReport:
    """Comprehensive quality report for the assembled dataset."""

    total_rows: int = 0
    total_columns: int = 0
    date_range_start: str = ""
    date_range_end: str = ""
    duration_hours: int = 0
    columns: list[ColumnQuality] = field(default_factory=list)
    target_columns_present: list[str] = field(default_factory=list)
    feature_columns_count: int = 0
    overall_missing_ratio: float = 0.0
    quality_score: float = 0.0  # 0.0 (terrible) to 1.0 (perfect)
    errors: list[str] = field(default_factory=list)


def assess_column_quality(
    series: pd.Series,
    outlier_zscore: float = 4.0,
) -> ColumnQuality:
    """Compute quality metrics for a single column.

    Args:
        series: Data series to assess.
        outlier_zscore: Z-score threshold for outlier detection.

    Returns:
        ColumnQuality with all metrics populated.
    """
    total = len(series)
    non_null = int(series.count())
    null_count = total - non_null
    valid = series.dropna()

    cq = ColumnQuality(
        name=str(series.name) if series.name is not None else "unknown",
        total_rows=total,
        non_null=non_null,
        null_count=null_count,
        missing_ratio=round(null_count / total, 4) if total > 0 else 1.0,
    )

    if len(valid) > 0:
        numeric = valid.astype(float)
        cq.mean = round(float(numeric.mean()), 4)
        cq.std = round(float(numeric.std()), 4)
        cq.min_val = round(float(numeric.min()), 4)
        cq.max_val = round(float(numeric.max()), 4)
        cq.p25 = round(float(numeric.quantile(0.25)), 4)
        cq.p50 = round(float(numeric.quantile(0.50)), 4)
        cq.p75 = round(float(numeric.quantile(0.75)), 4)
        cq.negative_count = int((numeric < 0).sum())
        cq.zero_count = int((numeric == 0).sum())
        cq.unique_count = int(numeric.nunique())

        # Outlier detection via z-score
        if cq.std > 0:
            zscores = np.abs((numeric - cq.mean) / cq.std)
            cq.outlier_count = int((zscores > outlier_zscore).sum())

    return cq


def generate_quality_report(
    df: pd.DataFrame,
    target_config: TargetConfig | None = None,
) -> DatasetQualityReport:
    """Generate a comprehensive quality report for the dataset.

    Args:
        df: The assembled dataset DataFrame.
        target_config: Target configuration for identifying target columns.

    Returns:
        DatasetQualityReport with all quality metrics.
    """
    report = DatasetQualityReport()

    if df.empty:
        report.errors.append("DataFrame is empty")
        return report

    report.total_rows = len(df)
    report.total_columns = len(df.columns)

    # Date range
    if hasattr(df.index, "min") and df.index.min() is not pd.NaT:
        report.date_range_start = str(df.index.min())
        report.date_range_end = str(df.index.max())
        delta = df.index.max() - df.index.min()
        report.duration_hours = int(delta.total_seconds() / 3600)

    # Per-column quality
    target_cols = [c for c in df.columns if c.startswith("target_")]
    feature_cols = [c for c in df.columns if c not in target_cols]
    report.target_columns_present = target_cols
    report.feature_columns_count = len(feature_cols)

    for col in df.columns:
        cq = assess_column_quality(df[col])
        report.columns.append(cq)

    # Overall missing ratio
    total_cells = report.total_rows * report.total_columns
    total_missing = int(df.isna().sum().sum())
    report.overall_missing_ratio = round(total_missing / total_cells, 4) if total_cells > 0 else 1.0

    # Quality score: composite metric
    # Penalties: missing data, outliers, short duration
    score = 1.0
    score -= report.overall_missing_ratio * 0.3  # up to -0.30 for missing
    outlier_total = sum(cq.outlier_count for cq in report.columns)
    if total_cells > 0:
        score -= (outlier_total / total_cells) * 0.2  # up to -0.20 for outliers
    if report.duration_hours < 168:  # less than 1 week
        score -= 0.2
    elif report.duration_hours < 720:  # less than 30 days
        score -= 0.1
    report.quality_score = round(max(0.0, score), 3)

    return report


def filter_target_rows(
    df: pd.DataFrame,
    target_col: str,
) -> pd.DataFrame:
    """Remove rows where the target column is NaN.

    Feature-lag NaN rows are kept (they will be trimmed later),
    but rows with NaN targets cannot be used for training.

    Args:
        df: Dataset DataFrame.
        target_col: Name of the target column.

    Returns:
        DataFrame with NaN-target rows removed.
    """
    if target_col not in df.columns:
        return df
    return df.dropna(subset=[target_col])
