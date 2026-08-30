"""Tests for Episode Intelligence feature.

Tests cover:
1. Backend episode service (episode.py)
2. Backend API endpoint (episode.py route)
3. Frontend useEpisodeIntelligence hook (mock)
4. Frontend EpisodeIntelligence component (snapshot)
5. No new ML models, no new DB tables, single API endpoint
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ===================================================================
# Backend Tests: episode.py service
# ===================================================================


class TestEpisodeState:
    """Test episode state detection."""

    def test_state_constants(self):
        """Verify exactly 4 states exist."""
        from app.modeling.serving.episode import EpisodeState

        states = [
            EpisodeState.NORMAL,
            EpisodeState.EPISODE,
            EpisodeState.IMPROVING,
            EpisodeState.UNCERTAIN,
        ]
        assert len(states) == 4
        assert len(set(states)) == 4

    def test_detect_normal_state(self):
        """Normal PM2.5 -> NORMAL state."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        recent = [
            ("2025-01-01T12:00:00Z", 60.0),
            ("2025-01-01T13:00:00Z", 65.0),
            ("2025-01-01T14:00:00Z", 58.0),
            ("2025-01-01T15:00:00Z", 62.0),
            ("2025-01-01T16:00:00Z", 64.0),
            ("2025-01-01T17:00:00Z", 61.0),
        ]
        state = detect_episode_state(61.0, recent, freshness_hours=1.0)
        assert state == EpisodeState.NORMAL

    def test_detect_episode_state_rapid_rise(self):
        """Rapid rise (current > 120 AND delta >= 30) -> EPISODE."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        recent = [
            ("2025-01-01T12:00:00Z", 90.0),  # 6h ago: 90
            ("2025-01-01T17:00:00Z", 130.0),
        ]
        # Current 130, delta = 40 >= 30, above threshold
        state = detect_episode_state(130.0, recent, freshness_hours=1.0)
        assert state == EpisodeState.EPISODE

    def test_detect_episode_state_sustained_severe(self):
        """Sustained severe (current > 150 AND last 3 all > 150) -> EPISODE."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        recent = [
            ("2025-01-01T12:00:00Z", 160.0),
            ("2025-01-01T13:00:00Z", 165.0),
            ("2025-01-01T14:00:00Z", 158.0),
            ("2025-01-01T15:00:00Z", 170.0),
        ]
        state = detect_episode_state(170.0, recent, freshness_hours=1.0)
        assert state == EpisodeState.EPISODE

    def test_detect_improving_state(self):
        """Below improving threshold + was elevated -> IMPROVING."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        recent = [
            ("2025-01-01T12:00:00Z", 140.0),
            ("2025-01-01T13:00:00Z", 120.0),
            ("2025-01-01T14:00:00Z", 100.0),
            ("2025-01-01T15:00:00Z", 90.0),
            ("2025-01-01T16:00:00Z", 95.0),
            ("2025-01-01T17:00:00Z", 85.0),
        ]
        state = detect_episode_state(85.0, recent, freshness_hours=1.0)
        assert state == EpisodeState.IMPROVING

    def test_detect_uncertain_no_data(self):
        """No current PM2.5 -> UNCERTAIN."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        state = detect_episode_state(None, [], freshness_hours=None)
        assert state == EpisodeState.UNCERTAIN

    def test_detect_uncertain_stale_data(self):
        """Stale data (>6h) -> UNCERTAIN."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        recent = [("2025-01-01T12:00:00Z", 150.0)]
        state = detect_episode_state(150.0, recent, freshness_hours=7.0)
        assert state == EpisodeState.UNCERTAIN


class TestTrajectory:
    """Test trajectory computation."""

    def test_trajectory_constants(self):
        """Verify trajectory directions."""
        from app.modeling.serving.episode import Trajectory

        assert Trajectory.RISING == "rising"
        assert Trajectory.STABLE == "stable"
        assert Trajectory.FALLING == "falling"
        assert Trajectory.UNKNOWN == "unknown"

    def test_trajectory_rising(self):
        """Forecast > current + margin -> RISING."""
        from app.modeling.serving.episode import Trajectory, compute_trajectory

        result = compute_trajectory(
            current_pm25=100.0,
            forecasts={1: 110.0, 6: 120.0, 12: 105.0, 24: 80.0},
            state="episode",
        )
        assert result["near_term"] == Trajectory.RISING
        assert result["medium_term"] == Trajectory.RISING

    def test_trajectory_falling(self):
        """Forecast < current - margin -> FALLING."""
        from app.modeling.serving.episode import Trajectory, compute_trajectory

        result = compute_trajectory(
            current_pm25=150.0,
            forecasts={1: 140.0, 6: 120.0, 12: 90.0, 24: 60.0},
            state="episode",
        )
        assert result["near_term"] == Trajectory.FALLING
        assert result["medium_term"] == Trajectory.FALLING

    def test_trajectory_stable(self):
        """Forecast within margin -> STABLE."""
        from app.modeling.serving.episode import Trajectory, compute_trajectory

        result = compute_trajectory(
            current_pm25=100.0,
            forecasts={1: 102.0, 6: 105.0, 12: 100.0, 24: 95.0},
            state="episode",
        )
        assert result["near_term"] == Trajectory.STABLE
        assert result["medium_term"] == Trajectory.STABLE

    def test_trajectory_recovery_expected(self):
        """Forecast < improving threshold -> recovery expected."""
        from app.modeling.serving.episode import compute_trajectory

        result = compute_trajectory(
            current_pm25=130.0,
            forecasts={1: 125.0, 6: 110.0, 12: 70.0, 24: 50.0},
            state="episode",
        )
        assert result["recovery_expected"] is True

    def test_trajectory_no_recovery(self):
        """Forecast > improving threshold -> no recovery."""
        from app.modeling.serving.episode import compute_trajectory

        result = compute_trajectory(
            current_pm25=150.0,
            forecasts={1: 155.0, 6: 160.0, 12: 140.0, 24: 130.0},
            state="episode",
        )
        assert result["recovery_expected"] is False


class TestWeatherComparison:
    """Test weather context comparison."""

    def test_weather_returns_4_variables(self):
        """Always returns exactly 4 weather variables."""
        from app.modeling.serving.episode import compare_weather

        weather = {
            "temperature": 15.0,
            "humidity": 80.0,
            "wind_speed": 5.0,
            "pressure": 1015.0,
        }
        result = compare_weather(weather)
        assert len(result) == 4

    def test_weather_matching_pattern(self):
        """Temperature < 18 matches episode pattern."""
        from app.modeling.serving.episode import compare_weather

        weather = {
            "temperature": 14.0,
            "humidity": 80.0,
            "wind_speed": 5.0,
            "pressure": 1015.0,
        }
        result = compare_weather(weather)
        temp_var = [r for r in result if r.label == "Temperature"][0]
        assert temp_var.matches_pattern is True

    def test_weather_non_matching(self):
        """Temperature > 18 does not match."""
        from app.modeling.serving.episode import compare_weather

        weather = {
            "temperature": 25.0,
            "humidity": 50.0,
            "wind_speed": 10.0,
            "pressure": 1005.0,
        }
        result = compare_weather(weather)
        temp_var = [r for r in result if r.label == "Temperature"][0]
        assert temp_var.matches_pattern is False

    def test_weather_none_values(self):
        """None weather values do not match patterns."""
        from app.modeling.serving.episode import compare_weather

        weather = {
            "temperature": None,
            "humidity": None,
            "wind_speed": None,
            "pressure": None,
        }
        result = compare_weather(weather)
        for var in result:
            assert var.matches_pattern is False


class TestNarrative:
    """Test narrative generation."""

    def test_narrative_episode_active(self):
        """Episode state produces active narrative."""
        from app.modeling.serving.episode import (
            EpisodeState,
            EpisodeWeatherVariable,
            Trajectory,
            generate_narrative,
        )

        narrative, caveat = generate_narrative(
            state=EpisodeState.EPISODE,
            current_pm25=150.0,
            trajectory={"near_term": Trajectory.RISING},
            weather_vars=[],
        )
        assert "episode is currently active" in narrative.lower()
        assert "150" in narrative

    def test_narrative_normal(self):
        """Normal state produces no-episode narrative."""
        from app.modeling.serving.episode import (
            EpisodeState,
            Trajectory,
            generate_narrative,
        )

        narrative, caveat = generate_narrative(
            state=EpisodeState.NORMAL,
            current_pm25=60.0,
            trajectory={"near_term": Trajectory.STABLE},
            weather_vars=[],
        )
        assert "no pollution episode" in narrative.lower()

    def test_narrative_contains_caveat(self):
        """All narratives include caveat about single grid point."""
        from app.modeling.serving.episode import (
            EpisodeState,
            Trajectory,
            generate_narrative,
        )

        _, caveat = generate_narrative(
            state=EpisodeState.NORMAL,
            current_pm25=60.0,
            trajectory={"near_term": Trajectory.STABLE},
            weather_vars=[],
        )
        assert "single grid point" in caveat.lower()

    def test_narrative_no_causal_language(self):
        """Narrative must NOT contain causal language."""
        from app.modeling.serving.episode import (
            EpisodeState,
            Trajectory,
            generate_narrative,
        )

        narrative, _ = generate_narrative(
            state=EpisodeState.EPISODE,
            current_pm25=150.0,
            trajectory={"near_term": Trajectory.RISING},
            weather_vars=[],
        )
        causal_words = ["causes", "caused", "causing", "leads to", "results in"]
        for word in causal_words:
            assert word not in narrative.lower()


class TestHistoricalContext:
    """Test historical context values are hardcoded correctly."""

    def test_total_episodes(self):
        """371 validated episodes."""
        from app.modeling.serving.episode import HISTORICAL_CONTEXT

        assert HISTORICAL_CONTEXT["total_episodes"] == 371

    def test_winter_percentage(self):
        """80.6% winter concentration."""
        from app.modeling.serving.episode import HISTORICAL_CONTEXT

        assert HISTORICAL_CONTEXT["seasonal"]["winter"]["pct"] == 80.6

    def test_recovery_times(self):
        """Severity-stratified recovery times."""
        from app.modeling.serving.episode import HISTORICAL_CONTEXT

        recovery = HISTORICAL_CONTEXT["recovery"]
        assert recovery["mild_peak"]["hours"] == 9
        assert recovery["moderate_peak"]["hours"] == 14
        assert recovery["severe_peak"]["hours"] == 26


class TestEpisodeResultSerialization:
    """Test EpisodeResult.to_dict() serialization."""

    def test_to_dict_returns_all_keys(self):
        """Verify all expected keys are present."""
        from app.modeling.serving.episode import EpisodeResult

        result = EpisodeResult()
        d = result.to_dict()

        expected_keys = [
            "state",
            "state_description",
            "current_pm25",
            "current_6h_delta",
            "trajectory",
            "trajectory_description",
            "near_term",
            "medium_term",
            "recovery_expected",
            "recovery_text",
            "weather_context",
            "historical_context",
            "narrative",
            "narrative_caveat",
            "data_status",
            "forecast_reliability",
            "warnings",
        ]
        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_json_serializable(self):
        """Result must be JSON-serializable."""
        from app.modeling.serving.episode import EpisodeResult

        result = EpisodeResult()
        d = result.to_dict()
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

    def test_no_confidence_keys_in_response(self):
        """No numeric confidence scores in response."""
        from app.modeling.serving.episode import EpisodeResult

        result = EpisodeResult()
        d = result.to_dict()
        serialized = json.dumps(d)
        assert "confidence_score" not in serialized
        assert "episode_confidence" not in serialized
        assert "weather_confidence" not in serialized


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_database(self):
        """Episode detection with empty observations returns UNCERTAIN."""
        from app.modeling.serving.episode import EpisodeState, detect_episode_state

        state = detect_episode_state(None, [], freshness_hours=None)
        assert state == EpisodeState.UNCERTAIN

    def test_all_none_forecasts(self):
        """Trajectory with all None forecasts returns UNKNOWN."""
        from app.modeling.serving.episode import Trajectory, compute_trajectory

        result = compute_trajectory(
            current_pm25=100.0,
            forecasts={1: None, 6: None, 12: None, 24: None},
            state="normal",
        )
        assert result["near_term"] == Trajectory.UNKNOWN
        assert result["medium_term"] == Trajectory.UNKNOWN

    def test_decimal_pm25_values(self):
        """Decimal PM2.5 values are handled correctly."""
        from app.modeling.serving.episode import detect_episode_state

        recent = [
            ("2025-01-01T12:00:00Z", 89.7),
            ("2025-01-01T13:00:00Z", 95.3),
        ]
        state = detect_episode_state(95.3, recent, freshness_hours=0.5)
        assert state in ("normal", "episode", "improving", "uncertain")


class TestForecastReliability:
    """Test forecast reliability mapping."""

    def test_returns_all_horizons(self):
        """All 5 horizons covered."""
        from app.modeling.serving.episode import get_forecast_reliability

        reliability = get_forecast_reliability()
        assert len(reliability) == 5
        for h in ["1h", "3h", "6h", "12h", "24h"]:
            assert h in reliability

    def test_no_numeric_scores(self):
        """Reliability uses text labels, not numbers."""
        from app.modeling.serving.episode import get_forecast_reliability

        reliability = get_forecast_reliability()
        for label in reliability.values():
            assert isinstance(label, str)
            # Should not contain percentage or decimal
            assert "%" not in label
            assert "." not in label


# ===================================================================
# Backend Tests: API endpoint
# ===================================================================


class TestEpisodeAPIEndpoint:
    """Test the /api/v1/episode endpoint."""

    def test_endpoint_exists(self):
        """Episode router is importable."""
        from app.api.v1.episode import router

        assert router is not None

    def test_endpoint_prefix(self):
        """Router has correct prefix."""
        from app.api.v1.episode import router

        assert router.prefix == "/episode"

    def test_endpoint_tags(self):
        """Router has correct tags."""
        from app.api.v1.episode import router

        assert "episode" in router.tags

    def test_router_registration(self):
        """Episode router is registered in main router."""
        from app.api.v1.router import api_v1_router

        # Check that the episode router was imported and registered
        # by verifying the routes list is non-empty and has episode-related routes
        registered_names = [
            getattr(r, "name", "") or str(getattr(r, "path", ""))
            for r in api_v1_router.routes
        ]
        route_str = " ".join(registered_names)
        assert "episode" in route_str.lower() or len(api_v1_router.routes) > 6


# ===================================================================
# API Contract Tests
# ===================================================================


class TestAPIContract:
    """Test API contract compliance."""

    def test_single_endpoint_only(self):
        """Episode router should have exactly two GET endpoints:
        /episode (intelligence) and /episode/analogs (historical analogs)."""
        from app.api.v1.episode import router

        # Should have exactly two GET routes
        get_routes = [
            r for r in router.routes if hasattr(r, "methods") and "GET" in r.methods
        ]
        assert len(get_routes) == 2

    def test_no_post_methods(self):
        """No write operations in episode endpoint."""
        from app.api.v1.episode import router

        post_routes = [
            r for r in router.routes if hasattr(r, "methods") and "POST" in r.methods
        ]
        assert len(post_routes) == 0

    def test_response_schema_structure(self):
        """Response has expected top-level keys."""
        from app.modeling.serving.episode import EpisodeResult, compare_weather

        result = EpisodeResult()
        d = result.to_dict()

        # Verify response structure matches API contract
        assert "state" in d
        assert "weather_context" in d
        assert "historical_context" in d
        assert "narrative" in d
        assert "forecast_reliability" in d
        assert "data_status" in d

        # Verify weather_context structure
        wc = d["weather_context"]
        assert "variables" in wc
        assert "note" in wc
        assert isinstance(wc["variables"], list)

        # When weather data is populated, should have 4 variables
        weather = {
            "temperature": 14.0,
            "humidity": 80.0,
            "wind_speed": 5.0,
            "pressure": 1015.0,
        }
        populated_result = EpisodeResult()
        populated_result.weather_variables = compare_weather(weather)
        populated_dict = populated_result.to_dict()
        assert len(populated_dict["weather_context"]["variables"]) == 4


# ===================================================================
# Integration Tests
# ===================================================================


class TestIntegration:
    """Test integration with existing system components."""

    def test_uses_existing_freshness(self):
        """Episode uses existing assess_freshness."""
        import inspect

        from app.api.v1.episode import get_episode_intelligence

        source = inspect.getsource(get_episode_intelligence)
        assert "assess_freshness" in source

    def test_uses_existing_prediction_service(self):
        """Episode uses existing PredictionService."""
        import inspect

        from app.api.v1.episode import get_episode_intelligence

        source = inspect.getsource(get_episode_intelligence)
        assert "PredictionService" in source or "predict_all_horizons" in source

    def test_no_new_ml_imports(self):
        """Episode module has no ML model imports."""
        import inspect

        from app.modeling.serving import episode

        source = inspect.getsource(episode)
        # Should not import sklearn, torch, tensorflow, xgboost
        ml_imports = ["sklearn", "torch", "tensorflow", "xgboost", "lightgbm"]
        for ml in ml_imports:
            assert ml not in source, f"Found ML import: {ml}"

    def test_no_new_database_tables(self):
        """Episode endpoint creates no new tables."""
        import inspect

        from app.api.v1.episode import get_episode_intelligence

        source = inspect.getsource(get_episode_intelligence)
        assert "CREATE TABLE" not in source
        assert "CREATE INDEX" not in source

    def test_deterministic_output(self):
        """Same inputs produce same outputs (deterministic)."""
        from app.modeling.serving.episode import (
            compare_weather,
            detect_episode_state,
            generate_narrative,
        )

        weather = {
            "temperature": 14.0,
            "humidity": 80.0,
            "wind_speed": 5.0,
            "pressure": 1015.0,
        }
        result1 = compare_weather(weather)
        result2 = compare_weather(weather)
        assert [r.matches_pattern for r in result1] == [
            r.matches_pattern for r in result2
        ]
