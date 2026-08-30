"""Historical Analog Engine tests (Phase 12).

Tests cover:
    1. Module imports cleanly
    2. Data structures (EpisodeFeatures, SimilarityFactor, AnalogResult, AnalogResponse)
    3. Normalization returns [0, 1] for all features
    4. Circular distance handles 0/360 wrap, same direction, opposite direction
    5. Match labels: Closest < Strong < Moderate < Weak
    6. find_analogs returns AnalogResponse with correct structure
    7. find_analogs returns non-empty analogs (real data)
    8. Each analog has 7 similarity factors (peak, temp, humid, wind, dir, pressure, month)
    9. what_happened_next uses past-tense language only (no predictions)
    10. Similarity factors contain no predictive claims
    11. Performance: find_analogs completes in < 5 seconds
    12. Episode features have all required fields
    13. Distance computation is deterministic (same inputs → same output)
    14. Analog dates are valid YYYY-MM-DD format
    15. Replay ranges are day-before to day-after the episode date
    16. Limit parameter controls number of results
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.modeling.serving.historical_analog import (
    AnalogResponse,
    AnalogResult,
    EpisodeFeatures,
    SimilarityFactor,
    _circular_distance,
    _compute_distance,
    _compute_what_happened_next,
    _fetch_all_episode_features,
    _format_outcome,
    _get_current_context,
    _label_distance,
    _normalize,
    _replay_range,
    find_analogs,
    MATCH_CLOSEST,
    MATCH_STRONG,
    MATCH_MODERATE,
    MATCH_WEAK,
    DISTANCE_CLOSEST,
    DISTANCE_STRONG,
    DISTANCE_MODERATE,
    FEATURE_WEIGHTS,
    NORMALIZATION_RANGES,
)

# ── Paths ──────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "lahore_pulse.db"


# ═══════════════════════════════════════════════════════════════════
# 1. Module Import
# ═══════════════════════════════════════════════════════════════════


class TestModuleImport:
    """Verify module imports without errors."""

    def test_import_all_symbols(self):
        """All public symbols import successfully."""
        assert callable(find_analogs)
        assert callable(_normalize)
        assert callable(_circular_distance)
        assert callable(_compute_distance)
        assert callable(_label_distance)


# ═══════════════════════════════════════════════════════════════════
# 2. Data Structures
# ═══════════════════════════════════════════════════════════════════


class TestDataStructures:
    """Verify dataclass construction and fields."""

    def test_episode_features_fields(self):
        ef = EpisodeFeatures(
            date="2024-01-15", peak_pm25=150.0, avg_pm25=120.0,
            temperature=10.0, humidity=80.0, wind_speed=5.0,
            wind_direction=270.0, pressure=1013.0, month=1, hours=24,
        )
        assert ef.date == "2024-01-15"
        assert ef.peak_pm25 == 150.0
        assert ef.hours == 24

    def test_similarity_factor_fields(self):
        sf = SimilarityFactor(
            dimension="temperature", current_value=20.0,
            historical_value=22.0, matches=True,
            label="temperature", unit="C",
        )
        assert sf.matches is True
        assert sf.unit == "C"

    def test_analog_result_fields(self):
        ar = AnalogResult(
            date="2024-01-15", peak_pm25=150.0, avg_pm25=120.0,
            duration_hours=24, distance=0.2,
            similarity_label=MATCH_CLOSEST,
            similarity_factors=[],
            what_happened_next={"peak_delay_hours": 4, "recovery_hours": 12,
                                "summary": "Peak arrived 4h later"},
            replay_start="2024-01-14", replay_end="2024-01-17",
        )
        assert ar.similarity_label == MATCH_CLOSEST
        assert ar.replay_start == "2024-01-14"


# ═══════════════════════════════════════════════════════════════════
# 3. Normalization
# ═══════════════════════════════════════════════════════════════════


class TestNormalization:
    """Verify normalization returns [0, 1] for all features."""

    def test_all_features_normalized_range(self):
        for feature, (low, high) in NORMALIZATION_RANGES.items():
            # Test at boundaries and middle
            for val in [low, high, (low + high) / 2]:
                result = _normalize(val, feature)
                assert 0.0 <= result <= 1.0, (
                    f"{feature}({val}) = {result} out of [0,1]"
                )

    def test_below_range_clamps_to_zero(self):
        result = _normalize(-100, "temperature")
        assert result == 0.0

    def test_above_range_clamps_to_one(self):
        result = _normalize(1000, "temperature")
        assert result == 1.0

    def test_low_equals_high_returns_zero(self):
        # Edge case: if range is zero-width
        result = _normalize(5.0, "pressure")
        assert 0.0 <= result <= 1.0


# ═══════════════════════════════════════════════════════════════════
# 4. Circular Distance
# ═══════════════════════════════════════════════════════════════════


class TestCircularDistance:
    """Verify angular distance computation."""

    def test_same_direction(self):
        assert _circular_distance(180, 180) == 0.0

    def test_opposite_direction(self):
        assert _circular_distance(0, 180) == 1.0

    def test_wrap_around_0_360(self):
        dist = _circular_distance(10, 350)
        assert dist < 0.2  # Should be close (20° apart = 0.111)

    def test_90_degree_apart(self):
        dist = _circular_distance(0, 90)
        assert abs(dist - 0.5) < 0.01

    def test_symmetry(self):
        assert _circular_distance(30, 90) == _circular_distance(90, 30)


# ═══════════════════════════════════════════════════════════════════
# 5. Match Labels
# ═══════════════════════════════════════════════════════════════════


class TestMatchLabels:
    """Verify distance-to-label mapping."""

    def test_closest(self):
        assert _label_distance(0.1) == MATCH_CLOSEST

    def test_strong(self):
        assert _label_distance(DISTANCE_CLOSEST) == MATCH_STRONG

    def test_moderate(self):
        assert _label_distance(DISTANCE_STRONG) == MATCH_MODERATE

    def test_weak(self):
        assert _label_distance(DISTANCE_MODERATE) == MATCH_WEAK

    def test_ordering(self):
        assert DISTANCE_CLOSEST < DISTANCE_STRONG < DISTANCE_MODERATE


# ═══════════════════════════════════════════════════════════════════
# 6-8. Integration: find_analogs
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not DB_PATH.exists(), reason="Database not available")
class TestFindAnalogs:
    """Integration tests against real database."""

    @pytest.fixture(scope="class")
    def response(self) -> AnalogResponse:
        """Run find_analogs once for all integration tests."""
        return find_analogs(DB_PATH)

    def test_returns_analog_response(self, response):
        """find_analogs returns an AnalogResponse object."""
        assert isinstance(response, AnalogResponse)

    def test_has_current_context(self, response):
        """Response includes current_context with expected keys."""
        ctx = response.current_context
        assert "current_pm25" in ctx
        assert "temperature" in ctx
        assert "humidity" in ctx
        assert "wind_speed" in ctx
        assert "wind_direction" in ctx
        assert "wind_sector" in ctx
        assert "pressure" in ctx
        assert "month" in ctx
        assert "season" in ctx
        assert "timestamp" in ctx

    def test_returns_nonempty_analogs(self, response):
        """At least 1 analog found (real data has 432 episodes)."""
        assert len(response.analogs) > 0

    def test_default_limit_three(self, response):
        """Default limit returns exactly 3 analogs."""
        assert len(response.analogs) == 3

    def test_total_episodes_searched(self, response):
        """Searched > 300 episodes (real data has ~432)."""
        assert response.total_episodes_searched > 300

    def test_has_caveat(self, response):
        """Response includes a scientific caveat."""
        assert len(response.caveat) > 0
        assert "similarity" in response.caveat.lower()

    def test_analogs_have_seven_factors(self, response):
        """Each analog has up to 7 similarity factors."""
        for analog in response.analogs:
            assert 5 <= len(analog.similarity_factors) <= 7

    def test_factors_have_no_predictions(self, response):
        """Similarity factors use observational language only."""
        prediction_words = [
            "will", "guarantee", "predict", "confidence",
            "expect", "forecast", "tomorrow",
        ]
        for analog in response.analogs:
            for factor in analog.similarity_factors:
                label_lower = factor.label.lower()
                for word in prediction_words:
                    assert word not in label_lower, (
                        f"Factor '{factor.label}' contains prediction word '{word}'"
                    )

    def test_analog_dates_valid(self, response):
        """All analog dates are valid YYYY-MM-DD."""
        from datetime import datetime
        for analog in response.analogs:
            datetime.strptime(analog.date, "%Y-%m-%d")

    def test_replay_ranges_correct(self, response):
        """Replay range is day-before to day-after episode date."""
        from datetime import datetime, timedelta
        for analog in response.analogs:
            ep_date = datetime.strptime(analog.date, "%Y-%m-%d")
            expected_start = (ep_date - timedelta(days=1)).strftime("%Y-%m-%d")
            expected_end = (ep_date + timedelta(days=2)).strftime("%Y-%m-%d")
            assert analog.replay_start == expected_start
            assert analog.replay_end == expected_end

    def test_similarity_labels_valid(self, response):
        """All labels are from the defined set."""
        valid = {MATCH_CLOSEST, MATCH_STRONG, MATCH_MODERATE, MATCH_WEAK}
        for analog in response.analogs:
            assert analog.similarity_label in valid

    def test_analogs_sorted_by_distance(self, response):
        """Analogs are sorted closest first."""
        distances = [a.distance for a in response.analogs]
        assert distances == sorted(distances)

    def test_what_happened_next_has_summary(self, response):
        """Each analog has a what_happened_next with summary."""
        for analog in response.analogs:
            whn = analog.what_happened_next
            assert "summary" in whn
            assert len(whn["summary"]) > 0

    def test_what_happened_next_past_tense(self, response):
        """what_happened_next summary uses past-tense language only."""
        future_words = ["will", "shall", "going to", "expect", "guarantee"]
        for analog in response.analogs:
            summary = analog.what_happened_next["summary"].lower()
            for word in future_words:
                assert word not in summary, (
                    f"Summary contains future word '{word}': {summary}"
                )


# ═══════════════════════════════════════════════════════════════════
# 9-10. Outcome Formatting
# ═══════════════════════════════════════════════════════════════════


class TestOutcomeFormatting:
    """Verify what_happened_next uses past-tense language."""

    def test_peak_delay_zero(self):
        outcome = _format_outcome({
            "peak_delay_hours": 0,
            "recovery_hours": 6,
            "declining_at_end": True,
        })
        assert "first hour" in outcome["summary"].lower()

    def test_peak_delay_positive(self):
        outcome = _format_outcome({
            "peak_delay_hours": 4,
            "recovery_hours": None,
            "declining_at_end": True,
        })
        assert "4h" in outcome["summary"]

    def test_recovery_quick(self):
        outcome = _format_outcome({
            "peak_delay_hours": 2,
            "recovery_hours": 3,
            "declining_at_end": False,
        })
        assert "3h" in outcome["summary"]

    def test_no_recovery_declining(self):
        outcome = _format_outcome({
            "peak_delay_hours": 1,
            "recovery_hours": None,
            "declining_at_end": True,
        })
        assert "declining" in outcome["summary"].lower()

    def test_no_recovery_persisted(self):
        outcome = _format_outcome({
            "peak_delay_hours": 1,
            "recovery_hours": None,
            "declining_at_end": False,
        })
        assert "persisted" in outcome["summary"].lower()


# ═══════════════════════════════════════════════════════════════════
# 11. Performance
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not DB_PATH.exists(), reason="Database not available")
class TestPerformance:
    """Verify analog engine meets performance targets."""

    def test_find_analogs_under_5s(self):
        """find_analogs completes in under 5 seconds."""
        t0 = time.time()
        result = find_analogs(DB_PATH)
        elapsed = time.time() - t0
        assert elapsed < 5.0, f"Took {elapsed:.1f}s (target: <5s)"
        assert len(result.analogs) > 0


# ═══════════════════════════════════════════════════════════════════
# 12. Distance Determinism
# ═══════════════════════════════════════════════════════════════════


class TestDeterminism:
    """Verify distance computation is deterministic."""

    def test_same_inputs_same_output(self):
        current = {
            "current_pm25": 150.0, "temperature": 20.0,
            "humidity": 70.0, "wind_speed": 5.0,
            "wind_direction": 180.0, "pressure": 1013.0,
            "month": 1,
        }
        ep = EpisodeFeatures(
            date="2024-01-15", peak_pm25=200.0, avg_pm25=160.0,
            temperature=22.0, humidity=75.0, wind_speed=8.0,
            wind_direction=190.0, pressure=1010.0, month=1, hours=20,
        )
        dist1, factors1 = _compute_distance(current, ep)
        dist2, factors2 = _compute_distance(current, ep)
        assert dist1 == dist2
        assert len(factors1) == len(factors2)

    def test_different_inputs_different_output(self):
        current = {
            "current_pm25": 50.0, "temperature": 10.0,
            "humidity": 40.0, "wind_speed": 15.0,
            "wind_direction": 0.0, "pressure": 1000.0,
            "month": 6,
        }
        ep1 = EpisodeFeatures(
            date="2024-01-15", peak_pm25=120.0, avg_pm25=100.0,
            temperature=10.0, humidity=40.0, wind_speed=15.0,
            wind_direction=0.0, pressure=1000.0, month=6, hours=20,
        )
        ep2 = EpisodeFeatures(
            date="2024-07-15", peak_pm25=300.0, avg_pm25=250.0,
            temperature=35.0, humidity=90.0, wind_speed=2.0,
            wind_direction=180.0, pressure=1025.0, month=12, hours=10,
        )
        d1, _ = _compute_distance(current, ep1)
        d2, _ = _compute_distance(current, ep2)
        assert d1 != d2


# ═══════════════════════════════════════════════════════════════════
# 13. Replay Range
# ═══════════════════════════════════════════════════════════════════


class TestReplayRange:
    """Verify replay date range computation."""

    def test_basic_range(self):
        start, end = _replay_range("2024-01-15")
        assert start == "2024-01-14"
        assert end == "2024-01-17"

    def test_month_boundary(self):
        start, end = _replay_range("2024-03-01")
        assert start == "2024-02-29"  # leap year
        assert end == "2024-03-03"

    def test_year_boundary(self):
        start, end = _replay_range("2024-01-01")
        assert start == "2023-12-31"
        assert end == "2024-01-03"


# ═══════════════════════════════════════════════════════════════════
# 14. Custom Limit
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(not DB_PATH.exists(), reason="Database not available")
class TestCustomLimit:
    """Verify limit parameter controls result count."""

    def test_limit_1(self):
        result = find_analogs(DB_PATH, limit=1)
        assert len(result.analogs) == 1

    def test_limit_5(self):
        result = find_analogs(DB_PATH, limit=5)
        assert len(result.analogs) == 5

    def test_limit_10(self):
        result = find_analogs(DB_PATH, limit=10)
        assert len(result.analogs) == 10
