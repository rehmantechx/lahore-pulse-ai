"""Tests for Phase 4 model definitions, baselines, artifacts, and registry.

Covers:
    - Model pipeline construction (Ridge, HGB)
    - Baseline predictions (persistence, seasonal-lag)
    - Feature matrix preparation
    - Feature importance extraction
    - Model artifact serialization
    - Model registry CRUD
    - Metric computation
    - No data leakage in features
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from app.modeling.models import (
    ModelArtifact,
    ModelRegistry,
    ModelRegistryEntry,
    build_derived_features,
    build_hgb_pipeline,
    build_ridge_pipeline,
    build_target_lags,
    build_target_rolling,
    build_temporal_features,
    build_weather_rolling,
    compute_metrics,
    extract_feature_importance,
    get_feature_columns,
    load_model_artifact,
    persistence_baseline,
    prepare_feature_matrix,
    save_feature_importance,
    save_model_artifact,
    seasonal_lag_baseline,
)


# ── Fixtures ─────────────────────────────────────────────────────────


def _make_pm25_df(hours: int = 500) -> pd.DataFrame:
    """Create a deterministic hourly PM2.5 + weather DataFrame."""
    idx = pd.date_range("2024-01-01", periods=hours, freq="1h", tz="UTC")
    t = np.arange(hours, dtype=float)
    # Realistic PM2.5 with diurnal cycle + noise
    pm25 = (
        70.0
        + 30.0 * np.sin(2 * np.pi * t / 24)
        + 15.0 * np.sin(2 * np.pi * t / 168)
        + np.random.default_rng(42).normal(0, 10, hours)
    )
    pm25 = np.clip(pm25, 0.5, 400.0)
    df = pd.DataFrame(
        {
            "temperature_2m": 20 + 10 * np.sin(2 * np.pi * t / 24),
            "relative_humidity_2m": 60 + 20 * np.sin(2 * np.pi * t / 24 + np.pi),
            "dew_point_2m": 10 + 5 * np.sin(2 * np.pi * t / 24),
            "apparent_temperature": 20 + 10 * np.sin(2 * np.pi * t / 24),
            "precipitation": np.maximum(0, np.sin(2 * np.pi * t / 72) * 2),
            "rain": np.maximum(0, np.sin(2 * np.pi * t / 72) * 1.5),
            "cloud_cover": 50 + 30 * np.sin(2 * np.pi * t / 48),
            "pressure_msl": 1013 + 5 * np.sin(2 * np.pi * t / 48),
            "surface_pressure": 1010 + 5 * np.sin(2 * np.pi * t / 48),
            "wind_speed_10m": 5 + 3 * np.sin(2 * np.pi * t / 12),
            "wind_gusts_10m": 8 + 5 * np.sin(2 * np.pi * t / 12),
            "shortwave_radiation": np.maximum(0, 300 * np.sin(2 * np.pi * (t - 6) / 24)),
            "soil_temperature_0_to_7cm": 15 + 8 * np.sin(2 * np.pi * t / 24),
            "pm2_5": pm25,
            "pm10": pm25 * 1.5,
            "carbon_monoxide": 0.5 + 0.2 * np.sin(2 * np.pi * t / 24),
            "nitrogen_dioxide": 30 + 15 * np.sin(2 * np.pi * t / 24),
            "ozone": 40 + 20 * np.sin(2 * np.pi * t / 24),
            "sulphur_dioxide": 5 + 3 * np.sin(2 * np.pi * t / 24),
        },
        index=idx,
    )
    df.index.name = "time"
    return df


# ── Model Pipeline Tests ─────────────────────────────────────────────


class TestRidgePipeline:
    """Tests for Ridge regression pipeline."""

    def test_builds_pipeline(self) -> None:
        pipe = build_ridge_pipeline()
        assert pipe is not None
        assert "imputer" in pipe.named_steps
        assert "scaler" in pipe.named_steps
        assert "model" in pipe.named_steps

    def test_fits_and_predicts(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(rng.standard_normal(200))
        pipe = build_ridge_pipeline()
        pipe.fit(X, y)
        preds = pipe.predict(X[:10])
        assert preds.shape == (10,)
        assert np.all(np.isfinite(preds))

    def test_pipeline_handles_nan(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        X.iloc[0, 0] = np.nan
        X.iloc[5, 2] = np.nan
        y = pd.Series(rng.standard_normal(200))
        pipe = build_ridge_pipeline()
        pipe.fit(X, y)
        preds = pipe.predict(X[:10])
        assert np.all(np.isfinite(preds))


class TestHGBPipeline:
    """Tests for HistGradientBoosting pipeline."""

    def test_builds_pipeline(self) -> None:
        pipe = build_hgb_pipeline()
        assert pipe is not None
        assert "model" in pipe.named_steps

    def test_fits_and_predicts(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(rng.standard_normal(200))
        pipe = build_hgb_pipeline()
        pipe.fit(X, y)
        preds = pipe.predict(X[:10])
        assert preds.shape == (10,)
        assert np.all(np.isfinite(preds))

    def test_handles_nan_natively(self) -> None:
        """HGB should handle NaN without imputer."""
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        X.iloc[0, 0] = np.nan
        X.iloc[5, 2] = np.nan
        y = pd.Series(rng.standard_normal(200))
        pipe = build_hgb_pipeline()
        pipe.fit(X, y)
        preds = pipe.predict(X[:10])
        assert np.all(np.isfinite(preds))


# ── Baseline Tests ───────────────────────────────────────────────────


class TestPersistenceBaseline:
    """Tests for persistence baseline."""

    def test_returns_predictions_and_actuals(self) -> None:
        df = _make_pm25_df(200)
        preds, actuals = persistence_baseline(df, horizon=1)
        assert len(preds) > 0
        assert len(actuals) > 0
        assert len(preds) == len(actuals)

    def test_prediction_equals_current_value(self) -> None:
        """Persistence: prediction at t is PM2.5(t)."""
        df = _make_pm25_df(200)
        preds, actuals = persistence_baseline(df, horizon=1)
        # preds should match pm2_5 at corresponding indices
        assert np.allclose(preds.values, df.loc[preds.index, "pm2_5"].values)

    def test_different_horizons(self) -> None:
        df = _make_pm25_df(500)
        for h in [1, 3, 6, 12, 24]:
            preds, actuals = persistence_baseline(df, horizon=h)
            assert len(preds) > 0


class TestSeasonalLagBaseline:
    """Tests for seasonal-lag baseline."""

    def test_returns_predictions_and_actuals(self) -> None:
        df = _make_pm25_df(500)
        preds, actuals = seasonal_lag_baseline(df, horizon=1)
        assert len(preds) > 0
        assert len(actuals) > 0

    def test_prediction_equals_week_ago(self) -> None:
        """Seasonal lag: prediction is PM2.5 from 168h ago."""
        df = _make_pm25_df(500)
        preds, actuals = seasonal_lag_baseline(df, horizon=1)
        for idx in preds.index:
            week_ago = idx - pd.Timedelta(hours=168)
            if week_ago in df.index:
                assert preds[idx] == df.loc[week_ago, "pm2_5"]


# ── Feature Engineering Tests ────────────────────────────────────────


class TestBuildTargetLags:
    def test_creates_lag_columns(self) -> None:
        df = _make_pm25_df(200)
        result = build_target_lags(df, target_col="pm2_5", lags=[1, 6, 24])
        assert "pm2_5_lag_1h" in result.columns
        assert "pm2_5_lag_6h" in result.columns
        assert "pm2_5_lag_24h" in result.columns

    def test_lag_values_are_shifted(self) -> None:
        df = _make_pm25_df(200)
        result = build_target_lags(df, target_col="pm2_5", lags=[1])
        # Lag 1 at time t should equal pm2_5 at time t-1
        assert result["pm2_5_lag_1h"].iloc[1] == df["pm2_5"].iloc[0]

    def test_does_not_modify_original(self) -> None:
        df = _make_pm25_df(200)
        original_cols = list(df.columns)
        _ = build_target_lags(df, target_col="pm2_5", lags=[1, 6])
        assert list(df.columns) == original_cols


class TestBuildTargetRolling:
    def test_creates_rolling_columns(self) -> None:
        df = _make_pm25_df(200)
        result = build_target_rolling(df, target_col="pm2_5", windows=[6, 24], operations=["mean", "std"])
        assert "pm2_5_roll_6h_mean" in result.columns
        assert "pm2_5_roll_6h_std" in result.columns
        assert "pm2_5_roll_24h_mean" in result.columns
        assert "pm2_5_roll_24h_std" in result.columns

    def test_rolling_mean_is_correct(self) -> None:
        df = _make_pm25_df(200)
        result = build_target_rolling(df, target_col="pm2_5", windows=[3], operations=["mean"])
        # At index 2, mean of pm2_5[0:3]
        expected = df["pm2_5"].iloc[:3].mean()
        assert abs(result["pm2_5_roll_3h_mean"].iloc[2] - expected) < 1e-10


class TestBuildWeatherRolling:
    def test_creates_weather_rolling_columns(self) -> None:
        df = _make_pm25_df(200)
        result = build_weather_rolling(df, columns=["temperature_2m"], windows=[6], operations=["mean"])
        assert "temperature_2m_roll_6h_mean" in result.columns


class TestBuildTemporalFeatures:
    def test_creates_temporal_encodings(self) -> None:
        df = _make_pm25_df(200)
        result = build_temporal_features(df)
        assert "hour_sin" in result.columns
        assert "hour_cos" in result.columns
        assert "dow_sin" in result.columns
        assert "dow_cos" in result.columns
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns

    def test_cyclical_range(self) -> None:
        df = _make_pm25_df(200)
        result = build_temporal_features(df)
        assert result["hour_sin"].between(-1, 1).all()
        assert result["hour_cos"].between(-1, 1).all()


class TestBuildDerivedFeatures:
    def test_creates_pressure_change(self) -> None:
        df = _make_pm25_df(200)
        result = build_derived_features(df)
        assert "pressure_change" in result.columns

    def test_creates_precipitation_accumulated(self) -> None:
        df = _make_pm25_df(200)
        result = build_derived_features(df)
        assert "precipitation_accumulated_3h" in result.columns


class TestGetFeatureColumns:
    def test_returns_available_columns(self) -> None:
        df = _make_pm25_df(200)
        cols = get_feature_columns(df)
        assert len(cols) > 0
        # All returned columns should exist in df
        for c in cols:
            assert c in df.columns


# ── Feature Matrix Preparation Tests ─────────────────────────────────


class TestPrepareFeatureMatrix:
    def test_returns_x_y_featurenames(self) -> None:
        df = _make_pm25_df(500)
        X, y, feature_names = prepare_feature_matrix(df, target_horizon=1, target_col="pm2_5")
        assert len(X) > 0
        assert len(y) > 0
        assert len(feature_names) > 0
        assert len(X) == len(y)

    def test_no_nan_in_target(self) -> None:
        df = _make_pm25_df(500)
        X, y, _ = prepare_feature_matrix(df, target_horizon=6, target_col="pm2_5")
        assert y.notna().all()

    def test_no_leakage_future_data(self) -> None:
        """Features should not contain future values of pm2_5 beyond the horizon."""
        df = _make_pm25_df(500)
        X, y, feature_names = prepare_feature_matrix(df, target_horizon=6, target_col="pm2_5")
        # Target lags should be ≤ 72h (max lag)
        lag_cols = [c for c in feature_names if "pm2_5_lag_" in c]
        for c in lag_cols:
            lag_hours = int(c.split("_lag_")[1].replace("h", ""))
            assert lag_hours <= 72

    def test_different_horizons_different_targets(self) -> None:
        df = _make_pm25_df(500)
        _, y1, _ = prepare_feature_matrix(df, target_horizon=1, target_col="pm2_5")
        _, y6, _ = prepare_feature_matrix(df, target_horizon=6, target_col="pm2_5")
        # Targets must be different at the SAME index (shifted by 5 hours)
        common_idx = y1.index.intersection(y6.index)
        assert len(common_idx) > 0
        # At the same time t, y1=t+1 and y6=t+6 — they should NOT be equal in general
        # Pick indices where they clearly differ (avoid exact crossings of sinusoidal data)
        diff_count = sum(abs(y1.loc[i] - y6.loc[i]) > 0.1 for i in common_idx[:100])
        assert diff_count > 50, f"Expected many different targets, got only {diff_count} differences"

    def test_multiple_horizons(self) -> None:
        df = _make_pm25_df(500)
        for h in [1, 3, 6, 12, 24]:
            X, y, fnames = prepare_feature_matrix(df, target_horizon=h, target_col="pm2_5")
            assert len(X) > 0
            assert len(fnames) > 0


# ── Metric Computation Tests ─────────────────────────────────────────


class TestComputeMetrics:
    def test_perfect_predictions(self) -> None:
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        m = compute_metrics(y, y)
        assert m["mae"] == 0.0
        assert m["rmse"] == 0.0
        assert m["r2"] == 1.0
        assert m["medae"] == 0.0
        assert m["max_error"] == 0.0

    def test_known_error(self) -> None:
        y_true = np.array([1.0, 2.0, 3.0])
        y_pred = np.array([2.0, 3.0, 4.0])
        m = compute_metrics(y_true, y_pred)
        assert m["mae"] == 1.0
        assert m["rmse"] == 1.0
        assert m["n_samples"] == 3

    def test_returns_all_metrics(self) -> None:
        m = compute_metrics(np.array([1, 2, 3]), np.array([1, 2, 3]))
        assert "mae" in m
        assert "rmse" in m
        assert "r2" in m
        assert "medae" in m
        assert "max_error" in m
        assert "n_samples" in m


# ── Feature Importance Tests ─────────────────────────────────────────


class TestFeatureImportance:
    def test_ridge_importance(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(rng.standard_normal(200))
        pipe = build_ridge_pipeline()
        pipe.fit(X, y)
        result = extract_feature_importance(pipe, list(X.columns), "ridge")
        assert result["method"] == "absolute_ridge_coefficients"
        assert len(result["top_features"]) == 5
        assert result["n_features"] == 5

    def test_hgb_importance(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(rng.standard_normal(200))
        pipe = build_hgb_pipeline()
        pipe.fit(X, y)
        result = extract_feature_importance(
            pipe, list(X.columns), "hgb", X_train=X, y_train=y,
        )
        assert result["method"] == "permutation_importance_mae"
        assert len(result["top_features"]) > 0
        assert result["n_features"] == 5

    def test_importance_sorted_descending(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(rng.standard_normal(200))
        pipe = build_ridge_pipeline()
        pipe.fit(X, y)
        result = extract_feature_importance(pipe, list(X.columns), "ridge")
        importances = [f["importance"] for f in result["all_features"]]
        assert importances == sorted(importances, reverse=True)

    def test_save_importance(self) -> None:
        importance = {
            "method": "test",
            "n_features": 3,
            "top_features": [{"feature": "f0", "importance": 1.0}],
            "all_features": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_feature_importance(importance, tmpdir, "test_model")
            assert Path(path).exists()
            loaded = json.loads(Path(path).read_text())
            assert loaded["method"] == "test"


# ── Model Artifact Tests ─────────────────────────────────────────────


class TestModelArtifact:
    def test_creates_with_defaults(self) -> None:
        art = ModelArtifact()
        assert art.model_version == ""
        assert art.algorithm == ""
        assert art.forecast_horizon == 0

    def test_to_dict(self) -> None:
        art = ModelArtifact(model_version="v1.0.0_h1_ridge", algorithm="ridge")
        d = art.to_dict()
        assert d["model_version"] == "v1.0.0_h1_ridge"
        assert d["algorithm"] == "ridge"

    def test_to_json_and_back(self) -> None:
        art = ModelArtifact(
            model_version="v1.0.0_h6_hgb",
            algorithm="hgb",
            forecast_horizon=6,
            val_metrics={"mae": 14.5, "rmse": 19.7, "r2": 0.82},
        )
        js = art.to_json()
        assert "v1.0.0_h6_hgb" in js
        # Round-trip through dict
        loaded = ModelArtifact(**{k: v for k, v in json.loads(js).items() if k in ModelArtifact.__dataclass_fields__})
        assert loaded.model_version == "v1.0.0_h6_hgb"
        assert loaded.val_metrics["mae"] == 14.5

    def test_save_and_load_metadata(self) -> None:
        art = ModelArtifact(
            model_version="v1.0.0_h1_ridge",
            algorithm="ridge",
            forecast_horizon=1,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metadata.json"
            art.save_metadata(path)
            assert path.exists()
            loaded = ModelArtifact.load_metadata(path)
            assert loaded.model_version == "v1.0.0_h1_ridge"

    def test_save_and_load_full_artifact(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame(rng.standard_normal((200, 5)), columns=[f"f{i}" for i in range(5)])
        y = pd.Series(rng.standard_normal(200))
        pipe = build_ridge_pipeline()
        pipe.fit(X, y)

        art = ModelArtifact(
            model_version="v1.0.0_h1_ridge",
            algorithm="ridge",
            forecast_horizon=1,
            feature_names=list(X.columns),
            feature_count=5,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            save_model_artifact(pipe, art, tmpdir)
            # Check files exist
            model_path = Path(tmpdir) / "v1.0.0_h1_ridge.joblib"
            meta_path = Path(tmpdir) / "v1.0.0_h1_ridge_metadata.json"
            assert model_path.exists()
            assert meta_path.exists()
            # Load and verify
            loaded_pipe = load_model_artifact(model_path)
            preds = loaded_pipe.predict(X[:5])
            assert preds.shape == (5,)


# ── Model Registry Tests ─────────────────────────────────────────────


class TestModelRegistry:
    def test_register_and_retrieve(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = ModelRegistry(Path(tmpdir) / "registry.json")
            entry = ModelRegistryEntry(
                model_version="v1.0.0_h1_ridge",
                model_name="ridge_h1",
                algorithm="ridge",
                status="candidate",
                created_at="2024-01-01T00:00:00",
                dataset_version="1.0.0",
                forecast_horizon=1,
                val_mae=4.5,
            )
            reg.register(entry)
            all_entries = reg.get_all()
            assert len(all_entries) == 1
            assert all_entries[0].model_version == "v1.0.0_h1_ridge"

    def test_update_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = ModelRegistry(Path(tmpdir) / "registry.json")
            entry = ModelRegistryEntry(
                model_version="v1.0.0_h1_ridge",
                model_name="ridge_h1",
                algorithm="ridge",
                status="candidate",
                created_at="2024-01-01T00:00:00",
                dataset_version="1.0.0",
                forecast_horizon=1,
            )
            reg.register(entry)
            reg.update_status("v1.0.0_h1_ridge", "selected")
            updated = reg.get_all()[0]
            assert updated.status == "selected"

    def test_persistence_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reg_path = Path(tmpdir) / "registry.json"
            reg = ModelRegistry(reg_path)
            entry = ModelRegistryEntry(
                model_version="v1.0.0_h6_hgb",
                model_name="hgb_h6",
                algorithm="hgb",
                status="validated",
                created_at="2024-01-01T00:00:00",
                dataset_version="1.0.0",
                forecast_horizon=6,
            )
            reg.register(entry)
            # New instance should load from disk
            reg2 = ModelRegistry(reg_path)
            assert len(reg2.get_all()) == 1
            assert reg2.get_all()[0].model_version == "v1.0.0_h6_hgb"

    def test_get_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = ModelRegistry(Path(tmpdir) / "registry.json")
            for i, status in enumerate(["candidate", "selected", "candidate"]):
                reg.register(ModelRegistryEntry(
                    model_version=f"v{i}",
                    model_name=f"m{i}",
                    algorithm="ridge",
                    status=status,
                    created_at="2024-01-01T00:00:00",
                    dataset_version="1.0.0",
                    forecast_horizon=1,
                ))
            selected = reg.get_by_status("selected")
            assert len(selected) == 1
            candidates = reg.get_by_status("candidate")
            assert len(candidates) == 2

    def test_get_best(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = ModelRegistry(Path(tmpdir) / "registry.json")
            for i, mae in enumerate([5.0, 3.0, 4.0]):
                reg.register(ModelRegistryEntry(
                    model_version=f"v{i}",
                    model_name=f"m{i}",
                    algorithm="ridge",
                    status="validated",
                    created_at="2024-01-01T00:00:00",
                    dataset_version="1.0.0",
                    forecast_horizon=1,
                    val_mae=mae,
                ))
            best = reg.get_best(metric="val_mae")
            assert best is not None
            assert best.val_mae == 3.0


# ── No Leakage Tests ─────────────────────────────────────────────────


class TestNoLeakage:
    """Verify that feature engineering does not introduce data leakage."""

    def test_lags_are_strictly_backwards(self) -> None:
        df = _make_pm25_df(200)
        result = build_target_lags(df, target_col="pm2_5", lags=[1, 6, 24])
        # Lag at time t should come from t-lag, not t+lag
        for lag in [1, 6, 24]:
            col = f"pm2_5_lag_{lag}h"
            # At index 24+lag, lag column should equal original at 24
            t = 30
            assert result[col].iloc[t] == df["pm2_5"].iloc[t - lag]

    def test_rolling_uses_only_past(self) -> None:
        df = _make_pm25_df(200)
        result = build_target_rolling(df, target_col="pm2_5", windows=[6], operations=["mean"])
        # Rolling mean at time t uses pm2_5[t-5:t+1] (inclusive window)
        # This is standard causal rolling, no future leak
        for t in range(6, 20):
            expected = df["pm2_5"].iloc[t - 5: t + 1].mean()
            assert abs(result["pm2_5_roll_6h_mean"].iloc[t] - expected) < 1e-10

    def test_target_shift_is_negative(self) -> None:
        """Target column must be shifted backwards (future), not forwards."""
        df = _make_pm25_df(500)
        X, y, fnames = prepare_feature_matrix(df, target_horizon=6, target_col="pm2_5")
        # y should be the pm2_5 value 6 hours ahead
        # Check that y aligns with the correct future values
        for idx in y.index[:10]:
            future_idx = idx + pd.Timedelta(hours=6)
            if future_idx in df.index:
                assert abs(y[idx] - df.loc[future_idx, "pm2_5"]) < 1e-10
