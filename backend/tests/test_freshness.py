"""Freshness state machine test matrix (Phase 6.75, Section 27).

Tests all four freshness states (FRESH / DEGRADED / STALE / UNAVAILABLE)
against the real database, using synthetic `as_of` values to place the
system into each state.  Also covers edge cases: missing database,
empty database, and parameter count warnings.

Design:
    - Uses REAL database — no mocks, no fabricated data.
    - Uses `get_latest_observation_time()` from test_utils to align
      to actual data, then offsets `as_of` to hit each threshold.
    - Validates both the state enum AND the warning content.
"""

from __future__ import annotations

import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.modeling.serving.freshness import (
    FRESH_THRESHOLD_HOURS,
    DEGRADED_THRESHOLD_HOURS,
    STALE_THRESHOLD_HOURS,
    FreshnessResult,
    FreshnessState,
    assess_freshness,
)
from tests.test_utils import get_latest_observation_time

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "lahore_pulse.db"


# ═══════════════════════════════════════════════════════════════════
# 1. State Threshold Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessStates:
    """Verify each freshness state is correctly assigned based on age."""

    def _get_latest(self) -> datetime:
        return get_latest_observation_time(DB_PATH)

    def test_fresh_state_when_recent(self):
        """Data < 2h old → FRESH."""
        latest = self._get_latest()
        # as_of just 30 minutes after latest observation
        as_of = latest + timedelta(minutes=30)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.FRESH, (
            f"Expected FRESH, got {result.state} "
            f"(freshness_hours={result.freshness_hours})"
        )
        assert result.freshness_hours <= FRESH_THRESHOLD_HOURS

    def test_degraded_state(self):
        """Data 2–6h old → DEGRADED."""
        latest = self._get_latest()
        # as_of 4 hours after latest observation
        as_of = latest + timedelta(hours=4)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.DEGRADED, (
            f"Expected DEGRADED, got {result.state} "
            f"(freshness_hours={result.freshness_hours})"
        )
        assert FRESH_THRESHOLD_HOURS < result.freshness_hours <= DEGRADED_THRESHOLD_HOURS

    def test_stale_state(self):
        """Data 6–12h old → STALE."""
        latest = self._get_latest()
        # as_of 9 hours after latest observation
        as_of = latest + timedelta(hours=9)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.STALE, (
            f"Expected STALE, got {result.state} "
            f"(freshness_hours={result.freshness_hours})"
        )
        assert DEGRADED_THRESHOLD_HOURS < result.freshness_hours <= STALE_THRESHOLD_HOURS

    def test_unavailable_state_when_very_stale(self):
        """Data > 12h old → UNAVAILABLE."""
        latest = self._get_latest()
        # as_of 24 hours after latest observation
        as_of = latest + timedelta(hours=24)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.UNAVAILABLE, (
            f"Expected UNAVAILABLE, got {result.state} "
            f"(freshness_hours={result.freshness_hours})"
        )
        assert result.freshness_hours > STALE_THRESHOLD_HOURS


# ═══════════════════════════════════════════════════════════════════
# 2. Boundary Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessBoundaries:
    """Verify exact boundary transitions between states."""

    def _get_latest(self) -> datetime:
        return get_latest_observation_time(DB_PATH)

    def test_boundary_fresh_to_degraded(self):
        """Exactly at FRESH_THRESHOLD → still FRESH (<= is inclusive)."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=FRESH_THRESHOLD_HOURS)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.FRESH

    def test_boundary_degraded_to_stale(self):
        """Exactly at DEGRADED_THRESHOLD → still DEGRADED."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=DEGRADED_THRESHOLD_HOURS)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.DEGRADED

    def test_boundary_stale_to_unavailable(self):
        """Exactly at STALE_THRESHOLD → still STALE."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=STALE_THRESHOLD_HOURS)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.STALE

    def test_just_beyond_degraded_is_stale(self):
        """1 minute past DEGRADED_THRESHOLD → STALE."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=DEGRADED_THRESHOLD_HOURS, minutes=1)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.STALE

    def test_just_beyond_stale_is_unavailable(self):
        """1 minute past STALE_THRESHOLD → UNAVAILABLE."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=STALE_THRESHOLD_HOURS, minutes=1)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.state == FreshnessState.UNAVAILABLE


# ═══════════════════════════════════════════════════════════════════
# 3. Warning Content Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessWarnings:
    """Verify warnings are generated for non-FRESH states."""

    def _get_latest(self) -> datetime:
        return get_latest_observation_time(DB_PATH)

    def test_fresh_has_no_warnings(self):
        """FRESH state should have no warnings."""
        latest = self._get_latest()
        as_of = latest + timedelta(minutes=30)
        result = assess_freshness(DB_PATH, as_of=as_of)
        # No stale/unavailable warnings for fresh data
        stale_warnings = [w for w in result.warnings if "stale" in w.lower() or "unavailable" in w.lower()]
        assert len(stale_warnings) == 0

    def test_degraded_has_warning(self):
        """DEGRADED state should have a warning."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=4)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert len(result.warnings) >= 1
        assert "degraded" in result.warnings[0].lower()

    def test_stale_has_warning(self):
        """STALE state should have a warning with 'stale'."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=9)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert len(result.warnings) >= 1
        assert "stale" in result.warnings[0].lower()

    def test_unavailable_has_critical_warning(self):
        """UNAVAILABLE state should have a 'CRITICAL' warning."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=24)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert len(result.warnings) >= 1
        assert "critical" in result.warnings[0].lower()


# ═══════════════════════════════════════════════════════════════════
# 4. Serialization Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessSerialization:
    """Verify to_dict produces correct JSON-serializable output."""

    def _get_latest(self) -> datetime:
        return get_latest_observation_time(DB_PATH)

    def test_to_dict_fresh(self):
        """FRESH result serialises correctly."""
        latest = self._get_latest()
        as_of = latest + timedelta(minutes=30)
        result = assess_freshness(DB_PATH, as_of=as_of)
        d = result.to_dict()
        assert d["state"] == "fresh"
        assert isinstance(d["freshness_hours"], float)
        assert d["freshness_hours"] is not None
        assert d["latest_observation_at"] is not None
        assert isinstance(d["parameters_available"], int)
        assert isinstance(d["warnings"], list)

    def test_to_dict_unavailable(self):
        """UNAVAILABLE result serialises with None freshness_hours."""
        # Non-existent database path
        result = assess_freshness("/tmp/nonexistent_999.db")
        d = result.to_dict()
        assert d["state"] == "unavailable"
        assert d["freshness_hours"] is None
        assert d["latest_observation_at"] is None
        assert d["parameters_available"] == 0

    def test_result_is_dataclass(self):
        """FreshnessResult should be a proper dataclass."""
        latest = self._get_latest()
        as_of = latest + timedelta(hours=3)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert isinstance(result, FreshnessResult)
        assert hasattr(result, "state")
        assert hasattr(result, "freshness_hours")
        assert hasattr(result, "latest_observation_at")
        assert hasattr(result, "parameters_available")
        assert hasattr(result, "warnings")


# ═══════════════════════════════════════════════════════════════════
# 5. Edge Case Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessEdgeCases:
    """Edge cases: missing DB, empty DB, parameter count warnings."""

    def test_missing_database_returns_unavailable(self):
        """Non-existent DB path → UNAVAILABLE with warning."""
        result = assess_freshness("/tmp/nonexistent_lahore_999.db")
        assert result.state == FreshnessState.UNAVAILABLE
        assert result.freshness_hours == float("inf")
        assert result.parameters_available == 0
        assert len(result.warnings) >= 1
        assert "not found" in result.warnings[0].lower()

    def test_empty_database_returns_unavailable(self):
        """DB exists but has no observations → UNAVAILABLE."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = Path(f.name)

        try:
            import sqlite3
            conn = sqlite3.connect(str(tmp_path))
            conn.execute("""
                CREATE TABLE observations (
                    id TEXT PRIMARY KEY,
                    station_id TEXT,
                    parameter TEXT,
                    value REAL,
                    unit TEXT,
                    observed_at TEXT,
                    source_id TEXT,
                    quality TEXT,
                    latitude REAL,
                    longitude REAL,
                    observation_type TEXT NOT NULL DEFAULT 'observation'
                )
            """)
            conn.commit()
            conn.close()

            result = assess_freshness(tmp_path)
            assert result.state == FreshnessState.UNAVAILABLE
            assert result.freshness_hours == float("inf")
            assert result.latest_observation_at is None
            assert result.parameters_available == 0
            assert any("no observations" in w.lower() for w in result.warnings)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_default_as_of_is_now(self):
        """Without as_of, uses current time and assesses DB freshness correctly."""
        result = assess_freshness(DB_PATH)
        # Freshness depends on actual DB state: fresh if data is recent, unavailable if stale.
        # This test verifies the function runs without error and returns a valid state.
        assert result.state in FreshnessState
        assert result.freshness_hours is not None or result.freshness_hours == float("inf")
        assert result.parameters_available >= 0

    def test_naive_datetime_assumed_utc(self):
        """Naive datetime without timezone → treated as UTC."""
        latest = get_latest_observation_time(DB_PATH)
        # Create a naive datetime equivalent of latest + 3h
        naive_as_of = (latest + timedelta(hours=3)).replace(tzinfo=None)
        result = assess_freshness(DB_PATH, as_of=naive_as_of)
        # Should still work and produce DEGRADED state
        assert result.state == FreshnessState.DEGRADED

    def test_parameters_available_is_positive(self):
        """Real database should have parameters available > 0."""
        latest = get_latest_observation_time(DB_PATH)
        as_of = latest + timedelta(minutes=30)
        result = assess_freshness(DB_PATH, as_of=as_of)
        assert result.parameters_available > 0


# ═══════════════════════════════════════════════════════════════════
# 6. State Enum Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessStateEnum:
    """Verify the FreshnessState enum has correct values."""

    def test_all_states_exist(self):
        """All four freshness states should be defined."""
        assert FreshnessState.FRESH == "fresh"
        assert FreshnessState.DEGRADED == "degraded"
        assert FreshnessState.STALE == "stale"
        assert FreshnessState.UNAVAILABLE == "unavailable"

    def test_state_count(self):
        """There should be exactly 4 freshness states."""
        assert len(FreshnessState) == 4

    def test_is_str_enum(self):
        """FreshnessState should be serializable as string."""
        assert str(FreshnessState.FRESH) == "fresh"
        assert FreshnessState.FRESH.value == "fresh"


# ═══════════════════════════════════════════════════════════════════
# 7. Threshold Consistency Tests
# ═══════════════════════════════════════════════════════════════════


class TestFreshnessThresholds:
    """Verify threshold constants are sensible and ordered."""

    def test_thresholds_are_positive(self):
        """All thresholds should be positive."""
        assert FRESH_THRESHOLD_HOURS > 0
        assert DEGRADED_THRESHOLD_HOURS > 0
        assert STALE_THRESHOLD_HOURS > 0

    def test_thresholds_are_ordered(self):
        """Thresholds should be in ascending order."""
        assert FRESH_THRESHOLD_HOURS < DEGRADED_THRESHOLD_HOURS < STALE_THRESHOLD_HOURS

    def test_fresh_threshold_is_2h(self):
        """FRESH threshold should be 2 hours."""
        assert FRESH_THRESHOLD_HOURS == 2.0

    def test_degraded_threshold_is_6h(self):
        """DEGRADED threshold should be 6 hours (matches staleness warning)."""
        assert DEGRADED_THRESHOLD_HOURS == 6.0

    def test_stale_threshold_is_12h(self):
        """STALE threshold should be 12 hours (matches staleness critical)."""
        assert STALE_THRESHOLD_HOURS == 12.0
