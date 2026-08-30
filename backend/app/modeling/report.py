"""Quality report generation — Markdown and JSON output.

Generates human-readable Markdown and machine-readable JSON reports
documenting dataset composition, quality metrics, and leakage status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .dataset import DatasetBundle


def generate_markdown_report(bundle: DatasetBundle) -> str:
    """Generate a comprehensive Markdown quality report.

    Sections:
        1. Executive Summary
        2. Dataset Configuration
        3. Data Collection
        4. Temporal Alignment
        5. Feature Inventory
        6. Target Construction
        7. Dataset Splits
        8. Data Quality Assessment
        9. Leakage Detection
        10. Limitations and Recommendations

    Args:
        bundle: The completed DatasetBundle.

    Returns:
        Markdown-formatted report string.
    """
    lines: list[str] = []
    qr = bundle.quality_report

    # ── Header ────────────────────────────────────────────────────────
    lines.append("# Phase 2 — Historical Modeling Dataset Report")
    lines.append("")
    lines.append("**Project**: Lahore Pulse AI — Predictive City-Intelligence Platform")
    lines.append("**Phase**: 2 (Historical Modeling Dataset, Temporal Alignment,")
    lines.append("Feature Engineering & Leakage Prevention)")
    lines.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Schema Version**: {bundle.config.schema_version}")
    lines.append("")

    # ── 1. Executive Summary ──────────────────────────────────────────
    lines.append("---")
    lines.append("## 1. Executive Summary")
    lines.append("")

    leakage_passed = bundle.leakage_report.get("passed", False)
    quality_score = qr.quality_score
    lines.append(
        f"- **Dataset status**: {'✅ COMPLETE' if qr.total_rows > 0 else '⚠️  INSUFFICIENT'}"
    )
    lines.append(f"- **Quality score**: {quality_score:.3f} / 1.000")
    lines.append(f"- **Total rows**: {qr.total_rows:,}")
    lines.append(f"- **Total columns**: {qr.total_columns}")
    lines.append(f"- **Date range**: {qr.date_range_start} → {qr.date_range_end}")
    lines.append(f"- **Duration**: {qr.duration_hours:,} hours")
    lines.append(f"- **Leakage checks**: {'✅ PASSED' if leakage_passed else '❌ FAILED'}")
    lines.append("")

    # ── 2. Dataset Configuration ──────────────────────────────────────
    lines.append("---")
    lines.append("## 2. Dataset Configuration")
    lines.append("")
    cfg = bundle.config
    lines.append(f"- **Target parameter**: {cfg.target.parameter} ({cfg.target.unit})")
    lines.append(f"- **Forecast horizons**: {cfg.target.horizons_hours}")
    lines.append(f"- **Alignment frequency**: {cfg.alignment.freq}")
    lines.append(
        f"- **Train/Val/Test split**: {cfg.splits.train_ratio}/{cfg.splits.val_ratio}/{cfg.splits.test_ratio}"
    )
    lines.append(f"- **Gap buffer**: {cfg.splits.gap_hours} hours")
    lines.append(f"- **Min training hours**: {cfg.splits.min_train_hours}")
    lines.append("")

    # ── 3. Data Collection ────────────────────────────────────────────
    lines.append("---")
    lines.append("## 3. Data Collection")
    lines.append("")
    meta = bundle.metadata
    lines.append("- **Source**: Open-Meteo (ECMWF IFS + CAMS)")
    lines.append(f"- **Location**: ({cfg.collection.latitude}, {cfg.collection.longitude})")
    weather_obs = meta.get("weather_observations", "N/A")
    lines.append(
        f"- **Weather observations**: {weather_obs:,}"
        if isinstance(weather_obs, int)
        else f"- **Weather observations**: {weather_obs}"
    )
    aq_obs = meta.get("aq_observations", "N/A")
    lines.append(
        f"- **AQ observations**: {aq_obs:,}"
        if isinstance(aq_obs, int)
        else f"- **AQ observations**: {aq_obs}"
    )
    total_obs = meta.get("total_observations_loaded", "N/A")
    lines.append(
        f"- **Total loaded**: {total_obs:,}"
        if isinstance(total_obs, int)
        else f"- **Total loaded**: {total_obs}"
    )
    lines.append("")

    # ── 4. Temporal Alignment ─────────────────────────────────────────
    lines.append("---")
    lines.append("## 4. Temporal Alignment")
    lines.append("")
    align = bundle.alignment_stats
    if align:
        lines.append(f"- **Original rows**: {align.get('original_rows', 'N/A'):,}")
        lines.append(f"- **Aligned rows**: {align.get('aligned_rows', 'N/A'):,}")
        lines.append(f"- **Expansion ratio**: {align.get('expansion_ratio', 'N/A')}")
        per_col = align.get("per_column", {})
        if per_col:
            lines.append("")
            lines.append("| Parameter | Missing Ratio | Max Gap (h) | Gap Count |")
            lines.append("|-----------|---------------|-------------|-----------|")
            per_col_dict: dict[str, dict[str, object]] = per_col  # type: ignore[assignment]
            for col_name, stats in per_col_dict.items():
                mr = stats.get("missing_ratio", 0)
                mg = stats.get("max_gap_length", 0)
                gc = stats.get("gap_count", 0)
                lines.append(f"| {col_name} | {mr:.2%} | {mg} | {gc} |")
    else:
        lines.append("- No alignment statistics available")
    lines.append("")

    # ── 5. Feature Inventory ──────────────────────────────────────────
    lines.append("---")
    lines.append("## 5. Feature Inventory")
    lines.append("")

    all_cols = list(bundle.full_dataset.columns)
    target_cols = [c for c in all_cols if c.startswith("target_")]
    feature_cols = [c for c in all_cols if c not in target_cols]

    lines.append(f"**Total feature columns**: {len(feature_cols)}")
    lines.append(f"**Total target columns**: {len(target_cols)}")
    lines.append("")

    # Feature categories
    lag_cols = [c for c in feature_cols if "_lag_" in c]
    roll_cols = [c for c in feature_cols if "_roll_" in c]
    temporal_cols = [
        c
        for c in feature_cols
        if c in ("hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos")
    ]
    weather_cols = [c for c in feature_cols if c in cfg.features.weather.variables]
    wind_cols = [c for c in feature_cols if c in ("wind_dir_sin", "wind_dir_cos")]
    derived_cols = [
        c
        for c in feature_cols
        if c
        in (
            "heat_index",
            "temp_humidity_interaction",
            "pressure_change",
            "precipitation_accumulated_3h",
        )
    ]

    lines.append("| Category | Count | Examples |")
    lines.append("|----------|-------|----------|")
    lines.append(
        f"| Weather (raw) | {len(weather_cols)} | {', '.join(weather_cols[:3])}{'...' if len(weather_cols) > 3 else ''} |"
    )
    lines.append(f"| Wind decomposition | {len(wind_cols)} | {', '.join(wind_cols)} |")
    lines.append(
        f"| Derived | {len(derived_cols)} | {', '.join(derived_cols[:3])}{'...' if len(derived_cols) > 3 else ''} |"
    )
    lines.append(
        f"| Lag features | {len(lag_cols)} | {', '.join(lag_cols[:3])}{'...' if len(lag_cols) > 3 else ''} |"
    )
    lines.append(
        f"| Rolling features | {len(roll_cols)} | {', '.join(roll_cols[:3])}{'...' if len(roll_cols) > 3 else ''} |"
    )
    lines.append(f"| Temporal (cyclical) | {len(temporal_cols)} | {', '.join(temporal_cols)} |")
    lines.append("")

    # ── 6. Target Construction ────────────────────────────────────────
    lines.append("---")
    lines.append("## 6. Target Construction")
    lines.append("")
    for tcol in target_cols:
        if tcol in bundle.full_dataset.columns:
            series = bundle.full_dataset[tcol]
            non_null = series.dropna()
            lines.append(f"### `{tcol}`")
            lines.append(f"- Valid observations: {len(non_null):,} / {len(series):,}")
            if len(non_null) > 0:
                lines.append(f"- Mean: {non_null.mean():.2f} μg/m³")
                lines.append(f"- Std: {non_null.std():.2f} μg/m³")
                lines.append(f"- Min: {non_null.min():.2f} μg/m³")
                lines.append(f"- Max: {non_null.max():.2f} μg/m³")
            lines.append("")

    # ── 7. Dataset Splits ─────────────────────────────────────────────
    lines.append("---")
    lines.append("## 7. Dataset Splits")
    lines.append("")
    sd = bundle.split_description
    if "error" in sd:
        lines.append(f"⚠️  Split error: {sd['error']}")
    else:
        lines.append("| Split | Rows | Start | End | Duration (h) |")
        lines.append("|-------|------|-------|-----|--------------|")
        for name in ("train", "validation", "test"):
            info = sd.get(name, {})
            rows = info.get("rows", 0)
            start = info.get("start", "N/A")
            end = info.get("end", "N/A")
            dur = info.get("duration_hours", 0)
            lines.append(f"| {name} | {rows:,} | {start} | {end} | {dur} |")
    lines.append("")

    # ── 8. Data Quality Assessment ────────────────────────────────────
    lines.append("---")
    lines.append("## 8. Data Quality Assessment")
    lines.append("")
    lines.append(f"- **Overall missing ratio**: {qr.overall_missing_ratio:.2%}")
    lines.append(f"- **Quality score**: {qr.quality_score:.3f}")
    lines.append("")

    if qr.columns:
        lines.append("| Parameter | Non-Null | Missing | Mean | Std | Outliers |")
        lines.append("|-----------|----------|---------|------|-----|----------|")
        for cq in qr.columns:
            lines.append(
                f"| {cq.name} | {cq.non_null:,} | {cq.null_count:,} "
                f"| {cq.mean:.2f} | {cq.std:.2f} | {cq.outlier_count} |"
            )
    lines.append("")

    # ── 9. Leakage Detection ──────────────────────────────────────────
    lines.append("---")
    lines.append("## 9. Leakage Detection")
    lines.append("")
    checks = bundle.leakage_report.get("checks", {})
    total_errors = bundle.leakage_report.get("total_errors", 0)
    lines.append(f"**Total violations**: {total_errors}")
    lines.append("")

    check_names = {
        "future_mutation": "Future-Mutation Test",
        "target_isolation": "Target-Isolation Test",
        "temporal_order": "Temporal-Order Test",
        "rolling_causality": "Rolling-Window Causality Test",
        "split_separation": "Split-Separation Test",
    }

    lines.append("| Check | Status | Details |")
    lines.append("|-------|--------|---------|")
    for key, label in check_names.items():
        check_info = checks.get(key, {})  # type: ignore[attr-defined]
        passed = check_info.get("passed", False)
        errors = check_info.get("errors", [])
        status = "✅ PASS" if passed else "❌ FAIL"
        detail = "; ".join(errors) if errors else "—"
        lines.append(f"| {label} | {status} | {detail} |")
    lines.append("")

    # ── 10. Limitations ───────────────────────────────────────────────
    lines.append("---")
    lines.append("## 10. Limitations and Recommendations")
    lines.append("")

    if qr.total_rows < 720:
        lines.append(
            "- ⚠️  **Insufficient data**: The dataset contains fewer than 720 hours "
            "(30 days) of observations. A minimum of 30 days is recommended for "
            "meaningful feature engineering and model training."
        )
    if qr.overall_missing_ratio > 0.10:
        lines.append(
            f"- ⚠️  **High missing ratio**: {qr.overall_missing_ratio:.1%} of values "
            "are missing. Consider collecting more data or using interpolation."
        )
    if qr.quality_score < 0.7:
        lines.append(
            f"- ⚠️  **Low quality score**: {qr.quality_score:.3f} indicates "
            "significant data quality issues."
        )

    lines.append("")
    lines.append("### Recommended Next Steps (Phase 3)")
    lines.append("")
    lines.append("1. Collect at least 6 months of historical data for seasonal coverage.")
    lines.append("2. Incorporate OpenAQ ground-truth PM2.5 measurements.")
    lines.append("3. Train and evaluate baseline models (ARIMA, XGBoost, LSTM).")
    lines.append("4. Implement real-time prediction serving.")
    lines.append("")
    lines.append("---")
    lines.append("*Report generated by the Lahore Pulse AI modeling pipeline.*")

    return "\n".join(lines)


def generate_json_report(bundle: DatasetBundle) -> dict[str, Any]:
    """Generate a machine-readable JSON quality report.

    Args:
        bundle: The completed DatasetBundle.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    qr = bundle.quality_report
    return {
        "schema_version": bundle.config.schema_version,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_rows": qr.total_rows,
            "total_columns": qr.total_columns,
            "date_range_start": qr.date_range_start,
            "date_range_end": qr.date_range_end,
            "duration_hours": qr.duration_hours,
            "quality_score": qr.quality_score,
            "overall_missing_ratio": qr.overall_missing_ratio,
        },
        "metadata": bundle.metadata,
        "leakage_report": bundle.leakage_report,
        "split_description": bundle.split_description,
        "alignment_stats": bundle.alignment_stats,
        "column_quality": [
            {
                "name": cq.name,
                "non_null": cq.non_null,
                "null_count": cq.null_count,
                "missing_ratio": cq.missing_ratio,
                "mean": cq.mean,
                "std": cq.std,
                "min": cq.min_val,
                "max": cq.max_val,
                "outlier_count": cq.outlier_count,
            }
            for cq in qr.columns
        ],
    }
