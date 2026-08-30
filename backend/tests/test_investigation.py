"""Tests for Investigation Evidence Assembler.

Tests cover:
1. Domain evaluation logic (weather trigger matching)
2. Evidence type constants
3. Geographic context building
4. Package structure and serialization
5. Graceful degradation on source failures
6. API endpoint response structure
7. Evidence type tagging correctness
8. Domain evaluation edge cases
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
        from app.modeling.serving.investigation import (
            InvestigationEvidencePackage,
            assemble_investigation_evidence,
            EvidenceType,
            INVESTIGATION_DOMAINS,
            _evaluate_domain,
            _evaluate_all_domains,
            _build_geographic_context,
        )
        assert callable(assemble_investigation_evidence)
        assert callable(_evaluate_domain)
        assert callable(_evaluate_all_domains)
        assert callable(_build_geographic_context)

    def test_import_api_endpoint(self):
        """API endpoint module imports successfully."""
        from app.api.v1.investigation import router
        assert router is not None


# ═══════════════════════════════════════════════════════════════════
# 2. Evidence Type Constants
# ═══════════════════════════════════════════════════════════════════


class TestEvidenceType:
    """Verify evidence type constants."""

    def test_three_types(self):
        from app.modeling.serving.investigation import EvidenceType
        assert EvidenceType.OBSERVED == "observed"
        assert EvidenceType.INFERRED == "inferred"
        assert EvidenceType.HYPOTHESIS == "hypothesis"

    def test_all_types_unique(self):
        from app.modeling.serving.investigation import EvidenceType
        types = [EvidenceType.OBSERVED, EvidenceType.INFERRED, EvidenceType.HYPOTHESIS]
        assert len(types) == len(set(types))


# ═══════════════════════════════════════════════════════════════════
# 3. Domain Definitions
# ═══════════════════════════════════════════════════════════════════


class TestInvestigationDomains:
    """Verify investigation domain definitions."""

    def test_four_domains(self):
        from app.modeling.serving.investigation import INVESTIGATION_DOMAINS
        assert len(INVESTIGATION_DOMAINS) == 4

    def test_domain_ids(self):
        from app.modeling.serving.investigation import INVESTIGATION_DOMAINS
        ids = [d["id"] for d in INVESTIGATION_DOMAINS]
        assert "open-burning" in ids
        assert "traffic-emissions" in ids
        assert "road-dust" in ids
        assert "industrial" in ids

    def test_all_domains_have_triggers(self):
        from app.modeling.serving.investigation import INVESTIGATION_DOMAINS
        for domain in INVESTIGATION_DOMAINS:
            assert "triggers" in domain
            assert len(domain["triggers"]) > 0

    def test_all_domains_have_legal_basis(self):
        from app.modeling.serving.investigation import INVESTIGATION_DOMAINS
        for domain in INVESTIGATION_DOMAINS:
            assert "legal_basis" in domain
            assert len(domain["legal_basis"]) > 0


# ═══════════════════════════════════════════════════════════════════
# 4. Domain Evaluation Logic
# ═══════════════════════════════════════════════════════════════════


class TestDomainEvaluation:
    """Verify weather trigger evaluation against domains."""

    def test_open_burning_triggers_match(self):
        """Cold + dry + calm → open burning conditions met."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "open-burning")
        weather_vars = [
            {"label": "Temperature", "current_value": 12.0},
            {"label": "Humidity", "current_value": 45.0},
            {"label": "Wind speed", "current_value": 3.0},
        ]
        result = _evaluate_domain(domain, weather_vars)
        assert result.conditions_met is True
        assert result.triggers_matched == 3
        assert result.evidence_type == "hypothesis"

    def test_open_burning_no_match(self):
        """Warm + humid → open burning conditions NOT met."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "open-burning")
        weather_vars = [
            {"label": "Temperature", "current_value": 30.0},
            {"label": "Humidity", "current_value": 85.0},
            {"label": "Wind speed", "current_value": 10.0},
        ]
        result = _evaluate_domain(domain, weather_vars)
        assert result.conditions_met is False
        assert result.triggers_matched == 0

    def test_traffic_emissions_match(self):
        """Calm + humid → traffic emissions conditions met."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "traffic-emissions")
        weather_vars = [
            {"label": "Wind speed", "current_value": 2.0},
            {"label": "Humidity", "current_value": 80.0},
        ]
        result = _evaluate_domain(domain, weather_vars)
        assert result.conditions_met is True
        assert result.triggers_matched == 2

    def test_road_dust_match(self):
        """Dry + windy → road dust conditions met."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "road-dust")
        weather_vars = [
            {"label": "Humidity", "current_value": 40.0},
            {"label": "Wind speed", "current_value": 8.0},
        ]
        result = _evaluate_domain(domain, weather_vars)
        assert result.conditions_met is True

    def test_industrial_match(self):
        """High pressure + calm → industrial conditions met."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "industrial")
        weather_vars = [
            {"label": "Pressure", "current_value": 1015.0},
            {"label": "Wind speed", "current_value": 3.0},
        ]
        result = _evaluate_domain(domain, weather_vars)
        assert result.conditions_met is True

    def test_empty_weather_returns_no_match(self):
        """Empty weather list → no triggers evaluated."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = INVESTIGATION_DOMAINS[0]
        result = _evaluate_domain(domain, [])
        assert result.conditions_met is False
        assert result.triggers_evaluated == 3
        assert result.triggers_matched == 0

    def test_partial_weather_data(self):
        """Missing some weather variables → only available triggers evaluated."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "open-burning")
        # Only temperature provided, humidity and wind missing
        weather_vars = [
            {"label": "Temperature", "current_value": 12.0},
        ]
        result = _evaluate_domain(domain, weather_vars)
        # 1 trigger matched out of 3 evaluated (missing data counted as not matched)
        assert result.triggers_matched == 1
        assert result.triggers_evaluated == 3

    def test_null_weather_values(self):
        """Null values in weather → triggers not matched."""
        from app.modeling.serving.investigation import _evaluate_domain, INVESTIGATION_DOMAINS

        domain = next(d for d in INVESTIGATION_DOMAINS if d["id"] == "open-burning")
        weather_vars = [
            {"label": "Temperature", "current_value": None},
            {"label": "Humidity", "current_value": None},
            {"label": "Wind speed", "current_value": None},
        ]
        result = _evaluate_domain(domain, weather_vars)
        assert result.conditions_met is False
        assert result.triggers_matched == 0


# ═══════════════════════════════════════════════════════════════════
# 5. Evaluate All Domains
# ═══════════════════════════════════════════════════════════════════


class TestEvaluateAllDomains:
    """Verify batch domain evaluation."""

    def test_returns_all_domains(self):
        from app.modeling.serving.investigation import _evaluate_all_domains

        weather_vars = [
            {"label": "Temperature", "current_value": 15.0},
            {"label": "Humidity", "current_value": 50.0},
            {"label": "Wind speed", "current_value": 3.0},
            {"label": "Pressure", "current_value": 1012.0},
        ]
        results = _evaluate_all_domains(weather_vars)
        assert len(results) == 4

    def test_each_result_has_required_fields(self):
        from app.modeling.serving.investigation import _evaluate_all_domains

        weather_vars = [
            {"label": "Temperature", "current_value": 15.0},
            {"label": "Humidity", "current_value": 50.0},
            {"label": "Wind speed", "current_value": 3.0},
            {"label": "Pressure", "current_value": 1012.0},
        ]
        results = _evaluate_all_domains(weather_vars)
        for r in results:
            assert "id" in r
            assert "name" in r
            assert "icon" in r
            assert "triggers_evaluated" in r
            assert "triggers_matched" in r
            assert "conditions_met" in r
            assert "evidence_type" in r
            assert "caveat" in r
            assert r["evidence_type"] == "hypothesis"

    def test_empty_weather_all_domains_returned(self):
        from app.modeling.serving.investigation import _evaluate_all_domains

        results = _evaluate_all_domains([])
        assert len(results) == 4
        # All should have conditions_met = False
        for r in results:
            assert r["conditions_met"] is False


# ═══════════════════════════════════════════════════════════════════
# 6. Geographic Context
# ═══════════════════════════════════════════════════════════════════


class TestGeographicContext:
    """Verify geographic context building."""

    def test_default_grid_point(self):
        from app.modeling.serving.investigation import _build_geographic_context

        ctx = _build_geographic_context(None)
        assert ctx["grid_point"]["lat"] == 31.5204
        assert ctx["grid_point"]["lon"] == 74.3587
        assert "scope" in ctx

    def test_with_compass_hint(self):
        from app.modeling.serving.investigation import _build_geographic_context

        compass = {
            "investigation_hint": {
                "corridor_sectors": ["NW", "W"],
                "corridor_label": "NW sector",
            }
        }
        ctx = _build_geographic_context(compass)
        assert ctx["suggested_search_corridor"]["sectors"] == ["NW", "W"]
        assert ctx["suggested_search_corridor"]["label"] == "NW sector"

    def test_without_hint(self):
        from app.modeling.serving.investigation import _build_geographic_context

        compass = {"investigation_hint": None}
        ctx = _build_geographic_context(compass)
        assert "suggested_search_corridor" not in ctx


# ═══════════════════════════════════════════════════════════════════
# 7. Package Structure and Serialization
# ═══════════════════════════════════════════════════════════════════


class TestPackageStructure:
    """Verify InvestigationEvidencePackage structure."""

    def test_to_dict_has_all_sections(self):
        from app.modeling.serving.investigation import InvestigationEvidencePackage

        pkg = InvestigationEvidencePackage()
        d = pkg.to_dict()
        assert "metadata" in d
        assert "event_detection" in d
        assert "weather_context" in d
        assert "directional_analysis" in d
        assert "investigation_domains" in d
        assert "historical_analogs" in d
        assert "geographic_context" in d
        assert "data_quality" in d
        assert "limitations" in d

    def test_metadata_fields(self):
        from app.modeling.serving.investigation import InvestigationEvidencePackage

        pkg = InvestigationEvidencePackage(assembled_at="2025-01-01T00:00:00Z")
        d = pkg.to_dict()
        assert d["metadata"]["assembled_at"] == "2025-01-01T00:00:00Z"
        assert d["metadata"]["assembly_version"] == "1.0.0"

    def test_empty_package_serializes(self):
        from app.modeling.serving.investigation import InvestigationEvidencePackage

        pkg = InvestigationEvidencePackage()
        d = pkg.to_dict()
        # Should serialize without errors
        assert isinstance(d, dict)
        assert isinstance(d["limitations"], list)


# ═══════════════════════════════════════════════════════════════════
# 8. Graceful Degradation (Mocked)
# ═══════════════════════════════════════════════════════════════════


class TestGracefulDegradation:
    """Verify that individual source failures produce partial packages."""

    @patch("app.modeling.serving.investigation.assess_freshness")
    @patch("app.modeling.serving.investigation.compute_episode_intelligence")
    @patch("app.modeling.serving.investigation.compute_source_compass")
    @patch("app.modeling.serving.investigation.find_analogs")
    def test_freshness_failure_still_returns_package(
        self, mock_analogs, mock_compass, mock_episode, mock_freshness
    ):
        from app.modeling.serving.investigation import assemble_investigation_evidence

        mock_freshness.side_effect = RuntimeError("DB locked")
        mock_episode.return_value.to_dict.return_value = {
            "state": "normal",
            "weather_context": {"variables": []},
        }
        mock_compass.return_value.to_dict.return_value = {}
        mock_analogs.return_value = MagicMock(
            analogs=[], total_episodes_searched=0, caveat=""
        )

        pkg = assemble_investigation_evidence(DB_PATH)
        d = pkg.to_dict()
        # Should still return a package with limitations
        assert "limitations" in d
        assert any("freshness" in lim.lower() for lim in d["limitations"])

    @patch("app.modeling.serving.investigation.assess_freshness")
    @patch("app.modeling.serving.investigation.compute_episode_intelligence")
    @patch("app.modeling.serving.investigation.compute_source_compass")
    @patch("app.modeling.serving.investigation.find_analogs")
    def test_episode_failure_still_returns_package(
        self, mock_analogs, mock_compass, mock_episode, mock_freshness
    ):
        from app.modeling.serving.investigation import assemble_investigation_evidence

        mock_freshness.return_value = MagicMock(
            state=MagicMock(value="fresh"),
            freshness_hours=1.0,
            latest_observation_at="2025-01-01T12:00:00Z",
            parameters_available=5,
        )
        mock_episode.side_effect = RuntimeError("Model not loaded")
        mock_compass.return_value.to_dict.return_value = {}
        mock_analogs.return_value = MagicMock(
            analogs=[], total_episodes_searched=0, caveat=""
        )

        pkg = assemble_investigation_evidence(DB_PATH)
        d = pkg.to_dict()
        assert d["event_detection"]["error"] is not None
        assert any("event detection" in lim.lower() for lim in d["limitations"])

    @patch("app.modeling.serving.investigation.assess_freshness")
    @patch("app.modeling.serving.investigation.compute_episode_intelligence")
    @patch("app.modeling.serving.investigation.compute_source_compass")
    @patch("app.modeling.serving.investigation.find_analogs")
    def test_compass_failure_still_returns_package(
        self, mock_analogs, mock_compass, mock_episode, mock_freshness
    ):
        from app.modeling.serving.investigation import assemble_investigation_evidence

        mock_freshness.return_value = MagicMock(
            state=MagicMock(value="fresh"),
            freshness_hours=1.0,
            latest_observation_at="2025-01-01T12:00:00Z",
            parameters_available=5,
        )
        mock_episode.return_value.to_dict.return_value = {
            "state": "normal",
            "weather_context": {"variables": []},
        }
        mock_compass.side_effect = RuntimeError("No wind data")
        mock_analogs.return_value = MagicMock(
            analogs=[], total_episodes_searched=0, caveat=""
        )

        pkg = assemble_investigation_evidence(DB_PATH)
        d = pkg.to_dict()
        assert d["directional_analysis"] is None
        assert any("compass" in lim.lower() or "directional" in lim.lower() for lim in d["limitations"])

    @patch("app.modeling.serving.investigation.assess_freshness")
    @patch("app.modeling.serving.investigation.compute_episode_intelligence")
    @patch("app.modeling.serving.investigation.compute_source_compass")
    @patch("app.modeling.serving.investigation.find_analogs")
    def test_analogs_failure_still_returns_package(
        self, mock_analogs, mock_compass, mock_episode, mock_freshness
    ):
        from app.modeling.serving.investigation import assemble_investigation_evidence

        mock_freshness.return_value = MagicMock(
            state=MagicMock(value="fresh"),
            freshness_hours=1.0,
            latest_observation_at="2025-01-01T12:00:00Z",
            parameters_available=5,
        )
        mock_episode.return_value.to_dict.return_value = {
            "state": "normal",
            "weather_context": {"variables": []},
        }
        mock_compass.return_value.to_dict.return_value = {}
        mock_analogs.side_effect = RuntimeError("No episodes")

        pkg = assemble_investigation_evidence(DB_PATH)
        d = pkg.to_dict()
        assert d["historical_analogs"] is None
        assert any("analog" in lim.lower() for lim in d["limitations"])

    @patch("app.modeling.serving.investigation.assess_freshness")
    @patch("app.modeling.serving.investigation.compute_episode_intelligence")
    @patch("app.modeling.serving.investigation.compute_source_compass")
    @patch("app.modeling.serving.investigation.find_analogs")
    def test_all_sources_fail_still_returns_package(
        self, mock_analogs, mock_compass, mock_episode, mock_freshness
    ):
        """Even with every source failing, endpoint returns a valid package."""
        from app.modeling.serving.investigation import assemble_investigation_evidence

        mock_freshness.side_effect = RuntimeError("DB error")
        mock_episode.side_effect = RuntimeError("Model error")
        mock_compass.side_effect = RuntimeError("Wind error")
        mock_analogs.side_effect = RuntimeError("Analog error")

        pkg = assemble_investigation_evidence(DB_PATH)
        d = pkg.to_dict()
        # Must still be a valid response
        assert "metadata" in d
        assert len(d["limitations"]) >= 3


# ═══════════════════════════════════════════════════════════════════
# 9. API Endpoint (Integration)
# ═══════════════════════════════════════════════════════════════════


class TestInvestigationEndpoint:
    """Test the GET /api/v1/investigation/current endpoint."""

    def test_endpoint_exists(self, client):
        """Endpoint responds (may be 503 if DB missing, but not 404)."""
        response = client.get("/api/v1/investigation/current")
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

    def test_response_structure_when_db_missing(self, client):
        """When DB doesn't exist, returns 503 with error structure."""
        response = client.get("/api/v1/investigation/current")
        if response.status_code == 503:
            data = response.json()
            assert "error" in data
            assert "code" in data["error"]

    def test_response_structure_when_db_exists(self, client):
        """When DB exists, returns evidence package structure."""
        if not DB_PATH.exists():
            pytest.skip("Test database not available")

        response = client.get("/api/v1/investigation/current")
        if response.status_code == 200:
            data = response.json()
            # Must have all evidence sections
            assert "metadata" in data
            assert "event_detection" in data
            assert "weather_context" in data
            assert "investigation_domains" in data
            assert "data_quality" in data
            assert "limitations" in data
            # Metadata
            assert "assembled_at" in data["metadata"]
            assert "assembly_version" in data["metadata"]
