"""Phase 6 tests — Investigation Learning & Accountability.

Tests cover:
    1. Schema validation: EvidenceStatus, ReliabilityClassification, context snapshot, response
    2. Band classification helpers: PM2.5, wind speed, temperature, humidity
    3. Distance calculations: band, sector, list, exact
    4. Similarity calculation: weighted scoring across dimensions
    5. Reliability calculation: scoring, classification, minimum thresholds
    6. Context building: evidence package → InvestigationContextSnapshot
    7. Full learning analytics: compute_investigation_learning with real DB
    8. API endpoint: demo mode and error handling
    9. Design rules: framing, minimum thresholds, limitations

All tests use deterministic calculations (NO ML).
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ── Paths ──────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _create_test_db(tmp_path: Path) -> Path:
    """Create a test database with verification_outcomes table."""
    db_path = tmp_path / "test_lahore_pulse.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verification_outcomes (
            outcome_id                      TEXT PRIMARY KEY,
            investigation_id                 TEXT NOT NULL,
            overall_status                  TEXT NOT NULL,
            recommendation_verification     TEXT,
            investigation_area_verification  TEXT,
            hypothesis_verifications         TEXT,
            field_notes                      TEXT,
            verified_by                      TEXT,
            verified_at                      TEXT,
            created_at                       TEXT NOT NULL,
            updated_at                       TEXT NOT NULL,
            investigation_context            TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()
    return db_path


def _insert_outcome(
    db_path: Path,
    outcome_id: str,
    investigation_id: str,
    overall_status: str,
    recommendation_verification: str = "UNKNOWN",
    investigation_area_verification: str = "UNKNOWN",
    field_notes: str = "",
    verified_by: str = "test_user",
    verified_at: str = "2024-11-01T10:00:00",
    created_at: str = "2024-11-01T10:00:00",
    updated_at: str = "2024-11-01T10:00:00",
    investigation_context: dict | None = None,
) -> None:
    """Insert a verification outcome into the test database."""
    conn = sqlite3.connect(str(db_path))
    context_json = json.dumps(investigation_context) if investigation_context else None
    conn.execute(
        """
        INSERT INTO verification_outcomes
            (outcome_id, investigation_id, overall_status,
             recommendation_verification, investigation_area_verification,
             hypothesis_verifications, field_notes, verified_by,
             verified_at, created_at, updated_at, investigation_context)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            outcome_id,
            investigation_id,
            overall_status,
            recommendation_verification,
            investigation_area_verification,
            None,
            field_notes,
            verified_by,
            verified_at,
            created_at,
            updated_at,
            context_json,
        ),
    )
    conn.commit()
    conn.close()


def _make_context(**overrides) -> dict:
    """Build a standard investigation context snapshot dict."""
    base = {
        "pm25_value": 165.0,
        "pm25_severity_band": "UNHEALTHY",
        "wind_sector": "E",
        "wind_speed_ms": 3.2,
        "wind_speed_band": "LIGHT",
        "temperature_c": 14.0,
        "temperature_band": "COOL",
        "humidity_pct": 68.0,
        "humidity_band": "MODERATE",
        "investigation_corridor": "East Corridor",
        "eligible_domains": ["open-burning", "traffic-emissions"],
        "trajectory": "rising",
        "episode_state": "episode",
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════
# 1. Schema Validation Tests
# ═══════════════════════════════════════════════════════════════════


class TestLearningSchemas:
    """Pydantic v2 schema validation for Phase 6."""

    def test_evidence_status_enum(self):
        from app.modeling.serving.learning_schemas import EvidenceStatus
        assert EvidenceStatus.INSUFFICIENT.value == "INSUFFICIENT"
        assert EvidenceStatus.LIMITED.value == "LIMITED"
        assert EvidenceStatus.MODERATE.value == "MODERATE"
        assert EvidenceStatus.STRONG.value == "STRONG"

    def test_reliability_classification_enum(self):
        from app.modeling.serving.learning_schemas import ReliabilityClassification
        assert ReliabilityClassification.INSUFFICIENT.value == "INSUFFICIENT"
        assert ReliabilityClassification.STRONG.value == "STRONG"

    def test_context_snapshot_defaults(self):
        from app.modeling.serving.learning_schemas import InvestigationContextSnapshot
        snap = InvestigationContextSnapshot()
        assert snap.pm25_severity_band == "UNKNOWN"
        assert snap.wind_sector == "UNKNOWN"
        assert snap.eligible_domains == []
        assert snap.trajectory == "UNKNOWN"

    def test_context_snapshot_with_values(self):
        from app.modeling.serving.learning_schemas import InvestigationContextSnapshot
        snap = InvestigationContextSnapshot(
            pm25_value=165.0,
            pm25_severity_band="UNHEALTHY",
            wind_sector="E",
            wind_speed_ms=3.2,
            wind_speed_band="LIGHT",
            temperature_c=14.0,
            temperature_band="COOL",
            humidity_pct=68.0,
            humidity_band="MODERATE",
            investigation_corridor="East Corridor",
            eligible_domains=["open-burning"],
            trajectory="rising",
            episode_state="episode",
        )
        assert snap.pm25_value == 165.0
        assert snap.wind_sector == "E"
        assert snap.investigation_corridor == "East Corridor"

    def test_reliability_score_defaults(self):
        from app.modeling.serving.learning_schemas import ReliabilityScore, ReliabilityClassification
        rs = ReliabilityScore()
        assert rs.score is None
        assert rs.classification == ReliabilityClassification.INSUFFICIENT
        assert rs.total_evaluated == 0

    def test_similar_case_schema(self):
        from app.modeling.serving.learning_schemas import SimilarCase
        case = SimilarCase(
            investigation_id="INV-001",
            outcome_id="VER-001",
            similarity_score=0.85,
            date="2024-11-01",
            overall_status="USEFUL",
            recommendation_verification="SUPPORTED",
        )
        assert case.similarity_score == 0.85
        assert case.matching_dimensions == []

    def test_learning_response_defaults(self):
        from app.modeling.serving.learning_schemas import InvestigationLearningResponse
        resp = InvestigationLearningResponse()
        assert resp.historical_investigations_found == 0
        assert resp.similar_cases == []
        assert resp.evidence_status.value == "INSUFFICIENT"

    def test_learning_response_is_serializable(self):
        from app.modeling.serving.learning_schemas import InvestigationLearningResponse
        resp = InvestigationLearningResponse(
            historical_investigations_found=5,
            evidence_status="MODERATE",
        )
        dumped = resp.model_dump()
        assert dumped["historical_investigations_found"] == 5
        assert isinstance(dumped, dict)


# ═══════════════════════════════════════════════════════════════════
# 2. Band Classification Tests
# ═══════════════════════════════════════════════════════════════════


class TestBandClassification:
    """Test PM2.5, wind speed, temperature, humidity band classification."""

    def test_classify_pm25_good(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(5.0) == "GOOD"

    def test_classify_pm25_moderate(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(25.0) == "MODERATE"

    def test_classify_pm25_unhealthy_sensitive(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(45.0) == "UNHEALTHY_SENSITIVE"

    def test_classify_pm25_unhealthy(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(100.0) == "UNHEALTHY"

    def test_classify_pm25_very_unhealthy(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(200.0) == "VERY_UNHEALTHY"

    def test_classify_pm25_hazardous(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(300.0) == "HAZARDOUS"

    def test_classify_pm25_none(self):
        from app.application.services.investigation_learning import classify_pm25_band
        assert classify_pm25_band(None) == "UNKNOWN"

    def test_classify_wind_speed_calm(self):
        from app.application.services.investigation_learning import classify_wind_speed_band
        assert classify_wind_speed_band(0.5) == "CALM"

    def test_classify_wind_speed_light(self):
        from app.application.services.investigation_learning import classify_wind_speed_band
        assert classify_wind_speed_band(3.0) == "LIGHT"

    def test_classify_wind_speed_moderate(self):
        from app.application.services.investigation_learning import classify_wind_speed_band
        assert classify_wind_speed_band(7.0) == "MODERATE"

    def test_classify_wind_speed_strong(self):
        from app.application.services.investigation_learning import classify_wind_speed_band
        assert classify_wind_speed_band(12.0) == "STRONG"

    def test_classify_temperature_cold(self):
        from app.application.services.investigation_learning import classify_temperature_band
        assert classify_temperature_band(5.0) == "COLD"

    def test_classify_temperature_cool(self):
        from app.application.services.investigation_learning import classify_temperature_band
        assert classify_temperature_band(14.0) == "COOL"

    def test_classify_temperature_warm(self):
        from app.application.services.investigation_learning import classify_temperature_band
        assert classify_temperature_band(25.0) == "WARM"

    def test_classify_temperature_hot(self):
        from app.application.services.investigation_learning import classify_temperature_band
        assert classify_temperature_band(35.0) == "HOT"

    def test_classify_humidity_dry(self):
        from app.application.services.investigation_learning import classify_humidity_band
        assert classify_humidity_band(20.0) == "DRY"

    def test_classify_humidity_moderate(self):
        from app.application.services.investigation_learning import classify_humidity_band
        assert classify_humidity_band(55.0) == "MODERATE"

    def test_classify_humidity_humid(self):
        from app.application.services.investigation_learning import classify_humidity_band
        assert classify_humidity_band(85.0) == "HUMID"


# ═══════════════════════════════════════════════════════════════════
# 3. Distance Calculation Tests
# ═══════════════════════════════════════════════════════════════════


class TestDistanceCalculations:
    """Test similarity distance helpers."""

    def test_band_distance_same(self):
        from app.application.services.investigation_learning import _band_distance, PM25_BAND_ORDER
        assert _band_distance("UNHEALTHY", "UNHEALTHY", PM25_BAND_ORDER) == 0.0

    def test_band_distance_different(self):
        from app.application.services.investigation_learning import _band_distance, PM25_BAND_ORDER
        d = _band_distance("GOOD", "HAZARDOUS", PM25_BAND_ORDER)
        assert d == 1.0  # max distance

    def test_band_distance_unknown(self):
        from app.application.services.investigation_learning import _band_distance, PM25_BAND_ORDER
        assert _band_distance("UNKNOWN", "UNHEALTHY", PM25_BAND_ORDER) == 1.0

    def test_sector_distance_same(self):
        from app.application.services.investigation_learning import _sector_distance
        assert _sector_distance("E", "E") == 0.0

    def test_sector_distance_opposite(self):
        from app.application.services.investigation_learning import _sector_distance
        assert _sector_distance("E", "W") == 1.0

    def test_sector_distance_adjacent(self):
        from app.application.services.investigation_learning import _sector_distance
        d = _sector_distance("E", "NE")
        assert 0.0 < d < 0.5  # 45 degrees / 180 = 0.25

    def test_sector_distance_unknown(self):
        from app.application.services.investigation_learning import _sector_distance
        assert _sector_distance("UNKNOWN", "E") == 1.0

    def test_list_distance_identical(self):
        from app.application.services.investigation_learning import _list_distance
        assert _list_distance(["a", "b"], ["b", "a"]) == 0.0

    def test_list_distance_disjoint(self):
        from app.application.services.investigation_learning import _list_distance
        assert _list_distance(["a"], ["b"]) == 1.0

    def test_list_distance_partial(self):
        from app.application.services.investigation_learning import _list_distance
        d = _list_distance(["a", "b"], ["b", "c"])
        assert 0.0 < d < 1.0

    def test_list_distance_empty(self):
        from app.application.services.investigation_learning import _list_distance
        assert _list_distance([], []) == 0.0

    def test_exact_distance_same(self):
        from app.application.services.investigation_learning import _exact_distance
        assert _exact_distance("rising", "rising") == 0.0

    def test_exact_distance_different(self):
        from app.application.services.investigation_learning import _exact_distance
        assert _exact_distance("rising", "falling") == 1.0

    def test_exact_distance_unknown(self):
        from app.application.services.investigation_learning import _exact_distance
        assert _exact_distance("UNKNOWN", "rising") == 1.0


# ═══════════════════════════════════════════════════════════════════
# 4. Similarity Calculation Tests
# ═══════════════════════════════════════════════════════════════════


class TestSimilarityCalculation:
    """Test deterministic similarity scoring."""

    def test_identical_contexts(self):
        from app.application.services.investigation_learning import compute_similarity
        from app.modeling.serving.learning_schemas import InvestigationContextSnapshot
        ctx = InvestigationContextSnapshot(**_make_context())
        score, matching, differing = compute_similarity(ctx, ctx)
        assert score == 1.0
        assert len(matching) > 0
        assert len(differing) == 0

    def test_completely_different_contexts(self):
        from app.application.services.investigation_learning import compute_similarity
        from app.modeling.serving.learning_schemas import InvestigationContextSnapshot
        current = InvestigationContextSnapshot(**_make_context(
            pm25_severity_band="GOOD",
            wind_sector="W",
            trajectory="falling",
            episode_state="normal",
        ))
        historical = InvestigationContextSnapshot(**_make_context(
            pm25_severity_band="HAZARDOUS",
            wind_sector="E",
            trajectory="rising",
            episode_state="episode",
        ))
        score, matching, differing = compute_similarity(current, historical)
        assert score < 1.0
        assert len(differing) > 0

    def test_partial_match(self):
        from app.application.services.investigation_learning import compute_similarity
        from app.modeling.serving.learning_schemas import InvestigationContextSnapshot
        current = InvestigationContextSnapshot(**_make_context(
            pm25_severity_band="UNHEALTHY",
            wind_sector="E",
        ))
        historical = InvestigationContextSnapshot(**_make_context(
            pm25_severity_band="UNHEALTHY",
            wind_sector="NE",
        ))
        score, matching, differing = compute_similarity(current, historical)
        assert 0.5 < score < 1.0  # Should be close since PM25 matches
        assert any("wind" in m.lower() for m in differing)

    def test_score_range(self):
        from app.application.services.investigation_learning import compute_similarity
        from app.modeling.serving.learning_schemas import InvestigationContextSnapshot
        ctx = InvestigationContextSnapshot(**_make_context())
        score, _, _ = compute_similarity(ctx, ctx)
        assert 0.0 <= score <= 1.0


# ═══════════════════════════════════════════════════════════════════
# 5. Reliability Calculation Tests
# ═══════════════════════════════════════════════════════════════════


class TestReliabilityCalculation:
    """Test deterministic reliability scoring."""

    def test_all_useful(self):
        from app.application.services.investigation_learning import compute_reliability
        from app.modeling.serving.learning_schemas import ReliabilityClassification
        r = compute_reliability(useful=10, partially_useful=0, not_supported=0, inconclusive=0)
        assert r.score == 100.0
        assert r.classification == ReliabilityClassification.STRONG

    def test_all_not_supported(self):
        from app.application.services.investigation_learning import compute_reliability
        r = compute_reliability(useful=0, partially_useful=0, not_supported=10, inconclusive=0)
        assert r.score == 0.0

    def test_mixed_outcomes(self):
        from app.application.services.investigation_learning import compute_reliability
        r = compute_reliability(useful=6, partially_useful=2, not_supported=2, inconclusive=0)
        assert 50.0 < r.score < 80.0

    def test_insufficient_data(self):
        from app.application.services.investigation_learning import compute_reliability
        from app.modeling.serving.learning_schemas import ReliabilityClassification
        r = compute_reliability(useful=1, partially_useful=0, not_supported=0, inconclusive=0)
        assert r.classification == ReliabilityClassification.INSUFFICIENT
        assert r.score is None

    def test_limited_data(self):
        from app.application.services.investigation_learning import compute_reliability
        from app.modeling.serving.learning_schemas import ReliabilityClassification
        r = compute_reliability(useful=2, partially_useful=1, not_supported=0, inconclusive=0)
        assert r.classification == ReliabilityClassification.LIMITED
        assert r.score is not None

    def test_moderate_data(self):
        from app.application.services.investigation_learning import compute_reliability
        from app.modeling.serving.learning_schemas import ReliabilityClassification
        r = compute_reliability(useful=4, partially_useful=2, not_supported=0, inconclusive=0)
        assert r.classification == ReliabilityClassification.MODERATE

    def test_strong_data(self):
        from app.application.services.investigation_learning import compute_reliability
        from app.modeling.serving.learning_schemas import ReliabilityClassification
        r = compute_reliability(useful=8, partially_useful=2, not_supported=0, inconclusive=0)
        assert r.classification == ReliabilityClassification.STRONG

    def test_inconclusive_excluded(self):
        """INCONCLUSIVE outcomes should not count toward reliability score."""
        from app.application.services.investigation_learning import compute_reliability
        r_with = compute_reliability(useful=3, partially_useful=1, not_supported=1, inconclusive=5)
        r_without = compute_reliability(useful=3, partially_useful=1, not_supported=1, inconclusive=0)
        # Scores should be the same since inconclusive is excluded
        assert r_with.score == r_without.score
        assert r_with.total_evaluated == r_without.total_evaluated
        # But inconclusive_count differs
        assert r_with.inconclusive_count == 5
        assert r_without.inconclusive_count == 0

    def test_score_calculation_formula(self):
        """Verify the weighted scoring formula."""
        from app.application.services.investigation_learning import compute_reliability
        # 3 useful (1.0 each) + 1 partially (0.5) out of 5 total
        # Score = (3*1.0 + 1*0.5) / 5 * 100 = 70.0
        r = compute_reliability(useful=3, partially_useful=1, not_supported=1, inconclusive=0)
        assert r.score == 70.0


# ═══════════════════════════════════════════════════════════════════
# 6. Context Building Tests
# ═══════════════════════════════════════════════════════════════════


class TestContextBuilding:
    """Test evidence package → InvestigationContextSnapshot extraction."""

    def test_build_context_full_evidence(self):
        from app.application.services.investigation_learning import build_context_from_evidence
        evidence = {
            "event_detection": {
                "data": {
                    "current_pm25": 165.0,
                    "state": "episode",
                    "trajectory": "rising",
                }
            },
            "weather_context": {
                "variables": [
                    {"name": "temperature", "value": 14.0},
                    {"name": "humidity", "value": 68.0},
                    {"name": "wind_speed", "value": 3.2},
                ]
            },
            "directional_analysis": {
                "current_wind": {"sector": "E"}
            },
            "investigation_domains": [
                {"id": "open-burning", "conditions_met": True},
                {"id": "traffic-emissions", "conditions_met": True},
                {"id": "road-dust", "conditions_met": False},
            ],
            "geographic_context": {
                "suggested_search_corridor": {"label": "East Corridor"}
            },
        }
        ctx = build_context_from_evidence(evidence)
        assert ctx.pm25_value == 165.0
        assert ctx.pm25_severity_band == "VERY_UNHEALTHY"
        assert ctx.wind_sector == "E"
        assert ctx.temperature_band == "COOL"
        assert ctx.humidity_band == "MODERATE"
        assert ctx.wind_speed_band == "LIGHT"
        assert ctx.investigation_corridor == "East Corridor"
        assert "open-burning" in ctx.eligible_domains
        assert "traffic-emissions" in ctx.eligible_domains
        assert "road-dust" not in ctx.eligible_domains
        assert ctx.trajectory == "rising"
        assert ctx.episode_state == "episode"

    def test_build_context_empty_evidence(self):
        from app.application.services.investigation_learning import build_context_from_evidence
        ctx = build_context_from_evidence({})
        assert ctx.pm25_severity_band == "UNKNOWN"
        assert ctx.wind_sector == "UNKNOWN"
        assert ctx.eligible_domains == []


# ═══════════════════════════════════════════════════════════════════
# 7. Full Learning Analytics Tests (with real DB)
# ═══════════════════════════════════════════════════════════════════


class TestInvestigationLearningAnalytics:
    """Integration tests for compute_investigation_learning with real DB."""

    def test_no_outcomes_returns_insufficient(self, tmp_path):
        """Empty database → INSUFFICIENT with zero findings."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        evidence = {
            "event_detection": {"data": {"current_pm25": 100.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {"variables": [{"name": "wind_speed", "value": 3.0}]},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.historical_investigations_found == 0
        assert result.evidence_status.value == "INSUFFICIENT"
        assert len(result.limitations) > 0

    def test_outcomes_without_context_returns_insufficient(self, tmp_path):
        """Outcomes without investigation_context → INSUFFICIENT."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        for i in range(5):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                recommendation_verification="SUPPORTED",
                # No investigation_context
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 100.0, "state": "episode", "trajectory": "rising"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.historical_investigations_found == 0

    def test_outcomes_with_context_produces_matches(self, tmp_path):
        """Outcomes with matching context → similar cases found."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(5):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                recommendation_verification="SUPPORTED",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {
                "variables": [
                    {"name": "temperature", "value": 14.0},
                    {"name": "humidity", "value": 68.0},
                    {"name": "wind_speed", "value": 3.2},
                ]
            },
            "directional_analysis": {"current_wind": {"sector": "E"}},
            "investigation_domains": [
                {"id": "open-burning", "conditions_met": True},
                {"id": "traffic-emissions", "conditions_met": True},
            ],
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.historical_investigations_found >= 5
        assert result.evidence_status.value in ("LIMITED", "MODERATE", "STRONG")
        assert result.recommendation_reliability.score is not None
        assert result.recommendation_reliability.useful_count == 5

    def test_mixed_outcomes_affect_reliability(self, tmp_path):
        """Mixed outcomes produce lower reliability score."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        statuses = ["USEFUL", "USEFUL", "PARTIALLY_USEFUL", "NOT_SUPPORTED", "USEFUL"]
        for i, status in enumerate(statuses):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status=status,
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {
                "variables": [
                    {"name": "temperature", "value": 14.0},
                    {"name": "humidity", "value": 68.0},
                    {"name": "wind_speed", "value": 3.2},
                ]
            },
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.recommendation_reliability.useful_count == 3
        assert result.recommendation_reliability.partially_useful_count == 1
        assert result.recommendation_reliability.not_supported_count == 1
        # Score = (3*1.0 + 1*0.5) / 5 * 100 = 70.0
        assert result.recommendation_reliability.score == 70.0

    def test_top_cases_limited_to_max(self, tmp_path):
        """Similar cases list is capped at MAX_SIMILAR_CASES."""
        from app.application.services.investigation_learning import compute_investigation_learning
        from app.modeling.serving.learning_schemas import MAX_SIMILAR_CASES
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(15):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {
                "variables": [
                    {"name": "temperature", "value": 14.0},
                    {"name": "wind_speed", "value": 3.2},
                ]
            },
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert len(result.similar_cases) <= MAX_SIMILAR_CASES
        # But total count includes all
        assert result.historical_investigations_found == 15

    def test_framing_not_ai_learned(self, tmp_path):
        """Verify framing does NOT say 'AI learned'."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(5):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {
                "variables": [{"name": "temperature", "value": 14.0}, {"name": "wind_speed", "value": 3.0}]
            },
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        # Should NEVER say "AI learned"
        assert "learned" not in result.historical_context_message.lower()
        assert "ai" not in result.historical_context_message.lower()
        # Should say "verified" or similar
        assert len(result.historical_context_message) > 0

    def test_response_always_has_limitations(self, tmp_path):
        """Every response includes limitations list."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        evidence = {
            "event_detection": {"data": {"current_pm25": 100.0, "state": "episode", "trajectory": "rising"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert isinstance(result.limitations, list)
        assert len(result.limitations) > 0

    def test_disclaimer_always_present(self, tmp_path):
        """Response always includes disclaimer text."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        evidence = {
            "event_detection": {"data": {"current_pm25": 100.0, "state": "episode", "trajectory": "rising"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.disclaimer is not None
        assert len(result.disclaimer) > 0

    def test_pending_outcomes_excluded(self, tmp_path):
        """PENDING outcomes should not be included in learning."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        # Only PENDING outcomes
        for i in range(5):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="PENDING",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.historical_investigations_found == 0

    def test_inconclusive_outcomes_counted_separately(self, tmp_path):
        """INCONCLUSIVE outcomes are tracked but excluded from reliability score."""
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(3):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        for i in range(3, 5):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="INCONCLUSIVE",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {
                "variables": [{"name": "temperature", "value": 14.0}, {"name": "wind_speed", "value": 3.0}]
            },
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.historical_investigations_found == 5
        # Score based on 3 useful + 0 partial + 0 not_supported = 3 evaluated
        assert result.recommendation_reliability.useful_count == 3
        assert result.recommendation_reliability.inconclusive_count == 2
        assert result.recommendation_reliability.total_evaluated == 3
        assert result.recommendation_reliability.score == 100.0


# ═══════════════════════════════════════════════════════════════════
# 8. API Endpoint Tests
# ═══════════════════════════════════════════════════════════════════


class TestLearningEndpoint:
    """Test the /api/v1/investigation/learning endpoint."""

    def test_demo_endpoint_returns_valid_response(self):
        """Demo mode returns deterministic fixture."""
        from app.api.v1.investigation import _get_demo_investigation_learning
        result = _get_demo_investigation_learning()
        assert result["historical_investigations_found"] == 12
        assert result["verified_outcomes"]["useful"] == 8
        assert result["recommendation_reliability"]["score"] == 0.79
        assert result["evidence_status"] == "MODERATE"
        assert len(result["similar_cases"]) == 12
        assert len(result["limitations"]) > 0
        assert len(result["disclaimer"]) > 0

    def test_demo_fixture_has_matching_framing(self):
        """Demo fixture uses correct accountability framing."""
        from app.api.v1.investigation import _get_demo_investigation_learning
        result = _get_demo_investigation_learning()
        msg = result["historical_context_message"]
        # Should reference "previously verified" or "verified"
        assert "verified" in msg.lower() or "similar" in msg.lower()
        # Should NOT say "AI learned"
        assert "ai learned" not in msg.lower()

    def test_demo_fixture_reliability_range(self):
        """Demo reliability score is between 0 and 100."""
        from app.api.v1.investigation import _get_demo_investigation_learning
        result = _get_demo_investigation_learning()
        score = result["recommendation_reliability"]["score"]
        assert 0.0 <= score <= 1.0

    def test_demo_fixture_all_similar_cases_have_required_fields(self):
        """Each similar case has required fields."""
        from app.api.v1.investigation import _get_demo_investigation_learning
        result = _get_demo_investigation_learning()
        for case in result["similar_cases"]:
            assert "investigation_id" in case
            assert "outcome_id" in case
            assert "similarity_score" in case
            assert 0.0 <= case["similarity_score"] <= 1.0
            assert "overall_status" in case
            assert "matching_dimensions" in case
            assert "differing_dimensions" in case


# ═══════════════════════════════════════════════════════════════════
# 9. Verification Schema Integration Tests
# ═══════════════════════════════════════════════════════════════════


class TestVerificationSchemaIntegration:
    """Test that verification schemas support investigation_context."""

    def test_create_request_with_context(self):
        from app.modeling.serving.verification_schemas import VerificationCreateRequest
        ctx = _make_context()
        req = VerificationCreateRequest(
            investigation_id="inv-001",
            overall_status="USEFUL",
            investigation_context=ctx,
        )
        assert req.investigation_context is not None
        assert req.investigation_context["pm25_value"] == 165.0

    def test_create_request_without_context(self):
        from app.modeling.serving.verification_schemas import VerificationCreateRequest
        req = VerificationCreateRequest(
            investigation_id="inv-002",
            overall_status="USEFUL",
        )
        assert req.investigation_context is None

    def test_outcome_response_with_context(self):
        from app.modeling.serving.verification_schemas import VerificationOutcomeResponse
        ctx = _make_context()
        resp = VerificationOutcomeResponse(
            outcome_id="VER-001",
            investigation_id="INV-001",
            overall_status="USEFUL",
            created_at="2024-11-01T10:00:00",
            updated_at="2024-11-01T10:00:00",
            investigation_context=ctx,
        )
        assert resp.investigation_context is not None
        assert resp.investigation_context["wind_sector"] == "E"

    def test_outcome_response_without_context(self):
        from app.modeling.serving.verification_schemas import VerificationOutcomeResponse
        resp = VerificationOutcomeResponse(
            outcome_id="VER-002",
            investigation_id="INV-002",
            overall_status="PENDING",
            created_at="2024-11-01T10:00:00",
            updated_at="2024-11-01T10:00:00",
        )
        assert resp.investigation_context is None


# ═══════════════════════════════════════════════════════════════════
# 10. Minimum Threshold Tests
# ═══════════════════════════════════════════════════════════════════


class TestMinimumThresholds:
    """Test evidence_status classification based on sample size."""

    def test_insufficient_below_3(self, tmp_path):
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(2):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {"variables": [{"name": "temperature", "value": 14.0}]},
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.evidence_status.value == "INSUFFICIENT"

    def test_limited_at_3(self, tmp_path):
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(3):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {"variables": [{"name": "temperature", "value": 14.0}]},
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.evidence_status.value == "LIMITED"

    def test_moderate_at_6(self, tmp_path):
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(6):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {"variables": [{"name": "temperature", "value": 14.0}]},
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.evidence_status.value == "MODERATE"

    def test_strong_at_10(self, tmp_path):
        from app.application.services.investigation_learning import compute_investigation_learning
        db_path = _create_test_db(tmp_path)
        ctx = _make_context()
        for i in range(10):
            _insert_outcome(
                db_path,
                outcome_id=f"VER-{i}",
                investigation_id=f"INV-{i}",
                overall_status="USEFUL",
                investigation_context=ctx,
            )
        evidence = {
            "event_detection": {"data": {"current_pm25": 165.0, "state": "episode", "trajectory": "rising"}},
            "weather_context": {"variables": [{"name": "temperature", "value": 14.0}]},
            "directional_analysis": {"current_wind": {"sector": "E"}},
        }
        result = compute_investigation_learning(db_path, evidence)
        assert result.evidence_status.value == "STRONG"
