"""Prediction service — domain logic for generating predictions.

This is the core orchestration layer that ties together:
    - ModelStore (model loading and caching)
    - FeatureAssembly (data retrieval and feature construction)
    - Audit trail (prediction logging)

Design principles:
    - Pure domain logic — no HTTP, no FastAPI dependencies
    - Every prediction is traced with full provenance
    - Fails honestly: returns structured errors, never fabricates values
    - Reuses the exact same feature pipeline as training
    - Reports actual data state (freshness, coverage, gaps)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from .audit import record_prediction
from .feature_assembly import (
    FeatureAssemblyResult,
    assemble_prediction_features,
    assemble_shared_features,
)
from .model_store import (
    HorizonNotAvailableError,
    ModelLoadError,
    ModelStore,
)


# ── Prediction Result ─────────────────────────────────────────────


@dataclass
class PredictionResult:
    """Structured result from a prediction request.

    Contains the prediction value, provenance, diagnostics,
    and any warnings. This is the domain-level response —
    the API layer formats it into HTTP.
    """

    # Core prediction
    prediction_id: str = ""
    predicted_pm25: float | None = None
    unit: str = "ug/m3"

    # Provenance
    model_version: str = ""
    algorithm: str = ""
    forecast_horizon: int = 0

    # Timing
    prediction_time: str = ""
    target_time: str = ""

    # Data quality
    data_timestamp: str | None = None
    freshness_hours: float | None = None
    feature_count: int = 0
    missing_features: list[str] = field(default_factory=list)

    # Performance
    inference_time_ms: float = 0.0

    # Diagnostics
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_successful(self) -> bool:
        """True if a prediction value was produced."""
        return self.predicted_pm25 is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "prediction_id": self.prediction_id,
            "predicted_pm25": round(self.predicted_pm25, 2) if self.predicted_pm25 is not None else None,
            "unit": self.unit,
            "model": {
                "version": self.model_version,
                "algorithm": self.algorithm,
            },
            "horizon_hours": self.forecast_horizon,
            "timing": {
                "prediction_time": self.prediction_time,
                "target_time": self.target_time,
                "inference_ms": round(self.inference_time_ms, 2),
            },
            "data_quality": {
                "data_timestamp": self.data_timestamp,
                "freshness_hours": round(self.freshness_hours, 2) if self.freshness_hours is not None else None,
                "feature_count": self.feature_count,
                "missing_features": self.missing_features,
            },
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ── Supported Horizons ────────────────────────────────────────────

SUPPORTED_HORIZONS = [1, 3, 6, 12, 24]


# ── Prediction Service ────────────────────────────────────────────


class PredictionService:
    """Domain-level prediction orchestrator.

    Usage:
        service = PredictionService(
            model_store=ModelStore("data/models"),
            db_path="data/lahore_pulse.db",
        )
        result = service.predict(horizon=6, as_of=datetime.now(UTC))
    """

    def __init__(
        self,
        model_store: ModelStore,
        db_path: str | Path,
        auto_load: bool = True,
    ) -> None:
        """Initialise the prediction service.

        Args:
            model_store: Pre-configured ModelStore instance.
            db_path: Path to the SQLite database.
            auto_load: If True, load all models on construction.
        """
        self.model_store = model_store
        self.db_path = Path(db_path)
        self._ready = False

        if auto_load:
            self._ready = self._try_load_models()

    def _try_load_models(self) -> bool:
        """Attempt to load all models. Returns True if at least one loaded."""
        try:
            loaded = self.model_store.load_all()
            if loaded:
                logger.info(
                    "Prediction service initialised",
                    loaded_horizons=sorted(loaded.keys()),
                )
                return True
            logger.warning("No models loaded during initialisation")
            return False
        except Exception as exc:
            logger.error("Failed to load models", error=str(exc))
            return False

    # ── Core Prediction ───────────────────────────────────────────

    def predict(
        self,
        horizon: int,
        as_of: datetime | None = None,
        record_to_db: bool = True,
    ) -> PredictionResult:
        """Generate a PM2.5 prediction for a given horizon.

        This is the main entry point. It:
        1. Validates the request
        2. Loads the model for the horizon
        3. Assembles features from the database
        4. Runs inference
        5. Records the prediction in the audit trail
        6. Returns the structured result

        Args:
            horizon: Forecast horizon in hours (1, 3, 6, 12, 24).
            as_of: Prediction reference time (default: now UTC).
            record_to_db: Whether to write to the audit trail.

        Returns:
            PredictionResult with value and full provenance.
        """
        t0 = time.perf_counter()
        now = datetime.now(UTC)
        target_time = as_of or now

        # Initialise result
        result = PredictionResult(
            prediction_time=now.isoformat(),
            target_time=target_time.isoformat(),
            forecast_horizon=horizon,
        )

        # 1. Validate horizon
        if horizon not in SUPPORTED_HORIZONS:
            result.errors.append(
                f"Unsupported horizon: {horizon}h. "
                f"Supported: {SUPPORTED_HORIZONS}"
            )
            return result

        # 2. Load model
        try:
            cached_model = self.model_store.get(horizon)
        except HorizonNotAvailableError as exc:
            result.errors.append(f"Model not available for horizon {horizon}h: {exc}")
            return result
        except ModelLoadError as exc:
            result.errors.append(f"Model load failed for horizon {horizon}h: {exc}")
            return result

        result.model_version = cached_model.metadata.model_version
        result.algorithm = cached_model.metadata.algorithm

        # 3. Assemble features
        assembly = assemble_prediction_features(
            db_path=self.db_path,
            as_of=target_time,
            target_horizon=horizon,
            model_feature_names=cached_model.metadata.feature_names,
        )

        result.data_timestamp = (
            assembly.data_timestamp.isoformat() if assembly.data_timestamp else None
        )
        result.freshness_hours = assembly.freshness_hours
        result.feature_count = len(assembly.feature_row.columns) if not assembly.feature_row.empty else 0
        result.missing_features = assembly.missing_features
        result.warnings = assembly.warnings

        # 4. Check if features are usable
        if not assembly.is_usable:
            if assembly.feature_row.empty:
                result.errors.append("Feature assembly produced an empty feature row")
            else:
                result.errors.append(
                    f"Feature coverage insufficient: {len(assembly.missing_features)} "
                    f"features missing/NaN"
                )
            return result

        # 5. Run inference
        try:
            t_pred = time.perf_counter()
            predictions = cached_model.predict(assembly.feature_row)
            self.model_store._cache[horizon].pipeline  # keep reference
            result.inference_time_ms = (time.perf_counter() - t_pred) * 1000
        except Exception as exc:
            result.errors.append(f"Prediction failed: {exc}")
            return result

        predicted_value = float(predictions.iloc[0])
        result.predicted_pm25 = predicted_value

        # 6. Record to audit trail
        if record_to_db:
            try:
                prediction_id = record_prediction(
                    db_path=self.db_path,
                    model_version=result.model_version,
                    algorithm=result.algorithm,
                    forecast_horizon=horizon,
                    prediction_time=now,
                    target_time=target_time,
                    predicted_value=predicted_value,
                    data_timestamp=(
                        assembly.data_timestamp
                        if assembly.data_timestamp
                        else now
                    ),
                    freshness_hours=assembly.freshness_hours,
                    feature_count=result.feature_count,
                    missing_features=assembly.missing_features or None,
                    warnings=assembly.warnings or None,
                )
                result.prediction_id = prediction_id
            except Exception as exc:
                # Audit trail failure is non-fatal but logged
                result.warnings.append(f"Audit trail write failed: {exc}")
                logger.error("Audit trail write failed", error=str(exc))

        total_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "Prediction completed",
            horizon=horizon,
            model_version=result.model_version,
            predicted_pm25=round(predicted_value, 2),
            total_ms=round(total_ms, 2),
            inference_ms=round(result.inference_time_ms, 2),
            freshness_hours=round(assembly.freshness_hours, 1) if assembly.freshness_hours else None,
        )

        return result

    # ── Batch Prediction ──────────────────────────────────────────

    def predict_all_horizons(
        self,
        as_of: datetime | None = None,
        record_to_db: bool = True,
    ) -> dict[int, PredictionResult]:
        """Generate predictions for all supported horizons.

        Phase 5.5 optimization: queries the database ONCE and builds
        features for all horizons from the same data. This reduces
        latency from ~5 × DB_query_time to ~1 × DB_query_time + 
        5 × model_inference_time.

        Args:
            as_of: Prediction reference time (default: now UTC).
            record_to_db: Whether to write to the audit trail.

        Returns:
            Dict mapping horizon → PredictionResult.
        """
        t0 = time.perf_counter()
        now = datetime.now(UTC)
        target_time = as_of or now

        # 1. Determine available horizons
        available_horizons = [
            h for h in SUPPORTED_HORIZONS
            if self.model_store.is_available(h)
        ]

        if not available_horizons:
            # Fallback to individual predictions (degraded mode)
            results = {}
            for horizon in SUPPORTED_HORIZONS:
                results[horizon] = self.predict(
                    horizon=horizon,
                    as_of=as_of,
                    record_to_db=record_to_db,
                )
            return results

        # 2. Build feature names map
        model_feature_names_map = {}
        for horizon in available_horizons:
            try:
                cached = self.model_store.get(horizon)
                model_feature_names_map[horizon] = cached.metadata.feature_names
            except Exception:
                model_feature_names_map[horizon] = []

        # 3. Single database query + shared feature assembly
        t_features = time.perf_counter()
        assembly_results = assemble_shared_features(
            db_path=self.db_path,
            as_of=target_time,
            horizons=available_horizons,
            model_feature_names_map=model_feature_names_map,
        )
        feature_time_ms = (time.perf_counter() - t_features) * 1000

        # 4. Run inference for each horizon
        results = {}
        for horizon in SUPPORTED_HORIZONS:
            if horizon not in assembly_results:
                # Horizon not available — create error result
                results[horizon] = PredictionResult(
                    prediction_time=now.isoformat(),
                    target_time=target_time.isoformat(),
                    forecast_horizon=horizon,
                    errors=[f"Model not available for horizon {horizon}h"],
                )
                continue

            assembly = assembly_results[horizon]
            result = PredictionResult(
                prediction_time=now.isoformat(),
                target_time=target_time.isoformat(),
                forecast_horizon=horizon,
            )

            # Load model for this horizon
            try:
                cached_model = self.model_store.get(horizon)
            except HorizonNotAvailableError as exc:
                result.errors.append(f"Model not available for horizon {horizon}h: {exc}")
                results[horizon] = result
                continue
            except ModelLoadError as exc:
                result.errors.append(f"Model load failed for horizon {horizon}h: {exc}")
                results[horizon] = result
                continue

            result.model_version = cached_model.metadata.model_version
            result.algorithm = cached_model.metadata.algorithm
            result.data_timestamp = (
                assembly.data_timestamp.isoformat() if assembly.data_timestamp else None
            )
            result.freshness_hours = assembly.freshness_hours
            result.feature_count = len(assembly.feature_row.columns) if not assembly.feature_row.empty else 0
            result.missing_features = assembly.missing_features
            result.warnings = assembly.warnings

            # Check if features are usable
            if not assembly.is_usable:
                if assembly.feature_row.empty:
                    result.errors.append("Feature assembly produced an empty feature row")
                else:
                    result.errors.append(
                        f"Feature coverage insufficient: {len(assembly.missing_features)} "
                        f"features missing/NaN"
                    )
                results[horizon] = result
                continue

            # Run inference
            try:
                t_pred = time.perf_counter()
                predictions = cached_model.predict(assembly.feature_row)
                result.inference_time_ms = (time.perf_counter() - t_pred) * 1000
            except Exception as exc:
                result.errors.append(f"Prediction failed: {exc}")
                results[horizon] = result
                continue

            predicted_value = float(predictions.iloc[0])
            result.predicted_pm25 = predicted_value

            # Record to audit trail
            if record_to_db:
                try:
                    prediction_id = record_prediction(
                        db_path=self.db_path,
                        model_version=result.model_version,
                        algorithm=result.algorithm,
                        forecast_horizon=horizon,
                        prediction_time=now,
                        target_time=target_time,
                        predicted_value=predicted_value,
                        data_timestamp=(
                            assembly.data_timestamp
                            if assembly.data_timestamp
                            else now
                        ),
                        freshness_hours=assembly.freshness_hours,
                        feature_count=result.feature_count,
                        missing_features=assembly.missing_features or None,
                        warnings=assembly.warnings or None,
                    )
                    result.prediction_id = prediction_id
                except Exception as exc:
                    result.warnings.append(f"Audit trail write failed: {exc}")
                    logger.error("Audit trail write failed", horizon=horizon, error=str(exc))

            results[horizon] = result

        total_ms = (time.perf_counter() - t0) * 1000
        successful = sum(1 for r in results.values() if r.is_successful)
        logger.info(
            "All-horizon prediction completed",
            horizons=len(results),
            successful=successful,
            total_ms=round(total_ms, 2),
            feature_ms=round(feature_time_ms, 2),
        )

        return results

    # ── Readiness / Status ────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """True if at least one model is loaded and ready."""
        return self.model_store.is_ready

    def status(self) -> dict[str, Any]:
        """Detailed service status."""
        return {
            "ready": self.is_ready,
            "model_store": self.model_store.status(),
            "db_path": str(self.db_path),
            "db_exists": self.db_path.exists(),
            "supported_horizons": SUPPORTED_HORIZONS,
        }
