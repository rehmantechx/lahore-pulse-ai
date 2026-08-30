"""Phase 5 tests — Model serving, feature assembly, prediction service, audit trail.

Tests cover:
    1. Model store: loading, caching, horizon routing, error handling
    2. Feature assembly: data loading, freshness, feature construction
    3. Prediction service: end-to-end prediction flow
    4. Audit trail: prediction recording and retrieval
    5. API endpoints: forecast, history, status
    6. No fabrication: models load real artifacts, predictions use real data
    7. Edge cases: missing data, invalid horizons, empty database
    8. Performance: load times within bounds

All tests use REAL model artifacts and REAL database (no mocks for
core serving logic — we must verify the actual pipeline works).
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# ── Paths ──────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
MODELS_DIR = DATA_DIR / "models"
DB_PATH = DATA_DIR / "lahore_pulse.db"


# ═══════════════════════════════════════════════════════════════════
# 1. Model Store Tests
# ═══════════════════════════════════════════════════════════════════


class TestModelStore:
    """Tests for model loading, caching, and horizon routing."""

    def test_registry_exists(self):
        """model_registry.json must exist with entries."""
        registry_path = MODELS_DIR / "model_registry.json"
        assert registry_path.exists()
        with open(registry_path) as f:
            data = json.load(f)
        assert len(data) > 0

    def test_all_five_horizons_have_artifacts(self):
        """Each horizon directory must contain a .joblib file."""
        for h in [1, 3, 6, 12, 24]:
            h_dir = MODELS_DIR / f"horizon_{h}h"
            assert h_dir.exists(), f"Horizon directory missing: {h_dir}"
            joblib_files = list(h_dir.glob("*.joblib"))
            assert len(joblib_files) > 0, f"No .joblib files in {h_dir}"

    def test_load_all_models(self):
        """All 5 models must load without error."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        loaded = store.load_all()
        assert len(loaded) == 5
        assert sorted(loaded.keys()) == [1, 3, 6, 12, 24]

    def test_load_individual_horizons(self):
        """Each horizon can be loaded independently."""
        from app.modeling.serving.model_store import ModelStore
        for h in [1, 3, 6, 12, 24]:
            store = ModelStore(MODELS_DIR)
            cached = store.load_horizon(h)
            assert cached.metadata.forecast_horizon == h
            assert cached.pipeline is not None

    def test_model_cache_reuse(self):
        """Loading the same horizon twice returns the cached model."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        first = store.load_horizon(6)
        second = store.load_horizon(6)
        assert first is second  # Same object — cached

    def test_model_metadata_has_features(self):
        """Loaded model metadata must list feature names."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        cached = store.load_horizon(1)
        assert len(cached.metadata.feature_names) > 0
        assert "pm2_5_lag_1h" in cached.metadata.feature_names
        assert "temperature_2m" in cached.metadata.feature_names

    def test_model_metadata_has_val_mae(self):
        """Metadata must include validation MAE from training."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        cached = store.load_horizon(1)
        assert cached.metadata.val_metrics["mae"] > 0

    def test_model_store_status_reports_all_horizons(self):
        """Status must list all horizons and their load state."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        store.load_all()
        status = store.status()
        assert status["loaded_count"] == 5
        for h_str in ["1", "3", "6", "12", "24"]:
            assert h_str in status["horizons"]
            assert status["horizons"][h_str]["status"] == "loaded"

    def test_is_ready_after_loading(self):
        """is_ready must be True after loading at least one model."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        assert not store.is_ready
        store.load_horizon(1)
        assert store.is_ready

    def test_unload_clears_cache(self):
        """unload_all() must clear the cache."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        store.load_all()
        assert len(store.available_horizons) == 5
        store.unload_all()
        assert len(store.available_horizons) == 0

    def test_horizon_not_available_error(self):
        """Requesting a non-existent horizon raises HorizonNotAvailableError."""
        from app.modeling.serving.model_store import HorizonNotAvailableError, ModelStore
        store = ModelStore(MODELS_DIR)
        with pytest.raises(HorizonNotAvailableError):
            store.load_horizon(99)

    def test_predict_runs_on_loaded_model(self):
        """A loaded model must accept a feature DataFrame and return predictions."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        cached = store.load_horizon(1)
        # Create a dummy feature row matching the expected feature count
        n_features = len(cached.metadata.feature_names)
        X = pd.DataFrame(
            np.random.randn(1, n_features),
            columns=cached.metadata.feature_names,
        )
        preds = cached.predict(X)
        assert len(preds) == 1
        assert preds.iloc[0] >= 0  # PM2.5 cannot be negative

    def test_load_times_are_reasonable(self):
        """All models must load within 2 seconds each."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        loaded = store.load_all()
        for h, cached in loaded.items():
            assert cached.load_time_ms < 2000, (
                f"Model for horizon {h}h took {cached.load_time_ms:.0f}ms to load"
            )

    def test_model_versions_match_registry(self):
        """Loaded model versions must match registry best entries."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        store.load_all()
        for h in [1, 3, 6, 12, 24]:
            cached = store.get(h)
            registry = store._get_registry()
            best = registry.get_best(metric="val_mae", horizon=h)
            assert cached.metadata.model_version == best.model_version


# ═══════════════════════════════════════════════════════════════════
# 2. Feature Assembly Tests
# ═══════════════════════════════════════════════════════════════════


class TestFeatureAssembly:
    """Tests for real-time feature construction from the database."""

    def test_database_exists(self):
        """The production database must exist."""
        assert DB_PATH.exists(), f"Database not found: {DB_PATH}"

    def test_load_recent_observations(self):
        """Must load observations from the database for recent hours."""
        from app.modeling.serving.feature_assembly import _load_recent_observations
        now = datetime.now(UTC)
        df = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        assert not df.empty
        assert "pm2_5" in df.columns

    def test_load_observations_returns_wide_format(self):
        """Loaded data must be wide-format (one column per parameter)."""
        from app.modeling.serving.feature_assembly import _load_recent_observations
        now = datetime.now(UTC)
        df = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        assert isinstance(df.columns, pd.Index)
        assert len(df.columns) > 1

    def test_align_to_hourly_grid(self):
        """Data must align to a regular hourly UTC grid."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
        )
        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=48)
        aligned = _align_to_hourly(raw)
        if not aligned.empty:
            # Check that index is regular
            freq = pd.infer_freq(aligned.index[:5])
            assert freq is not None or len(aligned) <= 2

    def test_feature_construction_succeeds(self):
        """Feature assembly must produce a valid feature row."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)
        feature_row, feature_cols = assemble_features(aligned, target_horizon=1)
        assert not feature_row.empty
        assert len(feature_cols) > 30

    def test_feature_row_has_target_lags(self):
        """Feature row must include PM2.5 lag features."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)
        feature_row, feature_cols = assemble_features(aligned, target_horizon=1)
        lag_cols = [c for c in feature_cols if "pm2_5_lag_" in c]
        assert len(lag_cols) == 8  # TARGET_LAGS has 8 entries

    def test_feature_row_has_temporal_features(self):
        """Feature row must include temporal encodings."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)
        feature_row, feature_cols = assemble_features(aligned, target_horizon=1)
        for f in ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos"]:
            assert f in feature_cols, f"Missing temporal feature: {f}"

    def test_freshness_check_with_recent_data(self):
        """Freshness check with available data should return finite freshness."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            check_freshness,
        )
        from tests.test_utils import get_data_aware_as_of
        as_of = get_data_aware_as_of(DB_PATH)
        raw = _load_recent_observations(DB_PATH, as_of, lookback_hours=96)
        aligned = _align_to_hourly(raw)
        freshness, warnings = check_freshness(aligned, as_of)
        # With data-aware as_of, freshness should be small (minutes, not hours)
        assert isinstance(freshness, float)
        assert freshness < 2, f"Freshness {freshness}h — expected < 2h with data-aware as_of"

    def test_freshness_check_with_stale_data(self):
        """Stale data must generate warnings."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            check_freshness,
        )
        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=48)
        aligned = _align_to_hourly(raw)
        # Ask about a time far enough beyond any data to guarantee staleness warnings
        future_time = datetime(2099, 1, 1, tzinfo=UTC)
        freshness, warnings = check_freshness(aligned, future_time)
        assert len(warnings) > 0

    def test_end_to_end_assembly(self):
        """Full assemble_prediction_features must succeed with real data."""
        from app.modeling.serving.feature_assembly import assemble_prediction_features
        from app.modeling.serving.model_store import ModelStore
        from tests.test_utils import get_data_aware_as_of
        store = ModelStore(MODELS_DIR)
        cached = store.load_horizon(1)
        as_of = get_data_aware_as_of(DB_PATH)
        result = assemble_prediction_features(
            db_path=DB_PATH,
            as_of=as_of,
            target_horizon=1,
            model_feature_names=cached.metadata.feature_names,
        )
        assert result.raw_observations_used > 0

    def test_missing_database_raises_error(self):
        """Loading from non-existent database must raise FileNotFoundError."""
        from app.modeling.serving.feature_assembly import _load_recent_observations
        with pytest.raises(FileNotFoundError):
            _load_recent_observations("/nonexistent/path.db", datetime.now(UTC))


# ═══════════════════════════════════════════════════════════════════
# 3. Prediction Service Tests
# ═══════════════════════════════════════════════════════════════════


class TestPredictionService:
    """Tests for the domain-level prediction orchestrator."""

    def _make_service(self):
        """Create a PredictionService with real models and DB."""
        from app.modeling.serving.model_store import ModelStore
        from app.modeling.serving.prediction_service import PredictionService
        store = ModelStore(MODELS_DIR)
        return PredictionService(
            model_store=store,
            db_path=str(DB_PATH),
            auto_load=True,
        )

    def test_service_initialises(self):
        """PredictionService must initialise with models loaded."""
        service = self._make_service()
        assert service.is_ready

    def test_predict_returns_result(self):
        """predict() must return a PredictionResult."""
        from app.modeling.serving.prediction_service import PredictionResult
        service = self._make_service()
        result = service.predict(horizon=1, record_to_db=False)
        assert isinstance(result, PredictionResult)

    def test_predict_has_model_provenance(self):
        """Prediction must identify which model produced it."""
        service = self._make_service()
        result = service.predict(horizon=1, record_to_db=False)
        assert result.model_version != ""
        assert result.algorithm in ("ridge", "hgb")
        assert result.forecast_horizon == 1

    def test_predict_returns_numeric_value(self):
        """Successful prediction must return a numeric PM2.5 value."""
        service = self._make_service()
        result = service.predict(horizon=1, record_to_db=False)
        if result.is_successful:
            assert isinstance(result.predicted_pm25, float)
            assert result.predicted_pm25 >= 0

    def test_predict_all_horizons(self):
        """predict_all_horizons must return results for all 5 horizons."""
        service = self._make_service()
        results = service.predict_all_horizons(record_to_db=False)
        assert len(results) == 5
        for h in [1, 3, 6, 12, 24]:
            assert h in results

    def test_predict_invalid_horizon_fails(self):
        """Unsupported horizon must produce an error result."""
        service = self._make_service()
        result = service.predict(horizon=99, record_to_db=False)
        assert not result.is_successful
        assert len(result.errors) > 0

    def test_predict_zero_horizon_fails(self):
        """Horizon 0 must produce an error result."""
        service = self._make_service()
        result = service.predict(horizon=0, record_to_db=False)
        assert not result.is_successful

    def test_prediction_result_serializable(self):
        """to_dict() must produce a valid JSON-serializable dict."""
        service = self._make_service()
        result = service.predict(horizon=1, record_to_db=False)
        d = result.to_dict()
        serialized = json.dumps(d, default=str)
        assert len(serialized) > 0

    def test_service_status_reports_ready(self):
        """status() must include ready=True when models are loaded."""
        service = self._make_service()
        status = service.status()
        assert status["ready"] is True
        assert "model_store" in status

    def test_service_records_to_db_when_requested(self):
        """When record_to_db=True, prediction_id must be set."""
        service = self._make_service()
        result = service.predict(horizon=1, record_to_db=True)
        if result.is_successful:
            assert result.prediction_id != ""


# ═══════════════════════════════════════════════════════════════════
# 4. Audit Trail Tests
# ═══════════════════════════════════════════════════════════════════


class TestAuditTrail:
    """Tests for prediction recording and retrieval."""

    def _make_temp_db(self, tmp_path: Path) -> str:
        """Create a temp database with the prediction schema."""
        from app.modeling.serving.audit import ensure_prediction_schema
        db = tmp_path / "test_audit.db"
        ensure_prediction_schema(db)
        return str(db)

    def test_ensure_prediction_schema(self):
        """Schema creation must create the prediction_records table."""
        with tempfile.TemporaryDirectory() as tmp:
            from app.modeling.serving.audit import ensure_prediction_schema
            db = Path(tmp) / "test.db"
            ensure_prediction_schema(db)
            conn = sqlite3.connect(str(db))
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "prediction_records" in table_names
            conn.close()

    def test_record_prediction(self):
        """Must write a prediction record and return an ID."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_temp_db(Path(tmp))
            from app.modeling.serving.audit import record_prediction
            pid = record_prediction(
                db_path=db,
                model_version="test_v1",
                algorithm="ridge",
                forecast_horizon=6,
                prediction_time=datetime.now(UTC),
                target_time=datetime.now(UTC) + timedelta(hours=6),
                predicted_value=42.5,
            )
            assert pid != ""
            assert len(pid) == 36  # UUID format

    def test_record_actual_updates_error(self):
        """Recording an actual value must compute prediction_error."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_temp_db(Path(tmp))
            from app.modeling.serving.audit import (
                get_recent_predictions,
                record_actual,
                record_prediction,
            )
            pid = record_prediction(
                db_path=db,
                model_version="test_v1",
                algorithm="ridge",
                forecast_horizon=6,
                prediction_time=datetime.now(UTC),
                target_time=datetime.now(UTC) + timedelta(hours=6),
                predicted_value=42.5,
            )
            record_actual(db, pid, actual_value=40.0)
            preds = get_recent_predictions(db)
            assert len(preds) == 1
            assert preds[0]["actual_value"] == 40.0
            assert preds[0]["prediction_error"] == 2.5

    def test_get_recent_predictions(self):
        """Must retrieve recent predictions from the database."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_temp_db(Path(tmp))
            from app.modeling.serving.audit import (
                get_recent_predictions,
                record_prediction,
            )
            # Insert 3 records
            for i in range(3):
                record_prediction(
                    db_path=db,
                    model_version=f"v{i}",
                    algorithm="ridge",
                    forecast_horizon=6,
                    prediction_time=datetime.now(UTC),
                    target_time=datetime.now(UTC) + timedelta(hours=6),
                    predicted_value=float(i * 10),
                )
            preds = get_recent_predictions(db, limit=10)
            assert len(preds) == 3

    def test_get_recent_predictions_by_horizon(self):
        """Must filter predictions by horizon."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_temp_db(Path(tmp))
            from app.modeling.serving.audit import (
                get_recent_predictions,
                record_prediction,
            )
            for h in [1, 6, 24]:
                record_prediction(
                    db_path=db,
                    model_version=f"v_h{h}",
                    algorithm="ridge",
                    forecast_horizon=h,
                    prediction_time=datetime.now(UTC),
                    target_time=datetime.now(UTC) + timedelta(hours=h),
                    predicted_value=float(h),
                )
            preds_h6 = get_recent_predictions(db, horizon=6)
            assert len(preds_h6) == 1
            assert preds_h6[0]["forecast_horizon"] == 6

    def test_count_predictions(self):
        """count_predictions must return accurate summary."""
        with tempfile.TemporaryDirectory() as tmp:
            db = self._make_temp_db(Path(tmp))
            from app.modeling.serving.audit import count_predictions, record_prediction
            for h in [1, 1, 6]:
                record_prediction(
                    db_path=db,
                    model_version="v1",
                    algorithm="ridge",
                    forecast_horizon=h,
                    prediction_time=datetime.now(UTC),
                    target_time=datetime.now(UTC),
                    predicted_value=50.0,
                )
            counts = count_predictions(db)
            assert counts["total_predictions"] == 3


# ═══════════════════════════════════════════════════════════════════
# 5. Feature Pipeline Consistency Tests
# ═══════════════════════════════════════════════════════════════════


class TestFeatureConsistency:
    """Verify the serving feature pipeline matches training exactly."""

    def test_feature_names_match_model_metadata(self):
        """Features produced by assembly must match model expectations."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        from app.modeling.serving.model_store import ModelStore

        store = ModelStore(MODELS_DIR)
        store.load_all()

        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)

        for h in [1, 3, 6, 12, 24]:
            cached = store.get(h)
            feature_row, feature_cols = assemble_features(aligned, target_horizon=h)
            model_features = set(cached.metadata.feature_names)
            produced_features = set(feature_cols)

            # All model features must be in the produced set
            missing = model_features - produced_features
            assert len(missing) == 0, (
                f"Horizon {h}h: model expects features not produced: {missing}"
            )

    def test_feature_count_matches_model(self):
        """Number of assembled features must equal model's expected count."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        from app.modeling.serving.model_store import ModelStore

        store = ModelStore(MODELS_DIR)
        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)

        for h in [1, 3, 6, 12, 24]:
            cached = store.load_horizon(h)
            feature_row, feature_cols = assemble_features(aligned, target_horizon=h)
            expected = len(cached.metadata.feature_names)
            actual = feature_row.shape[1]
            assert actual == expected, (
                f"Horizon {h}h: expected {expected} features, got {actual}"
            )

    def test_ridge_model_accepts_features(self):
        """The Ridge pipeline must accept assembled features without error."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        from app.modeling.serving.model_store import ModelStore

        store = ModelStore(MODELS_DIR)
        cached = store.load_horizon(1)  # Ridge model
        assert cached.metadata.algorithm == "ridge"

        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)
        feature_row, _ = assemble_features(aligned, target_horizon=1)
        preds = cached.predict(feature_row)
        assert len(preds) == 1

    def test_hgb_model_accepts_features(self):
        """The HGB pipeline must accept assembled features without error."""
        from app.modeling.serving.feature_assembly import (
            _align_to_hourly,
            _load_recent_observations,
            assemble_features,
        )
        from app.modeling.serving.model_store import ModelStore

        store = ModelStore(MODELS_DIR)
        cached = store.load_horizon(6)  # HGB model
        assert cached.metadata.algorithm == "hgb"

        now = datetime.now(UTC)
        raw = _load_recent_observations(DB_PATH, now, lookback_hours=96)
        aligned = _align_to_hourly(raw)
        feature_row, _ = assemble_features(aligned, target_horizon=6)
        preds = cached.predict(feature_row)
        assert len(preds) == 1


# ═══════════════════════════════════════════════════════════════════
# 6. No Fabrication Tests
# ═══════════════════════════════════════════════════════════════════


class TestNoFabrication:
    """Verify the system never fabricates data or results."""

    def test_models_are_real_joblib_files(self):
        """Model files must be real .joblib files, not placeholders."""
        for h in [1, 3, 6, 12, 24]:
            h_dir = MODELS_DIR / f"horizon_{h}h"
            joblib_files = list(h_dir.glob("*.joblib"))
            assert len(joblib_files) == 1
            # File must be > 1KB (a real model, not a stub)
            size = joblib_files[0].stat().st_size
            assert size > 1024, (
                f"Model file {joblib_files[0]} is suspiciously small ({size} bytes)"
            )

    def test_predictions_use_real_database(self):
        """Predictions must read from the real database, not generate synthetic data."""
        from app.modeling.serving.feature_assembly import _load_recent_observations
        now = datetime.now(UTC)
        df = _load_recent_observations(DB_PATH, now, lookback_hours=48)
        # Must have real timestamps (not all the same)
        if not df.empty:
            assert df.index.nunique() > 1

    def test_model_metadata_matches_training_results(self):
        """Model validation MAE must match Phase 4 training results."""
        from app.modeling.serving.model_store import ModelStore
        store = ModelStore(MODELS_DIR)
        # Expected val_mae from Phase 4 (approximate ranges)
        expected_ranges = {
            1: (4.0, 5.0),    # Ridge: ~4.50
            3: (10.0, 11.5),  # HGB: ~10.61
            6: (14.0, 15.5),  # HGB: ~14.45
            12: (16.0, 17.5), # HGB: ~16.34
            24: (17.5, 19.0), # Ridge: ~17.97
        }
        for h, (lo, hi) in expected_ranges.items():
            cached = store.load_horizon(h)
            actual_mae = cached.metadata.val_metrics["mae"]
            assert lo <= actual_mae <= hi, (
                f"Horizon {h}h val_mae={actual_mae} "
                f"outside expected range [{lo}, {hi}]"
            )


# ═══════════════════════════════════════════════════════════════════
# 7. Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Tests for graceful handling of edge cases."""

    def test_feature_coverage_check(self):
        """check_feature_coverage must detect missing features."""
        from app.modeling.serving.feature_assembly import check_feature_coverage
        row = pd.DataFrame({"a": [1.0], "b": [2.0]})
        missing = check_feature_coverage(row, ["a", "b", "c", "d"])
        assert "c" in missing
        assert "d" in missing
        assert "a" not in missing

    def test_feature_coverage_nan_detection(self):
        """NaN values must be flagged as missing."""
        from app.modeling.serving.feature_assembly import check_feature_coverage
        row = pd.DataFrame({"a": [1.0], "b": [np.nan]})
        missing = check_feature_coverage(row, ["a", "b"])
        assert "b" in missing
        assert "a" not in missing

    def test_empty_feature_row_not_usable(self):
        """Empty feature row must be marked as not usable."""
        from app.modeling.serving.feature_assembly import FeatureAssemblyResult
        result = FeatureAssemblyResult(
            timestamp=datetime.now(UTC),
            feature_row=pd.DataFrame(),
        )
        assert not result.is_usable

    def test_prediction_result_error_no_value(self):
        """PredictionResult with no value must report is_successful=False."""
        from app.modeling.serving.prediction_service import PredictionResult
        result = PredictionResult(errors=["something went wrong"])
        assert not result.is_successful
        assert result.predicted_pm25 is None

    def test_prediction_result_with_value(self):
        """PredictionResult with a value must report is_successful=True."""
        from app.modeling.serving.prediction_service import PredictionResult
        result = PredictionResult(predicted_pm25=42.5)
        assert result.is_successful


# ═══════════════════════════════════════════════════════════════════
# 8. Performance Tests
# ═══════════════════════════════════════════════════════════════════


class TestPerformance:
    """Verify serving layer meets latency requirements."""

    def test_full_prediction_under_30_seconds(self):
        """End-to-end prediction (cold: load + features + infer) under 30s.

        On a dev machine with a ~550 MB SQLite database the initial DB
        query can take 10-15 s.  The generous bound still catches
        pathological regressions while tolerating real-world I/O.
        """
        from app.modeling.serving.model_store import ModelStore
        from app.modeling.serving.prediction_service import PredictionService
        store = ModelStore(MODELS_DIR)
        service = PredictionService(
            model_store=store,
            db_path=str(DB_PATH),
            auto_load=True,
        )
        t0 = time.perf_counter()
        result = service.predict(horizon=1, record_to_db=False)
        elapsed = time.perf_counter() - t0
        assert elapsed < 30.0, f"Prediction took {elapsed:.2f}s (limit: 30s)"

    def test_cached_prediction_under_60_seconds(self):
        """After warm-up, predictions must complete under 60s.

        Model loading is cached in-process, but each prediction still
        queries the ~550 MB SQLite database for fresh features.  On a
        dev machine this takes 10-15 s per query.  The 60 s bound
        accounts for DB I/O on the large dataset plus inference.
        """
        from app.modeling.serving.model_store import ModelStore
        from app.modeling.serving.prediction_service import PredictionService
        store = ModelStore(MODELS_DIR)
        service = PredictionService(
            model_store=store,
            db_path=str(DB_PATH),
            auto_load=True,
        )
        # Warm up — caches model loading
        service.predict(horizon=1, record_to_db=False)
        # Timed run
        t0 = time.perf_counter()
        result = service.predict(horizon=1, record_to_db=False)
        elapsed = time.perf_counter() - t0
        assert elapsed < 60.0, f"Cached prediction took {elapsed:.2f}s (limit: 60s)"
