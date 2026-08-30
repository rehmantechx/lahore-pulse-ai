"""Phase 5 tests — Investigation Verification & Learning Loop.

Tests cover:
    1. Pydantic schemas: validation, defaults, enum constraints
    2. Verification service: CRUD operations, duplicate detection, stats aggregation
    3. API endpoints: POST/GET/PUT/DELETE for verification
    4. Minimum sample threshold: percentages only shown when >= 3 verified cases
    5. Error handling: not found, invalid data, duplicate investigation_id
    6. Historical analog enrichment: verification context injection

All tests use a real SQLite database (no mocks for core logic).
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ── Paths ──────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════
# 1. Schema Validation Tests
# ═══════════════════════════════════════════════════════════════════


class TestVerificationSchemas:
    """Pydantic v2 schema validation tests."""

    def test_status_enums(self):
        """Status enums have expected values."""
        from app.modeling.serving.verification_schemas import (
            OverallVerificationStatus,
            RecommendationVerification,
            InvestigationAreaVerification,
        )
        assert OverallVerificationStatus.USEFUL.value == "USEFUL"
        assert OverallVerificationStatus.PARTIALLY_USEFUL.value == "PARTIALLY_USEFUL"
        assert OverallVerificationStatus.NOT_SUPPORTED.value == "NOT_SUPPORTED"
        assert OverallVerificationStatus.INCONCLUSIVE.value == "INCONCLUSIVE"

        assert RecommendationVerification.SUPPORTED.value == "SUPPORTED"
        assert InvestigationAreaVerification.PARTIALLY_SUPPORTED.value == "PARTIALLY_SUPPORTED"

    def test_verification_create_request_valid(self):
        """Valid request creates without error."""
        from app.modeling.serving.verification_schemas import VerificationCreateRequest
        req = VerificationCreateRequest(
            investigation_id="inv-001",
            overall_status="USEFUL",
        )
        assert req.investigation_id == "inv-001"
        assert req.overall_status == "USEFUL"
        # recommendation_verification defaults to UNKNOWN, not None
        assert req.recommendation_verification.value == "UNKNOWN"
        assert req.hypothesis_verifications == []
        assert req.field_notes == ""
        assert req.verified_by == ""

    def test_verification_create_request_full(self):
        """Full request with all fields."""
        from app.modeling.serving.verification_schemas import VerificationCreateRequest
        req = VerificationCreateRequest(
            investigation_id="inv-002",
            overall_status="PARTIALLY_USEFUL",
            recommendation_verification="SUPPORTED",
            investigation_area_verification="NOT_SUPPORTED",
            hypothesis_verifications=[
                {"factor": "Industrial emissions", "verified": True, "notes": "Confirmed"},
                {"factor": "Crop burning", "verified": False, "notes": "Not observed"},
            ],
            field_notes="Field observations here",
            verified_by="Officer Khan",
        )
        assert len(req.hypothesis_verifications) == 2
        # HypothesisVerification objects — access via attribute, not subscript
        assert req.hypothesis_verifications[0].verified is True
        assert req.hypothesis_verifications[0].factor == "Industrial emissions"
        assert req.hypothesis_verifications[1].verified is False

    def test_verification_create_request_invalid_status(self):
        """Invalid status raises validation error."""
        from app.modeling.serving.verification_schemas import VerificationCreateRequest
        with pytest.raises(Exception):
            VerificationCreateRequest(
                investigation_id="inv-001",
                overall_status="INVALID_STATUS",
            )

    def test_verification_update_request_optional_fields(self):
        """Update request allows partial fields."""
        from app.modeling.serving.verification_schemas import VerificationUpdateRequest
        req = VerificationUpdateRequest(overall_status="NOT_SUPPORTED")
        assert req.overall_status == "NOT_SUPPORTED"
        assert req.recommendation_verification is None
        assert req.field_notes is None

    def test_verification_outcome_response_fields(self):
        """Response model has all expected fields."""
        from app.modeling.serving.verification_schemas import VerificationOutcomeResponse
        resp = VerificationOutcomeResponse(
            outcome_id="vout-001",
            investigation_id="inv-001",
            overall_status="USEFUL",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert resp.outcome_id == "vout-001"
        # recommendation_verification defaults to UNKNOWN, not None
        assert resp.recommendation_verification.value == "UNKNOWN"

    def test_verification_stats_min_sample(self):
        """Stats model includes MIN_SAMPLE_FOR_STATS constant."""
        from app.modeling.serving.verification_schemas import MIN_SAMPLE_FOR_STATS
        assert MIN_SAMPLE_FOR_STATS == 3

    def test_hypothesis_verification_schema(self):
        """Hypothesis verification has factor, verified, notes."""
        from app.modeling.serving.verification_schemas import HypothesisVerification
        hv = HypothesisVerification(factor="Test factor", verified=True, notes="Test notes")
        assert hv.factor == "Test factor"
        assert hv.verified is True


# ═══════════════════════════════════════════════════════════════════
# 2. Verification Service Tests
# ═══════════════════════════════════════════════════════════════════


class TestVerificationService:
    """Tests for verification CRUD operations and aggregation."""

    @pytest.fixture
    def tmp_db(self, tmp_path):
        """Create a temporary database with verification_outcomes table."""
        db_path = str(tmp_path / "test_verification.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verification_outcomes (
                outcome_id                      TEXT PRIMARY KEY,
                investigation_id                 TEXT NOT NULL,
                overall_status                  TEXT NOT NULL
                    CHECK(overall_status IN ('USEFUL','PARTIALLY_USEFUL','NOT_SUPPORTED','INCONCLUSIVE')),
                recommendation_verification     TEXT
                    CHECK(recommendation_verification IN ('SUPPORTED','PARTIALLY_SUPPORTED','NOT_SUPPORTED','UNKNOWN')),
                investigation_area_verification  TEXT
                    CHECK(investigation_area_verification IN ('SUPPORTED','PARTIALLY_SUPPORTED','NOT_SUPPORTED','UNKNOWN')),
                hypothesis_verifications         TEXT,
                field_notes                      TEXT,
                verified_by                      TEXT,
                verified_at                      TEXT,
                investigation_context             TEXT DEFAULT NULL,
                created_at                       TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at                       TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_investigation ON verification_outcomes(investigation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_status ON verification_outcomes(overall_status)")
        conn.commit()
        conn.close()
        return db_path

    def test_store_and_retrieve(self, tmp_db):
        """Store a verification and retrieve it by investigation ID."""
        from app.modeling.serving.verification import store_verification, get_verification_by_investigation
        from app.modeling.serving.verification_schemas import VerificationCreateRequest

        req = VerificationCreateRequest(
            investigation_id="inv-store-001",
            overall_status="USEFUL",
            recommendation_verification="SUPPORTED",
            field_notes="Test field notes",
            verified_by="Test Officer",
        )

        outcome = store_verification(tmp_db, req)
        assert outcome.outcome_id.startswith("vout-")
        assert outcome.investigation_id == "inv-store-001"
        assert outcome.overall_status == "USEFUL"

        retrieved = get_verification_by_investigation(tmp_db, "inv-store-001")
        assert retrieved is not None
        assert retrieved.outcome_id == outcome.outcome_id

    def test_duplicate_investigation_id_rejected(self, tmp_db):
        """Storing two verifications for the same investigation raises ValueError."""
        from app.modeling.serving.verification import store_verification
        from app.modeling.serving.verification_schemas import VerificationCreateRequest

        req1 = VerificationCreateRequest(
            investigation_id="inv-dup-001",
            overall_status="USEFUL",
        )
        store_verification(tmp_db, req1)

        req2 = VerificationCreateRequest(
            investigation_id="inv-dup-001",
            overall_status="NOT_SUPPORTED",
        )
        with pytest.raises(ValueError, match="already exists"):
            store_verification(tmp_db, req2)

    def test_get_nonexistent_returns_none(self, tmp_db):
        """Looking up nonexistent investigation returns None."""
        from app.modeling.serving.verification import get_verification_by_investigation
        result = get_verification_by_investigation(tmp_db, "nonexistent")
        assert result is None

    def test_get_by_id(self, tmp_db):
        """Retrieve by outcome_id."""
        from app.modeling.serving.verification import store_verification, get_verification_by_id
        from app.modeling.serving.verification_schemas import VerificationCreateRequest

        req = VerificationCreateRequest(investigation_id="inv-id-001", overall_status="INCONCLUSIVE")
        outcome = store_verification(tmp_db, req)

        retrieved = get_verification_by_id(tmp_db, outcome.outcome_id)
        assert retrieved is not None
        assert retrieved.overall_status == "INCONCLUSIVE"

    def test_update_verification(self, tmp_db):
        """Update specific fields of an existing outcome."""
        from app.modeling.serving.verification import store_verification, update_verification, get_verification_by_id
        from app.modeling.serving.verification_schemas import VerificationCreateRequest, VerificationUpdateRequest

        req = VerificationCreateRequest(investigation_id="inv-upd-001", overall_status="INCONCLUSIVE")
        outcome = store_verification(tmp_db, req)

        update_req = VerificationUpdateRequest(
            overall_status="USEFUL",
            field_notes="Updated field notes",
        )
        updated = update_verification(tmp_db, outcome.outcome_id, update_req)
        assert updated is not None
        assert updated.overall_status == "USEFUL"
        assert updated.field_notes == "Updated field notes"

    def test_delete_verification(self, tmp_db):
        """Delete returns True for existing, False for nonexistent."""
        from app.modeling.serving.verification import store_verification, delete_verification
        from app.modeling.serving.verification_schemas import VerificationCreateRequest

        req = VerificationCreateRequest(investigation_id="inv-del-001", overall_status="USEFUL")
        outcome = store_verification(tmp_db, req)

        assert delete_verification(tmp_db, outcome.outcome_id) is True
        assert delete_verification(tmp_db, "nonexistent") is False

    def test_list_verifications(self, tmp_db):
        """List verifications with optional status filter."""
        from app.modeling.serving.verification import store_verification, get_all_verifications
        from app.modeling.serving.verification_schemas import VerificationCreateRequest

        for i in range(3):
            req = VerificationCreateRequest(
                investigation_id=f"inv-list-{i:03d}",
                overall_status="USEFUL" if i < 2 else "NOT_SUPPORTED",
            )
            store_verification(tmp_db, req)

        all_outcomes = get_all_verifications(tmp_db)
        assert len(all_outcomes) == 3

        useful_only = get_all_verifications(tmp_db, status="USEFUL")
        assert len(useful_only) == 2

        not_supported_only = get_all_verifications(tmp_db, status="NOT_SUPPORTED")
        assert len(not_supported_only) == 1


# ═══════════════════════════════════════════════════════════════════
# 3. Stats Aggregation Tests
# ═══════════════════════════════════════════════════════════════════


class TestVerificationStats:
    """Tests for stats aggregation and minimum sample threshold."""

    @pytest.fixture
    def tmp_db(self, tmp_path):
        """Create temp database."""
        db_path = str(tmp_path / "test_stats.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
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
                investigation_context             TEXT DEFAULT NULL,
                created_at                       TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at                       TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
        return db_path

    def _insert_outcome(self, db_path, inv_id, overall, rec=None, area=None, hyps=None):
        """Helper to insert a verification outcome directly."""
        conn = sqlite3.connect(db_path)
        conn.execute("""
            INSERT INTO verification_outcomes
            (outcome_id, investigation_id, overall_status, recommendation_verification,
             investigation_area_verification, hypothesis_verifications, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            f"vout-{uuid.uuid4().hex[:12]}",
            inv_id,
            overall,
            rec,
            area,
            json.dumps(hyps) if hyps else None,
        ))
        conn.commit()
        conn.close()

    def test_empty_stats(self, tmp_db):
        """Empty database returns zero stats."""
        from app.modeling.serving.verification import compute_verification_stats
        stats = compute_verification_stats(tmp_db)
        assert stats.total_verifications == 0
        assert stats.useful_count == 0

    def test_stats_with_fewer_than_3(self, tmp_db):
        """Fewer than 3 verifications: percentages are None."""
        from app.modeling.serving.verification import compute_verification_stats
        self._insert_outcome(tmp_db, "inv-1", "USEFUL", "SUPPORTED")
        self._insert_outcome(tmp_db, "inv-2", "PARTIALLY_USEFUL")

        stats = compute_verification_stats(tmp_db)
        assert stats.total_verifications == 2
        assert stats.useful_count == 1
        assert stats.recommendation_supported_pct is None
        assert stats.area_supported_pct is None
        assert stats.hypothesis_hit_rate is None

    def test_stats_with_3_or_more(self, tmp_db):
        """3+ verifications: percentages are calculated."""
        from app.modeling.serving.verification import compute_verification_stats
        self._insert_outcome(tmp_db, "inv-1", "USEFUL", "SUPPORTED", "SUPPORTED",
                             [{"factor": "A", "verified": True}, {"factor": "B", "verified": False}])
        self._insert_outcome(tmp_db, "inv-2", "USEFUL", "SUPPORTED", "PARTIALLY_SUPPORTED",
                             [{"factor": "A", "verified": True}])
        self._insert_outcome(tmp_db, "inv-3", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED")

        stats = compute_verification_stats(tmp_db)
        assert stats.total_verifications == 3
        assert stats.useful_count == 2
        assert stats.not_supported_count == 1
        assert stats.recommendation_supported_pct is not None
        assert stats.area_supported_pct is not None
        assert stats.hypothesis_hit_rate is not None
        assert 0 <= stats.recommendation_supported_pct <= 100

    def test_stats_status_distribution(self, tmp_db):
        """Status counts are accurate."""
        from app.modeling.serving.verification import compute_verification_stats
        self._insert_outcome(tmp_db, "inv-1", "USEFUL")
        self._insert_outcome(tmp_db, "inv-2", "USEFUL")
        self._insert_outcome(tmp_db, "inv-3", "PARTIALLY_USEFUL")
        self._insert_outcome(tmp_db, "inv-4", "NOT_SUPPORTED")
        self._insert_outcome(tmp_db, "inv-5", "INCONCLUSIVE")

        stats = compute_verification_stats(tmp_db)
        assert stats.total_verifications == 5
        assert stats.useful_count == 2
        assert stats.partially_useful_count == 1
        assert stats.not_supported_count == 1
        assert stats.inconclusive_count == 1


# ═══════════════════════════════════════════════════════════════════
# 4. API Endpoint Tests
# ═══════════════════════════════════════════════════════════════════


class TestVerificationAPI:
    """Tests for verification API endpoints."""

    @pytest.fixture
    def mock_db_path(self, tmp_path, monkeypatch):
        """Patch _get_db_path to use temp database."""
        from pathlib import Path
        db_path = Path(tmp_path / "test_api.db")

        # Initialize the database with the schema
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
                investigation_context             TEXT DEFAULT NULL,
                created_at                       TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at                       TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_investigation ON verification_outcomes(investigation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_status ON verification_outcomes(overall_status)")
        conn.commit()
        conn.close()

        monkeypatch.setattr("app.api.v1.verification._get_db_path", lambda: db_path)
        return db_path

    def test_submit_verification(self, client, mock_db_path):
        """POST /api/v1/verification creates a new outcome."""
        response = client.post("/api/v1/verification", json={
            "investigation_id": "api-inv-001",
            "overall_status": "USEFUL",
            "recommendation_verification": "SUPPORTED",
            "field_notes": "Test submission",
            "verified_by": "API Tester",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["outcome_id"].startswith("vout-")
        assert data["investigation_id"] == "api-inv-001"
        assert data["overall_status"] == "USEFUL"

    def test_submit_duplicate_investigation(self, client, mock_db_path):
        """POST duplicate investigation_id returns 409."""
        client.post("/api/v1/verification", json={
            "investigation_id": "api-dup-001",
            "overall_status": "USEFUL",
        })
        response = client.post("/api/v1/verification", json={
            "investigation_id": "api-dup-001",
            "overall_status": "NOT_SUPPORTED",
        })
        assert response.status_code == 409

    def test_get_verification_context(self, client, mock_db_path):
        """GET /api/v1/verification/context/{id} returns context."""
        # First create one
        client.post("/api/v1/verification", json={
            "investigation_id": "api-ctx-001",
            "overall_status": "PARTIALLY_USEFUL",
        })

        response = client.get("/api/v1/verification/context/api-ctx-001")
        assert response.status_code == 200
        data = response.json()
        assert "current_outcome" in data
        assert "stats" in data
        assert "disclaimer" in data

    def test_get_verification_context_not_found(self, client, mock_db_path):
        """GET context for nonexistent investigation returns null outcome."""
        response = client.get("/api/v1/verification/context/nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["current_outcome"] is None

    def test_get_verification_stats(self, client, mock_db_path):
        """GET /api/v1/verification/stats returns aggregated stats."""
        response = client.get("/api/v1/verification/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_verifications" in data
        assert "useful_count" in data

    def test_list_verifications(self, client, mock_db_path):
        """GET /api/v1/verification returns list."""
        # Create some entries
        for i in range(3):
            client.post("/api/v1/verification", json={
                "investigation_id": f"api-list-{i:03d}",
                "overall_status": "USEFUL",
            })

        response = client.get("/api/v1/verification")
        assert response.status_code == 200
        data = response.json()
        # List endpoint returns paginated response with 'outcomes' key
        assert "outcomes" in data
        assert isinstance(data["outcomes"], list)
        assert len(data["outcomes"]) >= 3
        assert data["count"] >= 3

    def test_update_verification(self, client, mock_db_path):
        """PUT /api/v1/verification/{id} updates fields."""
        # Create
        create_resp = client.post("/api/v1/verification", json={
            "investigation_id": "api-upd-001",
            "overall_status": "INCONCLUSIVE",
        })
        outcome_id = create_resp.json()["outcome_id"]

        # Update
        response = client.put(f"/api/v1/verification/{outcome_id}", json={
            "overall_status": "USEFUL",
            "field_notes": "Updated via API",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "USEFUL"
        assert data["field_notes"] == "Updated via API"

    def test_delete_verification(self, client, mock_db_path):
        """DELETE /api/v1/verification/{id} returns 204."""
        create_resp = client.post("/api/v1/verification", json={
            "investigation_id": "api-del-001",
            "overall_status": "USEFUL",
        })
        outcome_id = create_resp.json()["outcome_id"]

        response = client.delete(f"/api/v1/verification/{outcome_id}")
        assert response.status_code == 204

    def test_delete_nonexistent_returns_404(self, client, mock_db_path):
        """DELETE nonexistent returns 404."""
        response = client.delete("/api/v1/verification/vout-nonexistent")
        assert response.status_code == 404

    def test_submit_invalid_status_returns_422(self, client, mock_db_path):
        """POST with invalid status returns 422."""
        response = client.post("/api/v1/verification", json={
            "investigation_id": "api-invalid-001",
            "overall_status": "INVALID_STATUS",
        })
        assert response.status_code == 422
