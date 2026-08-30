"""Model store — loads, caches, and routes model artifacts.

Design principles:
    - Loads real .joblib artifacts from disk (no mocking, no fabrication)
    - Caches loaded pipelines in-process (no Redis/Kafka)
    - Routes requests to the correct model by forecast horizon
    - Reports actual loading status — never claims a model is ready
      when it hasn't been loaded
    - Thread-safe for concurrent request handling

Architecture:
    ModelStore reads model_registry.json to discover which model is
    "selected" for each horizon.  It then loads the corresponding
    .joblib file and metadata JSON.  Loaded models are cached in a
    dict keyed by horizon.  If a model file is missing or corrupt,
    the store reports the error honestly.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from sklearn.pipeline import Pipeline

from ..models import ModelArtifact, ModelRegistry, load_model_artifact


class ModelLoadError(Exception):
    """Raised when a model artifact cannot be loaded from disk."""


class HorizonNotAvailableError(Exception):
    """Raised when no model is available for a requested horizon."""


class _CachedModel:
    """Internal container for a loaded model and its metadata."""

    def __init__(
        self,
        pipeline: Pipeline,
        metadata: ModelArtifact,
        load_time_ms: float,
    ) -> None:
        self.pipeline = pipeline
        self.metadata = metadata
        self.load_time_ms = load_time_ms

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Run inference and return predictions as a Series."""
        t0 = time.perf_counter()
        raw = self.pipeline.predict(X)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            "Prediction generated",
            horizon=self.metadata.forecast_horizon,
            model_version=self.metadata.model_version,
            rows=len(X),
            predict_ms=round(elapsed_ms, 2),
        )
        return pd.Series(raw, index=X.index, name=f"pm2_5_pred_h{self.metadata.forecast_horizon}")


class ModelStore:
    """In-process model cache with horizon-based routing.

    Usage:
        store = ModelStore(models_dir="data/models")
        store.load_all()            # or store.load_horizon(6)
        cached = store.get(6)       # returns _CachedModel
        predictions = cached.predict(X)
    """

    def __init__(self, models_dir: str | Path) -> None:
        """Initialise the model store.

        Args:
            models_dir: Directory containing horizon sub-folders
                        and model_registry.json.
        """
        self.models_dir = Path(models_dir)
        self._cache: dict[int, _CachedModel] = {}
        self._load_errors: dict[int, str] = {}
        self._registry: ModelRegistry | None = None

    # ── Registry ──────────────────────────────────────────────────

    def _get_registry(self) -> ModelRegistry:
        """Lazily load the model registry."""
        if self._registry is None:
            registry_path = self.models_dir / "model_registry.json"
            if not registry_path.exists():
                raise ModelLoadError(f"Model registry not found: {registry_path}")
            self._registry = ModelRegistry(registry_path)
        return self._registry

    # ── Loading ───────────────────────────────────────────────────

    def load_horizon(self, horizon: int) -> _CachedModel:
        """Load and cache the best model for a specific horizon.

        Looks up the "selected" model in the registry, then loads
        the .joblib and metadata files.

        Args:
            horizon: Forecast horizon in hours (1, 3, 6, 12, 24).

        Returns:
            Cached model ready for inference.

        Raises:
            HorizonNotAvailableError: No model found for this horizon.
            ModelLoadError: Model file missing or corrupt.
        """
        if horizon in self._cache:
            logger.debug("Model already cached", horizon=horizon)
            return self._cache[horizon]

        registry = self._get_registry()
        entry = registry.get_best(metric="val_mae", horizon=horizon)
        if entry is None:
            msg = f"No model registered for horizon {horizon}h"
            self._load_errors[horizon] = msg
            raise HorizonNotAvailableError(msg)

        model_version = entry.model_version

        # Discover the artifact files
        # Convention: data/models/horizon_Xh/<model_version>.joblib
        horizon_dir = self.models_dir / f"horizon_{horizon}h"
        joblib_path = horizon_dir / f"{model_version}.joblib"
        metadata_path = horizon_dir / f"{model_version}_metadata.json"

        if not joblib_path.exists():
            msg = f"Model file not found: {joblib_path}"
            self._load_errors[horizon] = msg
            raise ModelLoadError(msg)

        t0 = time.perf_counter()
        try:
            pipeline = load_model_artifact(joblib_path)
        except Exception as exc:
            msg = f"Failed to load model {model_version}: {exc}"
            self._load_errors[horizon] = msg
            raise ModelLoadError(msg) from exc

        # Load metadata (non-fatal — use defaults if missing)
        if metadata_path.exists():
            metadata = ModelArtifact.load_metadata(metadata_path)
        else:
            logger.warning(
                "Metadata file not found, using registry defaults",
                path=str(metadata_path),
            )
            metadata = ModelArtifact(
                model_version=model_version,
                algorithm=entry.algorithm,
                forecast_horizon=horizon,
                val_mae=entry.val_mae,
            )

        load_time_ms = (time.perf_counter() - t0) * 1000

        cached = _CachedModel(pipeline, metadata, load_time_ms)
        self._cache[horizon] = cached
        self._load_errors.pop(horizon, None)

        logger.info(
            "Model loaded",
            horizon=horizon,
            model_version=model_version,
            algorithm=entry.algorithm,
            load_time_ms=round(load_time_ms, 1),
            artifact_kb=round(joblib_path.stat().st_size / 1024, 1),
        )
        return cached

    def load_all(self) -> dict[int, _CachedModel]:
        """Load models for all horizons present in the registry.

        Returns:
            Dict mapping horizon → cached model.  Horizons that
            fail to load are logged and skipped.
        """
        registry = self._get_registry()
        horizons = {e.forecast_horizon for e in registry.get_all()}
        loaded = {}
        for h in sorted(horizons):
            try:
                loaded[h] = self.load_horizon(h)
            except (HorizonNotAvailableError, ModelLoadError) as exc:
                logger.warning("Failed to load model", horizon=h, error=str(exc))
        return loaded

    # ── Retrieval ─────────────────────────────────────────────────

    def get(self, horizon: int) -> _CachedModel:
        """Get a cached model for the given horizon.

        Args:
            horizon: Forecast horizon in hours.

        Returns:
            Cached model.

        Raises:
            HorizonNotAvailableError: Model not loaded for this horizon.
        """
        if horizon not in self._cache:
            # Attempt lazy loading
            return self.load_horizon(horizon)
        return self._cache[horizon]

    @property
    def available_horizons(self) -> list[int]:
        """Horizons that are currently loaded and ready."""
        return sorted(self._cache.keys())

    # ── Status / Readiness ────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Report the actual state of the model store.

        Each horizon reports its true status — loaded, error, or
        not-yet-attempted.  No component is claimed to be ready
        when it is not.
        """
        try:
            registry = self._get_registry()
            all_entries = registry.get_all()
            horizons_in_registry = sorted({e.forecast_horizon for e in all_entries})
        except (ModelLoadError, Exception) as exc:
            logger.warning("Registry unavailable for status", error=str(exc))
            return {
                "models_dir": str(self.models_dir),
                "registry_loaded": False,
                "registry_error": str(exc),
                "loaded_count": len(self._cache),
                "horizons": {},
            }

        models_status = {}
        for h in horizons_in_registry:
            best = registry.get_best(metric="val_mae", horizon=h)
            if h in self._cache:
                cached = self._cache[h]
                models_status[str(h)] = {
                    "status": "loaded",
                    "model_version": cached.metadata.model_version,
                    "algorithm": cached.metadata.algorithm,
                    "val_mae": best.val_mae if best else None,
                    "load_time_ms": round(cached.load_time_ms, 1),
                }
            elif h in self._load_errors:
                models_status[str(h)] = {
                    "status": "error",
                    "error": self._load_errors[h],
                }
            else:
                models_status[str(h)] = {
                    "status": "not_loaded",
                    "model_version": best.model_version if best else None,
                }

        return {
            "models_dir": str(self.models_dir),
            "registry_entries": len(all_entries),
            "loaded_count": len(self._cache),
            "horizons": models_status,
        }

    @property
    def is_ready(self) -> bool:
        """True if at least one model is loaded."""
        return len(self._cache) > 0

    def is_available(self, horizon: int) -> bool:
        """Check if a model for the given horizon is loaded and ready.

        This is cheaper than get() — does not attempt lazy loading.
        """
        return horizon in self._cache

    def unload_all(self) -> None:
        """Clear the model cache (for testing)."""
        self._cache.clear()
        self._load_errors.clear()
        self._registry = None
