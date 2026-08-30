"""Phase 4 Orchestrator — end-to-end model training and evaluation.

This is the main entry point for Phase 4. It:

1. Loads data from the database
2. Prepares feature matrices for each forecast horizon
3. Trains and evaluates baselines
4. Trains and evaluates candidate models
5. Performs walk-forward backtesting
6. Runs error analysis
7. Selects the best model
8. Saves model artifacts with full provenance
9. Generates the final report

Usage:
    python run_phase4.py
    python run_phase4.py --horizons 1 6 24
    python run_phase4.py --db-path data/lahore_pulse.db
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from .config import DatasetConfig, SplitConfig, TargetConfig
from .dataset_loader import prepare_modeling_dataset
from .evaluation import (
    ChronologicalSplit,
    EvaluationResult,
    WalkForwardResult,
    analyze_errors,
    chronological_train_val_test_split,
    evaluate_model_full,
)
from .models import (
    ModelArtifact,
    ModelRegistry,
    ModelRegistryEntry,
    build_hgb_pipeline,
    build_ridge_pipeline,
    compute_metrics,
    extract_feature_importance,
    load_model_artifact,
    persistence_baseline,
    prepare_feature_matrix,
    save_feature_importance,
    save_model_artifact,
    seasonal_lag_baseline,
)

# ── Constants ────────────────────────────────────────────────────────

DEFAULT_HORIZONS = [1, 3, 6, 12, 24]
DEFAULT_DB_PATH = "data/lahore_pulse.db"
OUTPUT_DIR = "data/models"
REPORT_DIR = "data/reports"
REGISTRY_PATH = "data/models/model_registry.json"


# ── Phase 4 Orchestrator ────────────────────────────────────────────


class Phase4Orchestrator:
    """Orchestrates the complete Phase 4 model training and evaluation.

    Coordinates all components:
        - Dataset loading from SQLite
        - Feature engineering per horizon
        - Baseline evaluation
        - Candidate model training
        - Walk-forward backtesting
        - Error analysis
        - Model selection and artifact saving
        - Report generation
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        output_dir: str = OUTPUT_DIR,
        report_dir: str = REPORT_DIR,
        horizons: list[int] | None = None,
        config: DatasetConfig | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)
        self.horizons = horizons or DEFAULT_HORIZONS
        self.config = config or DatasetConfig()

        # Results storage
        self.dataset_description: dict[str, Any] = {}
        self.aligned_df: pd.DataFrame | None = None
        self.evaluations: dict[int, dict[str, EvaluationResult]] = {}
        self.baselines: dict[int, dict[str, dict[str, float]]] = {}
        self.selected_models: dict[int, ModelArtifact] = {}
        self.registry: ModelRegistry | None = None
        self.total_duration: float = 0.0

    def run(self) -> dict[str, Any]:
        """Execute the complete Phase 4 pipeline.

        Returns:
            Dictionary with summary of all results.
        """
        t0 = time.perf_counter()
        logger.info("=" * 70)
        logger.info("PHASE 4: Model Training & Evaluation")
        logger.info("=" * 70)

        # Step 1: Load dataset
        self._load_dataset()

        # Step 2: Initialize registry
        self.registry = ModelRegistry(self.output_dir / "model_registry.json")

        # Step 3: For each horizon, train and evaluate
        for horizon in self.horizons:
            logger.info(f"\n{'='*50}")
            logger.info(f"Forecast Horizon: {horizon}h")
            logger.info(f"{'='*50}")

            self._evaluate_horizon(horizon)

        # Step 4: Select best models
        self._select_best_models()

        # Step 5: Save artifacts
        self._save_artifacts()

        # Step 6: Generate report
        self.total_duration = time.perf_counter() - t0
        report = self._generate_report()

        logger.info("=" * 70)
        logger.info(f"PHASE 4 COMPLETE in {self.total_duration:.1f}s")
        logger.info("=" * 70)

        return report

    def _load_dataset(self) -> None:
        """Step 1: Load and prepare the dataset."""
        logger.info("Step 1: Loading dataset from database")

        result = prepare_modeling_dataset(
            db_path=str(self.db_path),
            config=self.config,
        )

        self.aligned_df = result["df"]
        self.dataset_description = result["description"]

        if self.aligned_df.empty:
            raise ValueError("No data loaded from database")

        logger.info(
            "Dataset loaded",
            rows=self.dataset_description["rows"],
            parameters=self.dataset_description["parameter_count"],
            duration_hours=self.dataset_description["duration_hours"],
        )

    def _evaluate_horizon(self, horizon: int) -> None:
        """Step 2-3: Prepare features and evaluate all models for one horizon."""
        logger.info(f"Preparing features for horizon={horizon}h")

        # Build feature matrix
        X, y, feature_names = prepare_feature_matrix(
            self.aligned_df,
            target_horizon=horizon,
            target_col="pm2_5",
        )

        logger.info(
            f"Feature matrix for {horizon}h",
            rows=len(X),
            features=len(feature_names),
        )

        # Chronological split
        split = chronological_train_val_test_split(
            X, y,
            train_ratio=self.config.splits.train_ratio,
            val_ratio=self.config.splits.val_ratio,
            gap_hours=self.config.splits.gap_hours,
        )

        split_desc = split.describe()
        logger.info(
            f"Split for {horizon}h",
            train=split_desc["train_rows"],
            val=split_desc["val_rows"],
            test=split_desc["test_rows"],
            train_period=split_desc["train_period"],
            val_period=split_desc["val_period"],
            test_period=split_desc["test_period"],
        )

        self.evaluations[horizon] = {}
        self.baselines[horizon] = {}

        # ── Evaluate baselines ────────────────────────────────────────
        logger.info(f"\n--- Baselines ({horizon}h) ---")

        # Persistence baseline
        persist_y_pred, persist_y_true = persistence_baseline(
            self.aligned_df, horizon=horizon
        )
        # Align to test set
        test_idx = split.X_test.index
        persist_test_mask = persist_y_pred.index.isin(test_idx)
        if persist_test_mask.sum() > 0:
            persist_metrics = compute_metrics(
                persist_y_true[persist_test_mask].values,
                persist_y_pred[persist_test_mask].values,
            )
        else:
            # Fallback: use all available
            persist_metrics = compute_metrics(persist_y_true.values, persist_y_pred.values)

        self.baselines[horizon]["persistence"] = persist_metrics
        logger.info(f"Persistence MAE: {persist_metrics['mae']:.2f}, RMSE: {persist_metrics['rmse']:.2f}")

        # Seasonal-lag baseline
        seasonal_y_pred, seasonal_y_true = seasonal_lag_baseline(
            self.aligned_df, horizon=horizon
        )
        seasonal_test_mask = seasonal_y_pred.index.isin(test_idx)
        if seasonal_test_mask.sum() > 0:
            seasonal_metrics = compute_metrics(
                seasonal_y_true[seasonal_test_mask].values,
                seasonal_y_pred[seasonal_test_mask].values,
            )
        else:
            seasonal_metrics = compute_metrics(seasonal_y_true.values, seasonal_y_pred.values)

        self.baselines[horizon]["seasonal_lag"] = seasonal_metrics
        logger.info(f"Seasonal-lag MAE: {seasonal_metrics['mae']:.2f}, RMSE: {seasonal_metrics['rmse']:.2f}")

        # Combined baseline comparison on validation set
        val_idx = split.X_val.index
        persist_val_mask = persist_y_pred.index.isin(val_idx)
        if persist_val_mask.sum() > 0:
            persist_val_metrics = compute_metrics(
                persist_y_true[persist_val_mask].values,
                persist_y_pred[persist_val_mask].values,
            )
        else:
            persist_val_metrics = persist_metrics

        seasonal_val_mask = seasonal_y_pred.index.isin(val_idx)
        if seasonal_val_mask.sum() > 0:
            seasonal_val_metrics = compute_metrics(
                seasonal_y_true[seasonal_val_mask].values,
                seasonal_y_pred[seasonal_val_mask].values,
            )
        else:
            seasonal_val_metrics = seasonal_metrics

        baseline_comparison = {
            "persistence": persist_val_metrics,
            "seasonal_lag": seasonal_val_metrics,
        }

        # ── Evaluate candidate models ─────────────────────────────────
        logger.info(f"\n--- Candidate Models ({horizon}h) ---")

        # Candidate A: Ridge Regression
        ridge_eval = evaluate_model_full(
            pipeline=build_ridge_pipeline(),
            X_train=split.X_train,
            y_train=split.y_train,
            X_val=split.X_val,
            y_val=split.y_val,
            X_test=split.X_test,
            y_test=split.y_test,
            model_name=f"ridge_h{horizon}",
            horizon=horizon,
            baseline_metrics=baseline_comparison,
            run_walk_forward=True,
            walk_forward_factory=build_ridge_pipeline,
            n_wf_folds=6,
        )
        self.evaluations[horizon]["ridge"] = ridge_eval

        # Candidate B: HistGradientBoosting
        hgb_eval = evaluate_model_full(
            pipeline=build_hgb_pipeline(),
            X_train=split.X_train,
            y_train=split.y_train,
            X_val=split.X_val,
            y_val=split.y_val,
            X_test=split.X_test,
            y_test=split.y_test,
            model_name=f"hgb_h{horizon}",
            horizon=horizon,
            baseline_metrics=baseline_comparison,
            run_walk_forward=True,
            walk_forward_factory=build_hgb_pipeline,
            n_wf_folds=6,
        )
        self.evaluations[horizon]["hgb"] = hgb_eval

        # Log comparison
        logger.info(f"\n--- Model Comparison ({horizon}h) ---")
        logger.info(f"{'Model':<20} {'Val MAE':>10} {'Val RMSE':>10} {'Test MAE':>10} {'Test R2':>10}")
        logger.info("-" * 60)
        logger.info(
            f"{'Persistence':<20} "
            f"{persist_val_metrics['mae']:>10.2f} "
            f"{'—':>10} "
            f"{persist_metrics['mae']:>10.2f} "
            f"{'—':>10}"
        )
        logger.info(
            f"{'Seasonal-Lag':<20} "
            f"{seasonal_val_metrics['mae']:>10.2f} "
            f"{'—':>10} "
            f"{seasonal_metrics['mae']:>10.2f} "
            f"{'—':>10}"
        )
        logger.info(
            f"{'Ridge':<20} "
            f"{ridge_eval.val_metrics['mae']:>10.2f} "
            f"{ridge_eval.val_metrics['rmse']:>10.2f} "
            f"{ridge_eval.test_metrics['mae']:>10.2f} "
            f"{ridge_eval.test_metrics['r2']:>10.4f}"
        )
        logger.info(
            f"{'HistGradientBoost':<20} "
            f"{hgb_eval.val_metrics['mae']:>10.2f} "
            f"{hgb_eval.val_metrics['rmse']:>10.2f} "
            f"{hgb_eval.test_metrics['mae']:>10.2f} "
            f"{hgb_eval.test_metrics['r2']:>10.4f}"
        )

    def _select_best_models(self) -> None:
        """Step 4: Select best model for each horizon based on validation MAE."""
        logger.info("\nStep 4: Selecting best models")

        for horizon in self.horizons:
            evaluations = self.evaluations.get(horizon, {})
            if not evaluations:
                continue

            # Find best model by validation MAE
            best_name = None
            best_mae = float("inf")
            best_eval = None

            for name, eval_result in evaluations.items():
                val_mae = eval_result.val_metrics.get("mae", float("inf"))
                if val_mae < best_mae:
                    best_mae = val_mae
                    best_name = name
                    best_eval = eval_result

            if best_name and best_eval:
                # Create model artifact
                artifact = ModelArtifact(
                    model_version=f"v1.0.0_h{horizon}_{best_name}",
                    model_name=f"{best_name}_h{horizon}",
                    algorithm=best_name,
                    created_at=pd.Timestamp.now(tz="UTC").isoformat(),
                    dataset_version="1.0.0",
                    target_definition=f"PM2.5(t+{horizon}h)",
                    forecast_horizon=horizon,
                    train_rows=len(best_eval.train_metrics) if best_eval.train_metrics else 0,
                    train_metrics=best_eval.train_metrics,
                    val_metrics=best_eval.val_metrics,
                    test_metrics=best_eval.test_metrics,
                    train_time_seconds=best_eval.train_time_seconds,
                )

                if best_eval.walk_forward:
                    artifact.walk_forward_metrics = best_eval.walk_forward.aggregate_metrics

                self.selected_models[horizon] = artifact

                # Register
                self.registry.register(ModelRegistryEntry(
                    model_version=artifact.model_version,
                    model_name=artifact.model_name,
                    algorithm=artifact.algorithm,
                    status="validated",
                    created_at=artifact.created_at,
                    dataset_version="1.0.0",
                    forecast_horizon=horizon,
                    val_mae=best_eval.val_metrics.get("mae", 0),
                    val_rmse=best_eval.val_metrics.get("rmse", 0),
                    val_r2=best_eval.val_metrics.get("r2", 0),
                ))

                logger.info(
                    f"Best model for {horizon}h: {best_name}",
                    val_mae=best_eval.val_metrics["mae"],
                    test_mae=best_eval.test_metrics["mae"],
                    test_r2=best_eval.test_metrics["r2"],
                )

    def _save_artifacts(self) -> None:
        """Step 5: Save model artifacts."""
        logger.info("\nStep 5: Saving model artifacts")

        for horizon, artifact in self.selected_models.items():
            evaluations = self.evaluations.get(horizon, {})
            best_eval = evaluations.get(artifact.algorithm)
            if best_eval is None:
                continue

            # Re-train the final model on train+val for production
            # (but we need to re-prepare features first)
            X, y, feature_names = prepare_feature_matrix(
                self.aligned_df,
                target_horizon=horizon,
                target_col="pm2_5",
            )

            split = chronological_train_val_test_split(
                X, y,
                train_ratio=self.config.splits.train_ratio,
                val_ratio=self.config.splits.val_ratio,
                gap_hours=self.config.splits.gap_hours,
            )

            # Combine train+val for final model training
            X_final_train = pd.concat([split.X_train, split.X_val])
            y_final_train = pd.concat([split.y_train, split.y_val])

            # Build and train final model
            if artifact.algorithm == "ridge":
                final_pipeline = build_ridge_pipeline()
            else:
                final_pipeline = build_hgb_pipeline()

            final_pipeline.fit(X_final_train, y_final_train)

            # Update artifact with feature info
            artifact.feature_names = feature_names
            artifact.feature_count = len(feature_names)
            artifact.train_rows = len(X_final_train)
            artifact.test_rows = len(split.X_test)

            # Save
            model_dir = self.output_dir / f"horizon_{horizon}h"
            save_model_artifact(final_pipeline, artifact, model_dir)

            # Extract and save feature importance
            importance = extract_feature_importance(
                final_pipeline, feature_names, artifact.algorithm,
                X_train=X_final_train, y_train=y_final_train,
            )
            save_feature_importance(importance, model_dir, artifact.model_version)

            # Store importance in artifact for report
            artifact.feature_importance = importance

            # Mark as selected in registry
            self.registry.update_status(artifact.model_version, "selected")

    def _generate_report(self) -> dict[str, Any]:
        """Step 6: Generate the final Phase 4 report."""
        logger.info("\nStep 6: Generating report")

        report: dict[str, Any] = {
            "phase": 4,
            "title": "Phase 4 — Predictive Forecasting Engine",
            "status": "COMPLETE",
            "duration_seconds": round(self.total_duration, 2),
            "dataset": self.dataset_description,
            "horizons_evaluated": self.horizons,
            "results": {},
            "selected_models": {},
        }

        for horizon in self.horizons:
            horizon_result: dict[str, Any] = {
                "baselines": self.baselines.get(horizon, {}),
                "models": {},
            }

            evaluations = self.evaluations.get(horizon, {})
            for name, eval_result in evaluations.items():
                horizon_result["models"][name] = eval_result.describe()

            if horizon in self.selected_models:
                sel = self.selected_models[horizon]
                sel_info: dict[str, Any] = {
                    "model_version": sel.model_version,
                    "algorithm": sel.algorithm,
                    "val_mae": sel.val_metrics.get("mae", 0),
                    "test_mae": sel.test_metrics.get("mae", 0),
                    "test_r2": sel.test_metrics.get("r2", 0),
                }
                # Include top feature importance if available
                if sel.feature_importance and sel.feature_importance.get("top_features"):
                    sel_info["feature_importance"] = {
                        "method": sel.feature_importance.get("method", ""),
                        "top_features": sel.feature_importance.get("top_features", []),
                    }
                report["selected_models"][str(horizon)] = sel_info

            report["results"][str(horizon)] = horizon_result

        # Save report
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / "phase4_results.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report saved to {report_path}")

        return report
