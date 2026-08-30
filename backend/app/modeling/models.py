"""Model definitions — baselines, candidate models, and preprocessing.

Implements a deliberately small set of models for PM2.5 forecasting:

Baselines:
    1. Persistence: predict last known PM2.5 value
    2. Seasonal-lag: PM2.5 from same hour, same day last week

Candidates:
    A. Ridge regression (regularized linear model)
    B. HistGradientBoosting (fast, handles NaN natively)

All models are wrapped in sklearn-compatible pipelines that handle
preprocessing (scaling, NaN handling) and are serializable via joblib.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    median_absolute_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ── Feature/Target Column Selection ──────────────────────────────────

# Features used by the model (curated to avoid excessive dimensionality
# relative to the ~35K-row dataset)
WEATHER_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "soil_temperature_0_to_7cm",
]

# Target lags (hours): recent PM2.5 values
TARGET_LAGS = [1, 2, 3, 6, 12, 24, 48, 72]

# Rolling statistics on target
TARGET_ROLLING_WINDOWS = [3, 6, 12, 24]
TARGET_ROLLING_OPS = ["mean", "std"]

# Weather rolling (reduced from full set to avoid overfitting)
WEATHER_ROLLING_WINDOWS = [6, 12, 24]
WEATHER_ROLLING_OPS = ["mean"]

# Temporal features
TEMPORAL_FEATURES = [
    "hour_sin", "hour_cos",
    "dow_sin", "dow_cos",
    "month_sin", "month_cos",
]


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Determine which feature columns exist in the DataFrame.

    Returns the intersection of planned features with available columns.
    """
    planned = (
        WEATHER_FEATURES
        + [f"pm2_5_lag_{h}h" for h in TARGET_LAGS]
        + [f"pm2_5_roll_{w}h_{op}" for w in TARGET_ROLLING_WINDOWS for op in TARGET_ROLLING_OPS]
        + [f"{v}_roll_{w}h_{op}" for v in ["temperature_2m", "humidity", "pressure_msl"]
           for w in WEATHER_ROLLING_WINDOWS for op in WEATHER_ROLLING_OPS]
        + TEMPORAL_FEATURES
    )
    available = [c for c in planned if c in df.columns]
    return available


def build_target_lags(
    df: pd.DataFrame,
    target_col: str = "pm2_5",
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Add lag features for the target variable.

    Args:
        df: DataFrame with DatetimeIndex.
        target_col: Name of the target column.
        lags: Lag offsets in hours.

    Returns:
        DataFrame with added lag columns.
    """
    lags = lags or TARGET_LAGS
    out = df.copy()
    for lag in lags:
        out[f"{target_col}_lag_{lag}h"] = out[target_col].shift(lag)
    return out


def build_target_rolling(
    df: pd.DataFrame,
    target_col: str = "pm2_5",
    windows: list[int] | None = None,
    operations: list[str] | None = None,
) -> pd.DataFrame:
    """Add rolling statistics for the target variable.

    Args:
        df: DataFrame with DatetimeIndex.
        target_col: Name of the target column.
        windows: Window sizes in hours.
        operations: Aggregation operations.

    Returns:
        DataFrame with added rolling columns.
    """
    windows = windows or TARGET_ROLLING_WINDOWS
    operations = operations or TARGET_ROLLING_OPS
    out = df.copy()
    for w in windows:
        rolling = out[target_col].rolling(window=w, min_periods=1)
        for op in operations:
            col_name = f"{target_col}_roll_{w}h_{op}"
            if op == "mean":
                out[col_name] = rolling.mean()
            elif op == "std":
                out[col_name] = rolling.std()
            elif op == "min":
                out[col_name] = rolling.min()
            elif op == "max":
                out[col_name] = rolling.max()
    return out


def build_weather_rolling(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    windows: list[int] | None = None,
    operations: list[str] | None = None,
) -> pd.DataFrame:
    """Add rolling statistics for selected weather variables.

    Only applies to temperature_2m, relative_humidity_2m, pressure_msl
    to keep feature count manageable.
    """
    columns = columns or ["temperature_2m", "relative_humidity_2m", "pressure_msl"]
    windows = windows or WEATHER_ROLLING_WINDOWS
    operations = operations or WEATHER_ROLLING_OPS
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            continue
        for w in windows:
            rolling = out[col].rolling(window=w, min_periods=1)
            for op in operations:
                roll_col = f"{col}_roll_{w}h_{op}"
                if op == "mean":
                    out[roll_col] = rolling.mean()
                elif op == "std":
                    out[roll_col] = rolling.std()
    return out


def build_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical temporal encodings (hour, day-of-week, month)."""
    out = df.copy()
    idx = out.index

    # Hour of day
    hours = idx.hour + idx.minute / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * hours / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hours / 24)

    # Day of week
    dow = idx.dayofweek
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    # Month of year
    month = idx.month - 1
    out["month_sin"] = np.sin(2 * np.pi * month / 12)
    out["month_cos"] = np.cos(2 * np.pi * month / 12)

    return out


def build_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add physically-motivated derived features."""
    out = df.copy()

    # Pressure change (hour-over-hour)
    if "pressure_msl" in out.columns:
        out["pressure_change"] = out["pressure_msl"].diff(1)

    # Precipitation accumulated 3h
    if "precipitation" in out.columns:
        out["precipitation_accumulated_3h"] = (
            out["precipitation"].rolling(window=3, min_periods=1).sum()
        )

    return out


def prepare_feature_matrix(
    df: pd.DataFrame,
    target_horizon: int = 1,
    target_col: str = "pm2_5",
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Prepare X, y, and feature names for a given forecast horizon.

    Steps:
        1. Add target lags and rolling stats (PM2.5 history features)
        2. Add weather rolling stats
        3. Add temporal features
        4. Add derived features
        5. Build target y(t+h) = PM2.5 at t+h
        6. Drop rows where y or critical features are NaN
        7. Return X, y, feature_names

    Args:
        df: Aligned hourly DataFrame with raw parameters.
        target_horizon: Forecast horizon in hours.
        target_col: Target parameter name.

    Returns:
        Tuple of (X DataFrame, y Series, feature_names list).
    """
    out = df.copy()

    # Step 1: Target lags (PM2.5 history)
    out = build_target_lags(out, target_col, TARGET_LAGS)

    # Step 2: Target rolling stats
    out = build_target_rolling(out, target_col, TARGET_ROLLING_WINDOWS, TARGET_ROLLING_OPS)

    # Step 3: Weather rolling stats (reduced set)
    out = build_weather_rolling(out)

    # Step 4: Temporal features
    out = build_temporal_features(out)

    # Step 5: Derived features
    out = build_derived_features(out)

    # Step 6: Build target (shift by horizon)
    target_name = f"target_{target_col}_t+{target_horizon}"
    out[target_name] = out[target_col].shift(-target_horizon)

    # Step 7: Select feature columns (only those that exist)
    feature_cols = get_feature_columns(out)

    # Step 8: Drop rows where target or features are NaN
    # For features: only drop if the raw weather features or critical lags are NaN
    critical_cols = [target_col] + [f"{target_col}_lag_1h", f"{target_col}_lag_3h"]
    critical_cols = [c for c in critical_cols if c in out.columns]
    valid_mask = out[target_name].notna() & out[critical_cols].notna().all(axis=1)

    out = out[valid_mask].copy()

    X = out[feature_cols].copy()
    y = out[target_name].copy()

    logger.info(
        "Feature matrix prepared",
        horizon=target_horizon,
        rows=len(X),
        features=len(feature_cols),
        target_mean=round(float(y.mean()), 2),
        target_std=round(float(y.std()), 2),
    )

    return X, y, feature_cols


# ── Model Definitions ────────────────────────────────────────────────


def build_ridge_pipeline() -> Pipeline:
    """Build a Ridge regression pipeline with preprocessing.

    Pipeline: Impute NaN → Scale → Ridge(alpha=1.0)

    Returns:
        sklearn Pipeline.
    """
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=1.0, random_state=42)),
    ])


def build_hgb_pipeline(
    learning_rate: float = 0.05,
    max_depth: int = 6,
    max_iter: int = 300,
    min_samples_leaf: int = 20,
    l2_regularization: float = 1.0,
    random_state: int = 42,
) -> Pipeline:
    """Build a HistGradientBoosting pipeline.

    HGBR handles NaN natively, so we skip imputation.
    No scaling needed for tree-based models.

    Args:
        learning_rate: Boosting learning rate.
        max_depth: Maximum tree depth.
        max_iter: Maximum boosting iterations.
        min_samples_leaf: Minimum samples per leaf.
        l2_regularization: L2 regularization (lambda).
        random_state: Random seed.

    Returns:
        sklearn Pipeline.
    """
    return Pipeline([
        ("model", HistGradientBoostingRegressor(
            learning_rate=learning_rate,
            max_depth=max_depth,
            max_iter=max_iter,
            min_samples_leaf=min_samples_leaf,
            l2_regularization=l2_regularization,
            random_state=random_state,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20,
        )),
    ])


# ── Baselines ────────────────────────────────────────────────────────


def persistence_baseline(
    df: pd.DataFrame,
    horizon: int = 1,
    target_col: str = "pm2_5",
) -> tuple[pd.Series, pd.Series]:
    """Persistence baseline: prediction = last known PM2.5 value.

    For horizon h, prediction at time t is PM2.5(t) — the current value,
    not shifted by h. This is the most naive forecast.

    Args:
        df: DataFrame with target_col and DatetimeIndex.
        horizon: Forecast horizon (used for target alignment only).
        target_col: Target column name.

    Returns:
        Tuple of (predictions, actuals).
    """
    out = df.copy()
    target_name = f"target_{target_col}_t+{horizon}"
    out[target_name] = out[target_col].shift(-horizon)

    valid = out.dropna(subset=[target_col, target_name])
    y_pred = valid[target_col].values
    y_true = valid[target_name].values

    return pd.Series(y_pred, index=valid.index), pd.Series(y_true, index=valid.index)


def seasonal_lag_baseline(
    df: pd.DataFrame,
    horizon: int = 1,
    target_col: str = "pm2_5",
    lag_hours: int = 168,
) -> tuple[pd.Series, pd.Series]:
    """Seasonal-lag baseline: prediction = PM2.5 from 1 week ago.

    Uses the value at t - 168h (same hour, same day last week)
    shifted by the forecast horizon.

    Args:
        df: DataFrame with target_col and DatetimeIndex.
        horizon: Forecast horizon in hours.
        target_col: Target column name.
        lag_hours: Seasonal lag (default 168 = 1 week).

    Returns:
        Tuple of (predictions, actuals).
    """
    out = df.copy()
    target_name = f"target_{target_col}_t+{horizon}"
    out[target_name] = out[target_col].shift(-horizon)
    out["seasonal_pred"] = out[target_col].shift(lag_hours)

    valid = out.dropna(subset=["seasonal_pred", target_name])
    y_pred = valid["seasonal_pred"].values
    y_true = valid[target_name].values

    return pd.Series(y_pred, index=valid.index), pd.Series(y_true, index=valid.index)


# ── Training & Evaluation ────────────────────────────────────────────


def train_model(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_name: str = "model",
) -> dict[str, Any]:
    """Train a model and return timing/provenance information.

    Args:
        pipeline: sklearn Pipeline to train.
        X_train: Training features.
        y_train: Training target.
        model_name: Name for logging.

    Returns:
        Dictionary with training metadata.
    """
    t0 = time.perf_counter()
    pipeline.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    logger.info(
        f"Model trained: {model_name}",
        train_time=f"{train_time:.2f}s",
        rows=len(X_train),
        features=X_train.shape[1],
    )

    return {
        "model_name": model_name,
        "train_rows": len(X_train),
        "train_features": X_train.shape[1],
        "train_time_seconds": round(train_time, 3),
    }


def predict_model(
    pipeline: Pipeline,
    X: pd.DataFrame,
    model_name: str = "model",
) -> dict[str, Any]:
    """Generate predictions and measure inference time.

    Args:
        pipeline: Trained sklearn Pipeline.
        X: Feature DataFrame.
        model_name: Name for logging.

    Returns:
        Dictionary with predictions and timing.
    """
    t0 = time.perf_counter()
    y_pred = pipeline.predict(X)
    predict_time = time.perf_counter() - t0

    return {
        "predictions": y_pred,
        "predict_time_seconds": round(predict_time, 3),
        "model_name": model_name,
    }


def compute_metrics(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
) -> dict[str, float]:
    """Compute regression metrics appropriate for continuous forecasting.

    Metrics:
        - MAE: Mean Absolute Error (interpretable in μg/m3)
        - RMSE: Root Mean Squared Error (penalizes large errors)
        - R2: Coefficient of determination (supporting metric)
        - MedAE: Median Absolute Error (robust to outliers)
        - MaxError: Maximum absolute error (worst case)

    Args:
        y_true: Ground truth values.
        y_pred: Predicted values.

    Returns:
        Dictionary of metric_name → value.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "medae": round(float(median_absolute_error(y_true, y_pred)), 4),
        "max_error": round(float(np.max(np.abs(y_true - y_pred))), 4),
        "n_samples": len(y_true),
    }


# ── Feature Importance / Explainability ──────────────────────────────


def extract_feature_importance(
    pipeline: Pipeline,
    feature_names: list[str],
    algorithm: str,
    X_train: pd.DataFrame | None = None,
    y_train: pd.Series | None = None,
) -> dict[str, Any]:
    """Extract feature importance from a trained pipeline.

    For Ridge: uses absolute coefficient values.
    For HGB: uses permutation importance (sklearn 1.9+ dropped feature_importances_).
    For other models: returns empty dict.

    Args:
        pipeline: Trained sklearn Pipeline.
        feature_names: List of feature column names.
        algorithm: Algorithm name ('ridge' or 'hgb').
        X_train: Training features (required for HGB permutation importance).
        y_train: Training target (required for HGB permutation importance).

    Returns:
        Dictionary with:
            - method: explanation of the importance method
            - top_features: list of (feature_name, importance) sorted descending
            - all_features: full sorted list
            - n_features: number of features
    """
    importance_values = None
    X_for_importance = X_train
    y_for_importance = y_train

    if algorithm == "ridge":
        # Ridge: extract coefficients from the final step
        model_step = pipeline.named_steps.get("model")
        if model_step is not None:
            try:
                importance_values = np.abs(model_step.coef_)
                method = "absolute_ridge_coefficients"
            except Exception:
                method = "unavailable"
        else:
            method = "unavailable"
    elif algorithm == "hgb":
        # HistGradientBoostingRegressor in sklearn 1.9+ no longer has
        # feature_importances_. Use permutation_importance instead.
        model_step = pipeline.named_steps.get("model")
        if model_step is not None:
            try:
                from sklearn.inspection import permutation_importance
                # Use a small subsample for speed (500 rows, no repeat)
                n_perm = min(500, len(X_for_importance) if X_for_importance is not None else 500)
                if X_for_importance is not None and y_for_importance is not None:
                    sample_idx = np.random.choice(len(X_for_importance), n_perm, replace=False)
                    X_perm = X_for_importance.iloc[sample_idx]
                    y_perm = y_for_importance.iloc[sample_idx]
                else:
                    X_perm = None
                    y_perm = None

                if X_perm is not None and y_perm is not None:
                    perm_result = permutation_importance(
                        pipeline, X_perm, y_perm,
                        n_repeats=3,
                        random_state=42,
                        scoring="neg_mean_absolute_error",
                    )
                    importance_values = perm_result.importances_mean
                    # Make non-negative (permutation importance can be negative)
                    importance_values = np.maximum(importance_values, 0.0)
                    method = "permutation_importance_mae"
                else:
                    method = "unavailable_no_data"
            except Exception as e:
                logger.warning(f"Permutation importance failed: {e}")
                method = "unavailable_error"
        else:
            method = "unavailable"
    else:
        method = "unsupported_algorithm"

    result: dict[str, Any] = {
        "method": method,
        "n_features": len(feature_names),
        "top_features": [],
        "all_features": [],
    }

    if importance_values is not None and len(importance_values) == len(feature_names):
        # Create (name, importance) pairs and sort descending
        pairs = list(zip(feature_names, importance_values.tolist()))
        pairs.sort(key=lambda x: x[1], reverse=True)

        result["all_features"] = [
            {"feature": name, "importance": round(float(imp), 6)}
            for name, imp in pairs
        ]
        result["top_features"] = result["all_features"][:15]
        result["importance_sum"] = round(float(np.sum(importance_values)), 6)

    return result


def save_feature_importance(
    importance: dict[str, Any],
    output_dir: str | Path,
    model_version: str,
) -> str:
    """Save feature importance to a JSON file.

    Args:
        importance: Result from extract_feature_importance.
        output_dir: Directory to save.
        model_version: Model version identifier.

    Returns:
        Path to saved file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = output_dir / f"{model_version}_feature_importance.json"
    with open(file_path, "w") as f:
        json.dump(importance, f, indent=2)

    logger.info(
        "Feature importance saved",
        path=str(file_path),
        top_feature=importance["top_features"][0]["feature"] if importance["top_features"] else "N/A",
        n_features=importance["n_features"],
    )

    return str(file_path)


# ── Model Artifact ───────────────────────────────────────────────────


@dataclass
class ModelArtifact:
    """Serializable model artifact with full provenance.

    Preserves everything needed to reproduce a prediction:
    model, preprocessing, feature definitions, training metadata,
    and evaluation results.
    """

    # Identity
    model_version: str = ""
    model_name: str = ""
    algorithm: str = ""
    created_at: str = ""

    # Dataset linkage
    dataset_version: str = "1.0.0"
    feature_version: str = "1.0.0"
    target_definition: str = ""  # e.g. "PM2.5(t+6h)"
    forecast_horizon: int = 0

    # Training provenance
    training_period: str = ""
    validation_period: str = ""
    test_period: str = ""
    train_rows: int = 0
    val_rows: int = 0
    test_rows: int = 0

    # Hyperparameters
    hyperparameters: dict[str, Any] = field(default_factory=dict)

    # Feature definitions
    feature_names: list[str] = field(default_factory=list)
    feature_count: int = 0

    # Evaluation results
    train_metrics: dict[str, float] = field(default_factory=dict)
    val_metrics: dict[str, float] = field(default_factory=dict)
    test_metrics: dict[str, float] = field(default_factory=dict)

    # Walk-forward results (if computed)
    walk_forward_metrics: dict[str, float] = field(default_factory=dict)

    # Feature importance / explainability
    feature_importance: dict[str, Any] = field(default_factory=dict)

    # Performance
    train_time_seconds: float = 0.0
    predict_time_ms: float = 0.0
    artifact_size_bytes: int = 0

    # File path
    model_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save_metadata(self, path: str | Path) -> None:
        """Save metadata to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())
        logger.info("Model artifact metadata saved", path=str(path))

    @classmethod
    def load_metadata(cls, path: str | Path) -> ModelArtifact:
        """Load metadata from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def save_model_artifact(
    pipeline: Pipeline,
    artifact: ModelArtifact,
    output_dir: str | Path,
) -> str:
    """Save a trained model pipeline and its metadata.

    Args:
        pipeline: Trained sklearn Pipeline.
        artifact: Model artifact metadata.
        output_dir: Directory to save the artifact.

    Returns:
        Path to the saved model file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_file = output_dir / f"{artifact.model_version}.joblib"
    joblib.dump(pipeline, model_file)

    # Update artifact with file info
    artifact.model_file = str(model_file)
    artifact.artifact_size_bytes = model_file.stat().st_size

    # Save metadata
    metadata_file = output_dir / f"{artifact.model_version}_metadata.json"
    artifact.save_metadata(metadata_file)

    logger.info(
        "Model artifact saved",
        model_version=artifact.model_version,
        model_file=str(model_file),
        artifact_size_kb=round(artifact.artifact_size_bytes / 1024, 1),
    )

    return str(model_file)


def load_model_artifact(
    model_path: str | Path,
) -> Pipeline:
    """Load a trained model pipeline from disk.

    Args:
        model_path: Path to the .joblib model file.

    Returns:
        Loaded sklearn Pipeline.
    """
    return joblib.load(model_path)


# ── Model Registry (Lightweight) ─────────────────────────────────────


@dataclass
class ModelRegistryEntry:
    """Lightweight model registry entry."""

    model_version: str
    model_name: str
    algorithm: str
    status: str  # candidate, validated, selected, production, retired
    created_at: str
    dataset_version: str
    forecast_horizon: int
    val_mae: float = 0.0
    val_rmse: float = 0.0
    val_r2: float = 0.0
    notes: str = ""


class ModelRegistry:
    """Lightweight model registry stored as JSON.

    Tracks model lifecycle from candidate → validated → selected → production.
    """

    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path)
        self._entries: list[ModelRegistryEntry] = []
        self._load()

    def _load(self) -> None:
        """Load registry from disk if it exists."""
        if self.registry_path.exists():
            with open(self.registry_path) as f:
                data = json.load(f)
            self._entries = [ModelRegistryEntry(**e) for e in data]
        else:
            self._entries = []

    def _save(self) -> None:
        """Save registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump([asdict(e) for e in self._entries], f, indent=2, default=str)

    def register(self, entry: ModelRegistryEntry) -> None:
        """Register a new model entry."""
        self._entries.append(entry)
        self._save()
        logger.info(
            "Model registered",
            model_version=entry.model_version,
            status=entry.status,
        )

    def update_status(
        self,
        model_version: str,
        status: str,
        notes: str = "",
    ) -> None:
        """Update the status of a model entry."""
        for entry in self._entries:
            if entry.model_version == model_version:
                entry.status = status
                if notes:
                    entry.notes = notes
                self._save()
                logger.info(
                    "Model status updated",
                    model_version=model_version,
                    new_status=status,
                )
                return
        logger.warning("Model version not found in registry", model_version=model_version)

    def get_by_status(self, status: str) -> list[ModelRegistryEntry]:
        """Get all models with a given status."""
        return [e for e in self._entries if e.status == status]

    def get_all(self) -> list[ModelRegistryEntry]:
        """Get all registry entries."""
        return list(self._entries)

    def get_best(
        self,
        metric: str = "val_mae",
        horizon: int | None = None,
    ) -> ModelRegistryEntry | None:
        """Get the best model by a given metric.

        Args:
            metric: Metric name to sort by (lower is better).
            horizon: Optional filter by forecast horizon.

        Returns:
            Best ModelRegistryEntry or None.
        """
        entries = self._entries
        if horizon is not None:
            entries = [e for e in entries if e.forecast_horizon == horizon]

        if not entries:
            return None

        return min(entries, key=lambda e: getattr(e, metric, float("inf")))
