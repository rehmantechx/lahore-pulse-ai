"""Dataset builder — orchestrates the full data preparation pipeline.

End-to-end workflow:
    1. Load observations from the database.
    2. Pivot to wide format (one column per parameter).
    3. Align to hourly UTC grid.
    4. Build target variables (future PM2.5 horizons).
    5. Engineer features (lags, rolling, temporal, weather).
    6. Split chronologically (train / val / test).
    7. Run leakage detection.
    8. Generate quality report.
    9. Package into a versioned DatasetBundle.

This module does NOT train models or fit transformers.
All transformations are deterministic and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd
from loguru import logger

from .alignment import (
    align_to_hourly_grid,
    compute_alignment_stats,
    observations_to_dataframe,
)
from .collector import DataCollector
from .config import DatasetConfig
from .features import build_features
from .leakage import run_all_leakage_checks
from .quality import DatasetQualityReport, generate_quality_report
from .splits import DatasetSplits, chronological_split, describe_splits
from .targets import build_targets


@dataclass
class DatasetBundle:
    """Container for the complete modeling dataset and its metadata.

    Attributes:
        config: The dataset configuration used to generate this bundle.
        full_dataset: The complete assembled DataFrame (features + targets).
        train: Training split DataFrame.
        validation: Validation split DataFrame.
        test: Test split DataFrame.
        leakage_report: Results of all leakage checks.
        quality_report: Dataset quality assessment.
        split_description: Statistics for each split.
        alignment_stats: Temporal alignment statistics.
        metadata: Additional provenance information.
    """

    config: DatasetConfig
    full_dataset: pd.DataFrame
    train: pd.DataFrame | None = None
    validation: pd.DataFrame | None = None
    test: pd.DataFrame | None = None
    leakage_report: dict[str, object] = field(default_factory=dict)
    quality_report: DatasetQualityReport = field(default_factory=DatasetQualityReport)
    split_description: dict[str, dict[str, object]] = field(default_factory=dict)
    alignment_stats: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class DatasetBuilder:
    """Orchestrates the full dataset generation pipeline.

    Usage:
        builder = DatasetBuilder(config, collector)
        bundle = await builder.build(start_date, end_date)
    """

    def __init__(
        self,
        config: DatasetConfig | None = None,
        collector: DataCollector | None = None,
    ) -> None:
        self._config = config or DatasetConfig()
        self._collector = collector

    async def build(
        self,
        start: date,
        end: date,
    ) -> DatasetBundle:
        """Build the complete modeling dataset.

        Steps:
            1. Collect weather + AQ data from Open-Meteo.
            2. Load observations from DB.
            3. Pivot to wide format.
            4. Align to hourly grid.
            5. Build features.
            6. Build targets.
            7. Split chronologically.
            8. Run leakage checks.
            9. Generate quality report.
            10. Package into DatasetBundle.

        Args:
            start: Start date for data collection.
            end: End date for data collection.

        Returns:
            DatasetBundle with all artifacts.
        """
        logger.info(
            "Building dataset",
            start=start.isoformat(),
            end=end.isoformat(),
        )

        metadata: dict[str, Any] = {
            "schema_version": self._config.schema_version,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "built_at": pd.Timestamp.now(tz="UTC").isoformat(),
        }

        # Step 1: Collect data
        if self._collector is not None:
            weather_count = await self._collector.collect_weather_data(start, end)
            aq_count = await self._collector.collect_aq_data(start, end)
            metadata["weather_observations"] = weather_count
            metadata["aq_observations"] = aq_count
            logger.info(
                "Data collection complete",
                weather=weather_count,
                aq=aq_count,
            )

        # Step 2: Load from DB
        if self._collector is None:
            raise ValueError("DataCollector is required for dataset building")

        all_obs = self._collector.load_observations()
        if not all_obs:
            logger.error("No observations found in database")
            return DatasetBundle(
                config=self._config,
                full_dataset=pd.DataFrame(),
                metadata=metadata,
            )

        metadata["total_observations_loaded"] = len(all_obs)
        logger.info("Loaded observations from DB", count=len(all_obs))

        # Step 3: Pivot to wide format
        df = observations_to_dataframe(all_obs)
        if df.empty:
            logger.error("Failed to pivot observations to wide format")
            return DatasetBundle(
                config=self._config,
                full_dataset=pd.DataFrame(),
                metadata=metadata,
            )

        metadata["raw_rows"] = len(df)
        metadata["raw_columns"] = list(df.columns)

        # Step 4: Align to hourly grid
        aligned = align_to_hourly_grid(df, self._config.alignment)
        align_stats = compute_alignment_stats(df, aligned)
        self._alignment_stats = align_stats
        metadata["aligned_rows"] = len(aligned)

        # Step 5: Build features
        featured = build_features(aligned, self._config.features)

        # Step 6: Build targets
        with_targets = build_targets(featured, self._config.target)

        # Step 7: Split chronologically
        try:
            splits = chronological_split(with_targets, self._config.splits)
            split_desc = describe_splits(splits)
        except ValueError as e:
            logger.error("Splitting failed", error=str(e))
            split_desc = {"error": str(e)}  # type: ignore[dict-item]
            splits = DatasetSplits(train=with_targets)

        # Step 8: Leakage checks
        leakage = run_all_leakage_checks(
            with_targets,
            train_df=splits.train,
            val_df=splits.validation,
            test_df=splits.test,
            config=self._config,
        )

        # Step 9: Quality report
        quality = generate_quality_report(with_targets, self._config.target)

        # Step 10: Package
        bundle = DatasetBundle(
            config=self._config,
            full_dataset=with_targets,
            train=splits.train,
            validation=splits.validation,
            test=splits.test,
            leakage_report=leakage,
            quality_report=quality,
            split_description=split_desc,
            alignment_stats=align_stats,
            metadata=metadata,
        )

        logger.info(
            "Dataset build complete",
            rows=len(with_targets),
            columns=len(with_targets.columns),
            leakage_passed=leakage["passed"],
            quality_score=quality.quality_score,
        )

        return bundle

    def build_from_dataframe(
        self,
        raw_df: pd.DataFrame,
    ) -> DatasetBundle:
        """Build dataset from a pre-existing DataFrame (for testing).

        Skips data collection; starts from the alignment step.

        Args:
            raw_df: DataFrame with DatetimeIndex and observation columns.

        Returns:
            DatasetBundle with all artifacts.
        """
        metadata: dict[str, Any] = {
            "schema_version": self._config.schema_version,
            "source": "pre-existing_dataframe",
            "built_at": pd.Timestamp.now(tz="UTC").isoformat(),
        }

        # Handle empty DataFrame early
        if raw_df.empty:
            return DatasetBundle(
                config=self._config,
                full_dataset=raw_df,
                train=None,
                validation=None,
                test=None,
                leakage_report={"passed": True, "checks": {}, "total_errors": 0},
                quality_report=generate_quality_report(raw_df),
                split_description={"error": "Empty DataFrame"},
                alignment_stats={},
                metadata=metadata,
            )

        # Align
        aligned = align_to_hourly_grid(raw_df, self._config.alignment)
        metadata["aligned_rows"] = len(aligned)

        # Features
        featured = build_features(aligned, self._config.features)

        # Targets
        with_targets = build_targets(featured, self._config.target)

        # Split
        try:
            splits = chronological_split(with_targets, self._config.splits)
            split_desc = describe_splits(splits)
        except ValueError as e:
            split_desc = {"error": str(e)}  # type: ignore[dict-item]
            splits = DatasetSplits(train=with_targets)

        # Leakage
        leakage = run_all_leakage_checks(
            with_targets,
            train_df=splits.train,
            val_df=splits.validation,
            test_df=splits.test,
            config=self._config,
        )

        # Quality
        quality = generate_quality_report(with_targets, self._config.target)

        return DatasetBundle(
            config=self._config,
            full_dataset=with_targets,
            train=splits.train,
            validation=splits.validation,
            test=splits.test,
            leakage_report=leakage,
            quality_report=quality,
            split_description=split_desc,
            metadata=metadata,
        )
