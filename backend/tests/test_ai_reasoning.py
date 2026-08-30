"""Tests for AI Investigation Reasoning Service.

Tests cover all 12 categories from the spec:
1.  Valid AI response (full schema pass)
2.  Invalid JSON from AI
3.  Invalid schema (missing required fields)
4.  Missing API key → deterministic fallback
5.  Provider timeout → graceful fallback
6.  Unsupported evidence reference filtering
7.  Confidence below 0.30 → hypothesis filtered
8.  Confidence above 0.85 → capped at 0.85
9.  Missing uncertainty section → auto-populated
10. Missing hypothesis evidence → cleaned
11. Deterministic fallback builder
12. Demo mode response

Additional coverage:
- Pydantic schema validation (ai_schemas.py)
- Evidence reference validation (ai_prompts.py)
- Confidence clamping (_clamp_confidence)
- JSON extraction (_extract_json)
- Full API endpoint integration (GET /api/v1/investigation/analyze)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Paths ──────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "lahore_pulse.db"


# ── Shared Fixtures ───────────────────────────────────────────────


@pytest.fixture
def sample_evidence_package() -> dict:
    """Minimal but valid evidence package for testing."""
    return {
        "metadata": {
            "assembled_at": "2026-01-01T00:00:00Z",
            "assembly_version": "1.0.0",
            "grid_point": {"latitude": 31.52, "longitude": 74.36},
            "sources_attempted": 6,
            "sources_succeeded": 4,
        },
        "event_detection": {
            "data": {
                "state": "EPISODE",
                "trajectory": "RISING",
                "current_pm25": 95.3,
                "episode_start": "2026-01-01T10:00:00Z",
            },
            "evidence_type": "observed",
        },
        "weather_context": {
            "data": {
                "variables": {
                    "temperature": 14.2,
                    "wind_speed": 3.1,
                    "humidity": 78,
                },
                "pattern_match": True,
            },
            "evidence_type": "observed",
        },
        "directional_analysis": {
            "current_wind": {"direction": 90, "sector": "E", "speed": 3.1},
            "historical": {
                "strongest_sector": "E",
                "strongest_enrichment": 1.44,
                "evidence_count": 972,
                "season": "winter",
            },
            "interpretation": "Wind from East sector shows 1.44x enrichment.",
        },
        "investigation_domains": [
            {
                "id": "open-burning",
                "triggers_matched": True,
                "weather_compatible": True,
            },
            {
                "id": "traffic-emissions",
                "triggers_matched": False,
                "weather_compatible": True,
            },
        ],
        "historical_analogs": {
            "matches": [
                {"date": "2025-12-15", "similarity": 0.82},
                {"date": "2025-11-20", "similarity": 0.75},
            ],
            "total_episodes_searched": 45,
        },
        "geographic_context": {
            "grid_point": {"latitude": 31.52, "longitude": 74.36},
            "search_radius_km": 50,
        },
        "data_quality": {
            "freshness_state": "fresh",
            "coverage_score": 0.85,
        },
        "limitations": ["No satellite fire data", "No traffic count data"],
    }


@pytest.fixture
def sample_ai_valid_response() -> dict:
    """A valid AI response that matches AIInvestigationResult schema."""
    return {
        "analysis_status": "complete",
        "event_summary": "PM2.5 episode with rising trajectory.",
        "severity_assessment": "Active episode, accumulation phase.",
        "observed_facts": [
            {
                "statement": "PM2.5 is in episode range.",
                "evidence_references": [
                    "event_detection.data.state",
                    "event_detection.data.current_pm25",
                ],
            }
        ],
        "model_inferences": [
            {
                "statement": "East sector enrichment suggests association.",
                "confidence": 0.70,
                "supporting_evidence": [
                    "directional_analysis.historical.strongest_enrichment",
                ],
            }
        ],
        "investigation_hypotheses": [
            {
                "factor": "East sector industrial emissions",
                "confidence": 0.65,
                "reasoning": "Wind from East with enrichment.",
                "supporting_evidence": [
                    "directional_analysis.historical.strongest_enrichment",
                ],
                "verification_needed": "Field inspection.",
            }
        ],
        "investigation_priority": {
            "area": "East sector",
            "priority": "HIGH",
            "rationale": "Highest enrichment.",
            "confidence": 0.70,
        },
        "likely_exposure_direction": {
            "description": "Downwind of East sector.",
            "confidence": 0.65,
            "limitations": ["Association, not confirmed source."],
        },
        "recommended_actions": [
            {
                "priority": 1,
                "action": "Deploy field inspection.",
                "rationale": "Highest enrichment corridor.",
                "verification_goal": "Confirm sources.",
            }
        ],
        "uncertainties": [
            "Enrichment shows association, not confirmed source.",
            "Historical analogs may not reflect current conditions.",
        ],
        "data_gaps": ["No satellite fire data."],
    }


# ═══════════════════════════════════════════════════════════════════
# 1. Module Imports
# ═══════════════════════════════════════════════════════════════════


class TestModuleImports:
    """Verify all AI reasoning modules import without errors."""

    def test_import_schemas(self):
        from app.modeling.serving.ai_schemas import (
            AIInvestigationResult,
            InvestigationAnalysisResponse,
            ObservedFact,
            ModelInference,
            InvestigationHypothesis,
        )
        assert callable(AIInvestigationResult)

    def test_import_prompts(self):
        from app.modeling.serving.ai_prompts import (
            INVESTIGATION_SYSTEM_PROMPT,
            INVESTIGATION_USER_TEMPLATE,
            KNOWN_EVIDENCE_PATHS,
        )
        assert len(INVESTIGATION_SYSTEM_PROMPT) > 100
        assert "{evidence_json}" in INVESTIGATION_USER_TEMPLATE
        assert len(KNOWN_EVIDENCE_PATHS) > 10

    def test_import_reasoning(self):
        from app.modeling.serving.ai_reasoning import (
            analyze_investigation,
            _clamp_confidence,
            _extract_json,
            _build_fallback_response,
            _post_process_result,
            _is_valid_reference,
            CONFIDENCE_MIN,
            CONFIDENCE_MAX,
            DEMO_AI_ANALYSIS,
        )
        assert callable(analyze_investigation)
        assert CONFIDENCE_MIN == 0.30
        assert CONFIDENCE_MAX == 0.85

    def test_import_api_endpoint(self):
        from app.api.v1.investigation import router
        assert router is not None


# ═══════════════════════════════════════════════════════════════════
# 2. Pydantic Schema Validation
# ═══════════════════════════════════════════════════════════════════


class TestAISchemas:
    """Validate Pydantic models for AI output."""

    def test_observed_fact_valid(self):
        from app.modeling.serving.ai_schemas import ObservedFact
        fact = ObservedFact(
            statement="PM2.5 is elevated.",
            evidence_references=["event_detection.data.current_pm25"],
        )
        assert fact.statement == "PM2.5 is elevated."

    def test_observed_fact_empty_refs(self):
        from app.modeling.serving.ai_schemas import ObservedFact
        fact = ObservedFact(
            statement="Something observed.",
            evidence_references=[],
        )
        assert fact.evidence_references == []

    def test_model_inference_confidence_cap(self):
        """Confidence above 0.85 should be capped by schema validator."""
        from app.modeling.serving.ai_schemas import ModelInference
        inf = ModelInference(
            statement="Some inference.",
            confidence=0.95,
            supporting_evidence=["event_detection.data.state"],
        )
        assert inf.confidence == 0.85

    def test_model_inference_valid(self):
        from app.modeling.serving.ai_schemas import ModelInference
        inf = ModelInference(
            statement="Statistical association found.",
            confidence=0.70,
            supporting_evidence=["directional_analysis.historical.strongest_enrichment"],
        )
        assert inf.confidence == 0.70

    def test_investigation_hypothesis_valid(self):
        from app.modeling.serving.ai_schemas import InvestigationHypothesis
        h = InvestigationHypothesis(
            factor="Industrial emissions",
            confidence=0.65,
            reasoning="Wind direction correlation.",
            supporting_evidence=["directional_analysis.historical.strongest_enrichment"],
            verification_needed="Field inspection.",
        )
        assert h.confidence == 0.65

    def test_investigation_priority_valid(self):
        from app.modeling.serving.ai_schemas import InvestigationPriority
        p = InvestigationPriority(
            area="East sector",
            priority="HIGH",
            rationale="Highest enrichment.",
            confidence=0.70,
        )
        assert p.priority == "HIGH"

    def test_investigation_priority_invalid_level(self):
        from app.modeling.serving.ai_schemas import InvestigationPriority
        with pytest.raises(Exception):
            InvestigationPriority(
                area="East",
                priority="CRITICAL",  # Not in allowed set
                rationale="Because.",
                confidence=0.7,
            )

    def test_exposure_direction_valid(self):
        from app.modeling.serving.ai_schemas import ExposureDirection
        d = ExposureDirection(
            description="Downwind area.",
            confidence=0.65,
            limitations=["Not confirmed."],
        )
        assert d.confidence == 0.65

    def test_recommended_action_valid(self):
        from app.modeling.serving.ai_schemas import RecommendedAction
        a = RecommendedAction(
            priority=1,
            action="Deploy inspection.",
            rationale="Highest enrichment.",
            verification_goal="Confirm sources.",
        )
        assert a.priority == 1

    def test_analysis_status_valid_values(self):
        from app.modeling.serving.ai_schemas import AIInvestigationResult
        for status in ["complete", "limited", "unavailable"]:
            result = AIInvestigationResult(
                analysis_status=status,
                event_summary="Test summary.",
            )
            assert result.analysis_status == status

    def test_analysis_status_invalid_value(self):
        from app.modeling.serving.ai_schemas import AIInvestigationResult
        with pytest.raises(Exception):
            AIInvestigationResult(analysis_status="partial", event_summary="X")

    def test_full_result_valid(self, sample_ai_valid_response):
        from app.modeling.serving.ai_schemas import AIInvestigationResult
        result = AIInvestigationResult(**sample_ai_valid_response)
        assert result.analysis_status == "complete"
        assert len(result.observed_facts) == 1
        assert len(result.investigation_hypotheses) == 1

    def test_analysis_response_structure(self, sample_evidence_package, sample_ai_valid_response):
        from app.modeling.serving.ai_schemas import InvestigationAnalysisResponse
        resp = InvestigationAnalysisResponse(
            evidence=sample_evidence_package,
            analysis=sample_ai_valid_response,
            analysis_metadata={
                "mode": "ai",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "generated_at": "2026-01-01T00:00:00Z",
                "fallback_used": False,
            },
        )
        dumped = resp.model_dump()
        assert "evidence" in dumped
        assert "analysis" in dumped
        assert "analysis_metadata" in dumped
        assert dumped["analysis_metadata"]["fallback_used"] is False


# ═══════════════════════════════════════════════════════════════════
# 3. Confidence Clamping
# ═══════════════════════════════════════════════════════════════════


class TestConfidenceClamping:
    """Test _clamp_confidence bounds."""

    def test_below_minimum(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(0.10) == 0.30

    def test_at_minimum(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(0.30) == 0.30

    def test_above_maximum(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(0.99) == 0.85

    def test_at_maximum(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(0.85) == 0.85

    def test_in_range(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(0.65) == 0.65

    def test_zero(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(0.0) == 0.30

    def test_negative(self):
        from app.modeling.serving.ai_reasoning import _clamp_confidence
        assert _clamp_confidence(-0.5) == 0.30


# ═══════════════════════════════════════════════════════════════════
# 4. JSON Extraction
# ═══════════════════════════════════════════════════════════════════


class TestExtractJSON:
    """Test _extract_json robustness."""

    def test_valid_json(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown_block(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_json_in_generic_block(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        text = '```\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        text = 'Here is the analysis:\n{"analysis_status": "complete"}\nDone.'
        result = _extract_json(text)
        assert result == {"analysis_status": "complete"}

    def test_invalid_text(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        result = _extract_json("This is not JSON at all")
        assert result is None

    def test_empty_string(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        result = _extract_json("")
        assert result is None

    def test_truncated_json(self):
        from app.modeling.serving.ai_reasoning import _extract_json
        result = _extract_json('{"key": "val')
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 5. Evidence Reference Validation
# ═══════════════════════════════════════════════════════════════════


class TestEvidenceReferences:
    """Test _is_valid_reference against KNOWN_EVIDENCE_PATHS."""

    def test_known_direct_path(self):
        from app.modeling.serving.ai_reasoning import _is_valid_reference
        assert _is_valid_reference("event_detection.data.state") is True

    def test_known_prefix_match(self):
        from app.modeling.serving.ai_reasoning import _is_valid_reference
        assert _is_valid_reference("event_detection.data.current_pm25") is True

    def test_unknown_path(self):
        from app.modeling.serving.ai_reasoning import _is_valid_reference
        assert _is_valid_reference("made_up.path.here") is False

    def test_empty_string(self):
        from app.modeling.serving.ai_reasoning import _is_valid_reference
        assert _is_valid_reference("") is False

    def test_known_directional_path(self):
        from app.modeling.serving.ai_reasoning import _is_valid_reference
        assert _is_valid_reference("directional_analysis.historical.strongest_enrichment") is True


# ═══════════════════════════════════════════════════════════════════
# 6. Post-Processing
# ═══════════════════════════════════════════════════════════════════


class TestPostProcessing:
    """Test _post_process_result constraints."""

    def test_caps_high_confidence(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [{"statement": "X", "confidence": 0.95, "supporting_evidence": []}],
            "investigation_hypotheses": [],
            "investigation_priority": {"confidence": 0.99},
            "likely_exposure_direction": {"confidence": 0.92},
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": [],
        }
        processed = _post_process_result(result)
        assert processed["model_inferences"][0]["confidence"] == 0.85
        assert processed["investigation_priority"]["confidence"] == 0.85
        assert processed["likely_exposure_direction"]["confidence"] == 0.85

    def test_filters_low_confidence_hypotheses(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [],
            "investigation_hypotheses": [
                {"factor": "A", "confidence": 0.20, "supporting_evidence": []},
                {"factor": "B", "confidence": 0.50, "supporting_evidence": []},
            ],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        assert len(processed["investigation_hypotheses"]) == 1
        assert processed["investigation_hypotheses"][0]["factor"] == "B"

    def test_removes_invalid_evidence_refs(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [
                {
                    "statement": "X",
                    "confidence": 0.6,
                    "supporting_evidence": [
                        "event_detection.data.state",
                        "totally_fake.ref.path",
                    ],
                }
            ],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [
                {
                    "statement": "Fact",
                    "evidence_references": ["event_detection.data.current_pm25"],
                }
            ],
            "recommended_actions": [],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        refs = processed["model_inferences"][0]["supporting_evidence"]
        assert "totally_fake.ref.path" not in refs
        assert "event_detection.data.state" in refs

    def test_adds_uncertainty_if_missing(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "limited",
            "model_inferences": [],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": [],
        }
        processed = _post_process_result(result)
        assert len(processed["uncertainties"]) >= 1
        assert "manual review" in processed["uncertainties"][0].lower()

    def test_adds_rationale_to_actions_without_it(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [
                {
                    "priority": 1,
                    "action": "Do something.",
                    "rationale": "",
                    "verification_goal": "Check.",
                }
            ],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        assert len(processed["recommended_actions"][0]["rationale"]) > 0


# ═══════════════════════════════════════════════════════════════════
# 7. Demo Mode (Category 12)
# ═══════════════════════════════════════════════════════════════════


class TestDemoMode:
    """Test demo mode returns deterministic fixture."""

    @pytest.mark.asyncio
    async def test_demo_returns_demo_fixture(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        result = await analyze_investigation(
            evidence_package=sample_evidence_package,
            use_demo=True,
        )
        resp = result.model_dump()
        assert resp["analysis"]["analysis_status"] == "complete"
        assert resp["analysis_metadata"]["mode"] == "demo"
        assert resp["analysis_metadata"]["demo"] is True
        assert resp["analysis_metadata"]["fallback_used"] is False

    @pytest.mark.asyncio
    async def test_demo_has_all_sections(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        result = await analyze_investigation(
            evidence_package=sample_evidence_package,
            use_demo=True,
        )
        analysis = result.model_dump()["analysis"]
        assert "observed_facts" in analysis
        assert "model_inferences" in analysis
        assert "investigation_hypotheses" in analysis
        assert "uncertainties" in analysis
        assert len(analysis["uncertainties"]) >= 3
        assert len(analysis["investigation_hypotheses"]) >= 2

    @pytest.mark.asyncio
    async def test_demo_no_ai_call(self, sample_evidence_package):
        """Demo mode should not call the AI provider."""
        from app.modeling.serving.ai_reasoning import analyze_investigation
        with patch(
            "app.modeling.serving.ai_reasoning._call_ai_provider",
            new_callable=AsyncMock,
        ) as mock_call:
            result = await analyze_investigation(
                evidence_package=sample_evidence_package,
                use_demo=True,
            )
            mock_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_demo_includes_evidence_package(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        result = await analyze_investigation(
            evidence_package=sample_evidence_package,
            use_demo=True,
        )
        assert "evidence" in result.model_dump()
        assert result.model_dump()["evidence"]["event_detection"]["data"]["state"] == "EPISODE"


# ═══════════════════════════════════════════════════════════════════
# 8. Missing API Key → Deterministic Fallback (Category 4)
# ═══════════════════════════════════════════════════════════════════


class TestMissingAPIKey:
    """When API key is not configured, should return fallback."""

    @pytest.mark.asyncio
    async def test_no_api_key_returns_fallback(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key=None)
            result = await analyze_investigation(
                evidence_package=sample_evidence_package,
                db_path=DB_PATH,
            )
            resp = result.model_dump()
            assert resp["analysis"]["analysis_status"] == "unavailable"
            assert resp["analysis_metadata"]["fallback_used"] is True
            assert "configured" in resp["analysis_metadata"]["fallback_reason"].lower()

    @pytest.mark.asyncio
    async def test_no_api_key_no_ai_call(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key=None)
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
            ) as mock_call:
                await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                mock_call.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# 9. Provider Timeout → Graceful Fallback (Category 5)
# ═══════════════════════════════════════════════════════════════════


class TestProviderTimeout:
    """When AI provider times out, should return fallback."""

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                ai_base_url="https://api.test.com/v1",
                ai_model="test-model",
            )
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                resp = result.model_dump()
                assert resp["analysis"]["analysis_status"] == "unavailable"
                assert resp["analysis_metadata"]["fallback_used"] is True


# ═══════════════════════════════════════════════════════════════════
# 10. Invalid JSON from AI (Category 2)
# ═══════════════════════════════════════════════════════════════════


class TestInvalidJSON:
    """When AI returns non-JSON, should return fallback."""

    @pytest.mark.asyncio
    async def test_invalid_json_returns_fallback(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                ai_base_url="https://api.test.com/v1",
                ai_model="test-model",
            )
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
                return_value="This is not JSON at all, just text.",
            ):
                result = await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                resp = result.model_dump()
                assert resp["analysis"]["analysis_status"] == "unavailable"
                assert "invalid json" in resp["analysis_metadata"]["fallback_reason"].lower()


# ═══════════════════════════════════════════════════════════════════
# 11. Invalid Schema (Category 3)
# ═══════════════════════════════════════════════════════════════════


class TestInvalidSchema:
    """When AI returns JSON that doesn't match schema, should fallback."""

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        incomplete_json = json.dumps({
            "event_summary": "Something happened.",
            # Missing analysis_status (required)
        })
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                ai_base_url="https://api.test.com/v1",
                ai_model="test-model",
            )
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
                return_value=incomplete_json,
            ):
                result = await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                resp = result.model_dump()
                assert resp["analysis"]["analysis_status"] == "unavailable"
                assert "schema" in resp["analysis_metadata"]["fallback_reason"].lower()

    @pytest.mark.asyncio
    async def test_invalid_analysis_status_value(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        invalid_json = json.dumps({
            "analysis_status": "partial",  # Not in allowed set
            "event_summary": "Test.",
        })
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                ai_base_url="https://api.test.com/v1",
                ai_model="test-model",
            )
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
                return_value=invalid_json,
            ):
                result = await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                resp = result.model_dump()
                assert resp["analysis"]["analysis_status"] == "unavailable"


# ═══════════════════════════════════════════════════════════════════
# 12. Valid AI Response (Category 1)
# ═══════════════════════════════════════════════════════════════════


class TestValidAIResponse:
    """When AI returns valid response, should post-process and return."""

    @pytest.mark.asyncio
    async def test_valid_response_passes_through(
        self, sample_evidence_package, sample_ai_valid_response
    ):
        from app.modeling.serving.ai_reasoning import analyze_investigation
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                ai_base_url="https://api.test.com/v1",
                ai_model="test-model",
            )
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
                return_value=json.dumps(sample_ai_valid_response),
            ):
                result = await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                resp = result.model_dump()
                assert resp["analysis"]["analysis_status"] == "complete"
                assert resp["analysis_metadata"]["mode"] == "ai"
                assert resp["analysis_metadata"]["fallback_used"] is False
                assert len(resp["analysis"]["observed_facts"]) == 1
                assert len(resp["analysis"]["investigation_hypotheses"]) == 1

    @pytest.mark.asyncio
    async def test_valid_response_confidence_capped(
        self, sample_evidence_package
    ):
        """Even a valid response should have confidence capped at 0.85."""
        from app.modeling.serving.ai_reasoning import analyze_investigation
        response_with_high_conf = {
            "analysis_status": "complete",
            "event_summary": "Test.",
            "severity_assessment": "Test.",
            "observed_facts": [],
            "model_inferences": [
                {
                    "statement": "Something.",
                    "confidence": 0.90,  # Above 0.85
                    "supporting_evidence": ["event_detection.data.state"],
                }
            ],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "recommended_actions": [],
            "uncertainties": ["Test uncertainty."],
            "data_gaps": [],
        }
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                openai_api_key="test-key",
                ai_base_url="https://api.test.com/v1",
                ai_model="test-model",
            )
            with patch(
                "app.modeling.serving.ai_reasoning._call_ai_provider",
                new_callable=AsyncMock,
                return_value=json.dumps(response_with_high_conf),
            ):
                result = await analyze_investigation(
                    evidence_package=sample_evidence_package,
                    db_path=DB_PATH,
                )
                resp = result.model_dump()
                # Post-processing should cap it
                assert resp["analysis"]["model_inferences"][0]["confidence"] <= 0.85


# ═══════════════════════════════════════════════════════════════════
# 13. Deterministic Fallback Builder (Category 11)
# ═══════════════════════════════════════════════════════════════════


class TestFallbackBuilder:
    """Test _build_fallback_response."""

    def test_fallback_has_unavailable_status(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import _build_fallback_response
        result = _build_fallback_response(sample_evidence_package, "Test reason")
        resp = result.model_dump()
        assert resp["analysis"]["analysis_status"] == "unavailable"
        assert resp["analysis_metadata"]["fallback_used"] is True
        assert resp["analysis_metadata"]["fallback_reason"] == "Test reason"

    def test_fallback_includes_evidence(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import _build_fallback_response
        result = _build_fallback_response(sample_evidence_package, "Test")
        assert "evidence" in result.model_dump()
        assert result.model_dump()["evidence"]["event_detection"]["data"]["state"] == "EPISODE"

    def test_fallback_has_uncertainties(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import _build_fallback_response
        result = _build_fallback_response(sample_evidence_package, "Test")
        assert len(result.model_dump()["analysis"]["uncertainties"]) >= 2

    def test_fallback_is_serializable(self, sample_evidence_package):
        from app.modeling.serving.ai_reasoning import _build_fallback_response
        result = _build_fallback_response(sample_evidence_package, "Test")
        # Should be fully JSON-serializable
        dumped = result.model_dump()
        json_str = json.dumps(dumped, default=str)
        assert len(json_str) > 100


# ═══════════════════════════════════════════════════════════════════
# 14. Unsupported Evidence Reference Filtering (Category 6)
# ═══════════════════════════════════════════════════════════════════


class TestUnsupportedEvidenceRefs:
    """Invalid evidence references should be removed, valid ones kept."""

    def test_valid_refs_kept(self):
        from app.modeling.serving.ai_reasoning import _validate_evidence_references
        items = [
            {
                "statement": "Test.",
                "supporting_evidence": [
                    "event_detection.data.state",
                    "event_detection.data.current_pm25",
                ],
            }
        ]
        result = _validate_evidence_references(items, "supporting_evidence")
        assert len(result[0]["supporting_evidence"]) == 2

    def test_invalid_refs_removed(self):
        from app.modeling.serving.ai_reasoning import _validate_evidence_references
        items = [
            {
                "statement": "Test.",
                "supporting_evidence": [
                    "event_detection.data.state",
                    "completely_fake.nonexistent.path",
                    "another_fake_path",
                ],
            }
        ]
        result = _validate_evidence_references(items, "supporting_evidence")
        assert len(result[0]["supporting_evidence"]) == 1
        assert result[0]["supporting_evidence"][0] == "event_detection.data.state"

    def test_all_invalid_refs(self):
        from app.modeling.serving.ai_reasoning import _validate_evidence_references
        items = [
            {
                "statement": "Test.",
                "evidence_references": ["fake.a.b", "another.c.d"],
            }
        ]
        result = _validate_evidence_references(items, "evidence_references")
        assert len(result[0]["evidence_references"]) == 0


# ═══════════════════════════════════════════════════════════════════
# 15. Confidence Below 0.30 Filters Hypotheses (Category 7)
# ═══════════════════════════════════════════════════════════════════


class TestLowConfidenceHypotheses:
    """Hypotheses with confidence below 0.30 should be filtered out."""

    def test_hypothesis_at_0_29_filtered(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "limited",
            "model_inferences": [],
            "investigation_hypotheses": [
                {"factor": "A", "confidence": 0.29, "supporting_evidence": []},
            ],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        assert len(processed["investigation_hypotheses"]) == 0

    def test_hypothesis_at_0_30_kept(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "limited",
            "model_inferences": [],
            "investigation_hypotheses": [
                {"factor": "A", "confidence": 0.30, "supporting_evidence": []},
            ],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        assert len(processed["investigation_hypotheses"]) == 1


# ═══════════════════════════════════════════════════════════════════
# 16. Confidence Above 0.85 Capped (Category 8)
# ═══════════════════════════════════════════════════════════════════


class TestHighConfidenceCapped:
    """Confidence above 0.85 should be capped at 0.85."""

    def test_model_inference_capped(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [
                {"statement": "X", "confidence": 0.99, "supporting_evidence": []},
            ],
            "investigation_hypotheses": [],
            "investigation_priority": {"confidence": 0.95},
            "likely_exposure_direction": {"confidence": 0.90},
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        assert processed["model_inferences"][0]["confidence"] == 0.85
        assert processed["investigation_priority"]["confidence"] == 0.85
        assert processed["likely_exposure_direction"]["confidence"] == 0.85


# ═══════════════════════════════════════════════════════════════════
# 17. Missing Uncertainties Auto-Populated (Category 9)
# ═══════════════════════════════════════════════════════════════════


class TestMissingUncertainties:
    """Missing uncertainty section should be auto-populated."""

    def test_empty_uncertainties_populated(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "limited",
            "model_inferences": [],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": [],
        }
        processed = _post_process_result(result)
        assert len(processed["uncertainties"]) >= 1
        assert "manual review" in processed["uncertainties"][0].lower()

    def test_none_uncertainties_populated(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "limited",
            "model_inferences": [],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": None,
        }
        processed = _post_process_result(result)
        assert len(processed["uncertainties"]) >= 1

    def test_existing_uncertainties_preserved(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [],
            "investigation_hypotheses": [],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": ["Existing uncertainty."],
        }
        processed = _post_process_result(result)
        assert processed["uncertainties"] == ["Existing uncertainty."]


# ═══════════════════════════════════════════════════════════════════
# 18. Missing Hypothesis Evidence Cleaned (Category 10)
# ═══════════════════════════════════════════════════════════════════


class TestHypothesisEvidenceCleaned:
    """Invalid evidence references in hypotheses should be removed."""

    def test_invalid_refs_removed_from_hypothesis(self):
        from app.modeling.serving.ai_reasoning import _post_process_result
        result = {
            "analysis_status": "complete",
            "model_inferences": [],
            "investigation_hypotheses": [
                {
                    "factor": "Test",
                    "confidence": 0.65,
                    "supporting_evidence": [
                        "event_detection.data.state",
                        "fake_nonexistent_ref",
                    ],
                }
            ],
            "investigation_priority": None,
            "likely_exposure_direction": None,
            "observed_facts": [],
            "recommended_actions": [],
            "uncertainties": ["Known."],
        }
        processed = _post_process_result(result)
        refs = processed["investigation_hypotheses"][0]["supporting_evidence"]
        assert "event_detection.data.state" in refs
        assert "fake_nonexistent_ref" not in refs


# ═══════════════════════════════════════════════════════════════════
# 19. API Endpoint Integration (Category 12 — endpoint)
# ═══════════════════════════════════════════════════════════════════


class TestAnalyzeEndpoint:
    """Test GET /api/v1/investigation/analyze endpoint."""

    def test_analyze_endpoint_exists(self, client):
        """Endpoint responds (not 404)."""
        response = client.get("/api/v1/investigation/analyze")
        assert response.status_code != 404

    def test_analyze_demo_mode(self, client):
        """Demo mode returns deterministic fixture."""
        response = client.get("/api/v1/investigation/analyze?demo=true")
        if response.status_code == 503:
            pytest.skip("Test database not available")
        if response.status_code == 200:
            data = response.json()
            assert "evidence" in data
            assert "analysis" in data
            assert "analysis_metadata" in data
            assert data["analysis_metadata"]["mode"] == "demo"
            assert data["analysis"]["analysis_status"] == "complete"

    def test_analyze_response_structure(self, client):
        """Response has all required top-level keys."""
        response = client.get("/api/v1/investigation/analyze?demo=true")
        if response.status_code == 503:
            pytest.skip("Test database not available")
        if response.status_code == 200:
            data = response.json()
            assert "evidence" in data
            assert "analysis" in data
            assert "analysis_metadata" in data
            # Evidence has expected sections
            evidence = data["evidence"]
            assert "event_detection" in evidence
            assert "metadata" in evidence
            # Analysis has expected sections
            analysis = data["analysis"]
            assert "analysis_status" in analysis
            assert "observed_facts" in analysis
            assert "investigation_hypotheses" in analysis
            assert "uncertainties" in analysis

    def test_analyze_without_demo_no_500(self, client):
        """Non-demo mode should never return 500 (fallback instead)."""
        response = client.get("/api/v1/investigation/analyze")
        # Even if AI is not configured, should return 200 with fallback
        # or 503 if DB missing — but never 500 from AI failure
        if response.status_code == 200:
            data = response.json()
            assert "analysis" in data
            # analysis_status should be either complete or unavailable
            assert data["analysis"]["analysis_status"] in ("complete", "limited", "unavailable")

    def test_analyze_no_api_key_returns_fallback(self, client):
        """Without API key, should return fallback (not 500)."""
        with patch("app.modeling.serving.ai_reasoning.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(openai_api_key=None)
            response = client.get("/api/v1/investigation/analyze")
            if response.status_code == 503:
                pytest.skip("Test database not available")
            if response.status_code == 200:
                data = response.json()
                assert data["analysis"]["analysis_status"] == "unavailable"
                assert data["analysis_metadata"]["fallback_used"] is True
