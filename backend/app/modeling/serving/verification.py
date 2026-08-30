"""Investigation Verification Service (Phase 5 — Learning Loop).

Provides persistence and retrieval for human verification of AI investigation results.

Design Rules:
- NEVER modify original AI analysis when storing verification
- Use language: "Recommendation supported" NOT "AI was correct"
- Minimum 3 verified cases before showing percentage statistics
- Historical verification is context only, not a guarantee
- This is a transparent feedback loop, NOT machine learning
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from .verification_schemas import (
    MIN_SAMPLE_FOR_STATS,
    HypothesisVerification,
    InvestigationAreaVerification,
    OverallVerificationStatus,
    RecommendationVerification,
    VerificationCreateRequest,
    VerificationOutcomeResponse,
    VerificationStats,
    VerificationUpdateRequest,
)


# ── Helpers ────────────────────────────────────────────────────────


def _parse_context(row: sqlite3.Row) -> dict | None:
    """Parse investigation_context JSON from a database row.

    Returns the parsed dict if present, None if NULL or invalid.
    """
    raw = row["investigation_context"] if "investigation_context" in row.keys() else None
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _get_write_connection(db_path: Path) -> sqlite3.Connection:
    """Open a write connection with WAL mode and foreign keys."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _get_read_connection(db_path: Path) -> sqlite3.Connection:
    """Open a read-only connection.

    Uses file: URI for read-only mode. On Windows, forward-slashes
    are required for the URI to parse correctly.
    """
    # Normalize path for URI: forward slashes, no leading slash on Windows
    uri_path = str(db_path).replace("\\", "/")
    # On Windows paths like C:/..., need to prefix with an extra slash
    if len(uri_path) >= 2 and uri_path[1] == ":":
        uri_path = "/" + uri_path
    conn = sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_outcome(row: sqlite3.Row) -> VerificationOutcomeResponse:
    """Convert a database row to a VerificationOutcomeResponse."""
    raw_hypotheses = row["hypothesis_verifications"]
    hypotheses = []
    if raw_hypotheses:
        try:
            parsed = json.loads(raw_hypotheses)
            hypotheses = [HypothesisVerification(**h) for h in parsed]
        except (json.JSONDecodeError, TypeError):
            hypotheses = []

    return VerificationOutcomeResponse(
        outcome_id=row["outcome_id"],
        investigation_id=row["investigation_id"],
        overall_status=OverallVerificationStatus(row["overall_status"]),
        recommendation_verification=RecommendationVerification(
            row["recommendation_verification"] or "UNKNOWN"
        ),
        investigation_area_verification=InvestigationAreaVerification(
            row["investigation_area_verification"] or "UNKNOWN"
        ),
        hypothesis_verifications=hypotheses,
        field_notes=row["field_notes"] or "",
        verified_by=row["verified_by"] or "",
        verified_at=row["verified_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        investigation_context=_parse_context(row),
    )


# ── Create ─────────────────────────────────────────────────────────


def store_verification(
    db_path: Path,
    request: VerificationCreateRequest,
) -> VerificationOutcomeResponse:
    """Store a new verification outcome for an investigation.

    The AI analysis itself is NEVER modified — verification is stored separately.
    If a verification already exists for this investigation_id, raises ValueError.

    Args:
        db_path: Path to the SQLite database.
        request: Verification submission request.

    Returns:
        The stored verification outcome response.

    Raises:
        ValueError: If a verification already exists for this investigation_id.
    """
    now = datetime.now(UTC).isoformat()
    outcome_id = f"vout-{uuid.uuid4().hex[:12]}"

    # Check for existing verification
    conn = _get_write_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT outcome_id FROM verification_outcomes WHERE investigation_id = ?",
            [request.investigation_id],
        ).fetchone()

        if existing:
            raise ValueError(
                f"Verification already exists for investigation '{request.investigation_id}'. "
                f"Use PUT to update, or delete the existing outcome first."
            )

        # Serialize hypothesis verifications
        hyp_json = json.dumps([h.model_dump() for h in request.hypothesis_verifications])

        # Set verified_at only when status is not PENDING
        verified_at = now if request.overall_status != OverallVerificationStatus.PENDING else None

        # Serialize investigation context (environmental snapshot for learning)
        context_json = json.dumps(request.investigation_context) if request.investigation_context else None

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
                request.investigation_id,
                request.overall_status.value,
                request.recommendation_verification.value,
                request.investigation_area_verification.value,
                hyp_json,
                request.field_notes,
                request.verified_by,
                verified_at,
                now,
                now,
                context_json,
            ),
        )
        conn.commit()
        logger.info(
            "Verification outcome stored",
            outcome_id=outcome_id,
            investigation_id=request.investigation_id,
            status=request.overall_status.value,
        )

        # Read back the stored record
        row = conn.execute(
            "SELECT * FROM verification_outcomes WHERE outcome_id = ?",
            [outcome_id],
        ).fetchone()
        return _row_to_outcome(row)

    finally:
        conn.close()


# ── Read ───────────────────────────────────────────────────────────


def get_verification_by_investigation(
    db_path: Path,
    investigation_id: str,
) -> VerificationOutcomeResponse | None:
    """Retrieve a verification outcome by investigation ID.

    Args:
        db_path: Path to the SQLite database.
        investigation_id: The investigation session identifier.

    Returns:
        The verification outcome if found, None otherwise.
    """
    conn = _get_read_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM verification_outcomes WHERE investigation_id = ?",
            [investigation_id],
        ).fetchone()
        return _row_to_outcome(row) if row else None
    finally:
        conn.close()


def get_verification_by_id(
    db_path: Path,
    outcome_id: str,
) -> VerificationOutcomeResponse | None:
    """Retrieve a verification outcome by its outcome ID.

    Args:
        db_path: Path to the SQLite database.
        outcome_id: The outcome identifier.

    Returns:
        The verification outcome if found, None otherwise.
    """
    conn = _get_read_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM verification_outcomes WHERE outcome_id = ?",
            [outcome_id],
        ).fetchone()
        return _row_to_outcome(row) if row else None
    finally:
        conn.close()


def get_all_verifications(
    db_path: Path,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[VerificationOutcomeResponse]:
    """List verification outcomes with optional status filter.

    Args:
        db_path: Path to the SQLite database.
        status: Optional filter by overall_status.
        limit: Maximum results to return.
        offset: Pagination offset.

    Returns:
        List of verification outcomes, most recent first.
    """
    conn = _get_read_connection(db_path)
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM verification_outcomes "
                "WHERE overall_status = ? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [status, limit, offset],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM verification_outcomes "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
        return [_row_to_outcome(row) for row in rows]
    finally:
        conn.close()


# ── Update ─────────────────────────────────────────────────────────


def update_verification(
    db_path: Path,
    outcome_id: str,
    request: VerificationUpdateRequest,
) -> VerificationOutcomeResponse:
    """Update an existing verification outcome.

    Only provided (non-None) fields are updated.

    Args:
        db_path: Path to the SQLite database.
        outcome_id: The outcome identifier to update.
        request: Update request with partial fields.

    Returns:
        The updated verification outcome.

    Raises:
        ValueError: If no outcome with the given ID exists.
    """
    now = datetime.now(UTC).isoformat()
    conn = _get_write_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT * FROM verification_outcomes WHERE outcome_id = ?",
            [outcome_id],
        ).fetchone()
        if not existing:
            raise ValueError(f"Verification outcome '{outcome_id}' not found.")

        # Build dynamic UPDATE
        updates: list[str] = []
        params: list = []

        if request.overall_status is not None:
            updates.append("overall_status = ?")
            params.append(request.overall_status.value)
            # Update verified_at when status is finalized
            if request.overall_status != OverallVerificationStatus.PENDING:
                updates.append("verified_at = ?")
                params.append(now)

        if request.recommendation_verification is not None:
            updates.append("recommendation_verification = ?")
            params.append(request.recommendation_verification.value)

        if request.investigation_area_verification is not None:
            updates.append("investigation_area_verification = ?")
            params.append(request.investigation_area_verification.value)

        if request.hypothesis_verifications is not None:
            updates.append("hypothesis_verifications = ?")
            params.append(
                json.dumps([h.model_dump() for h in request.hypothesis_verifications])
            )

        if request.field_notes is not None:
            updates.append("field_notes = ?")
            params.append(request.field_notes)

        if not updates:
            # Nothing to update — return existing
            return _row_to_outcome(existing)

        updates.append("updated_at = ?")
        params.append(now)
        params.append(outcome_id)

        conn.execute(
            f"UPDATE verification_outcomes SET {', '.join(updates)} WHERE outcome_id = ?",
            params,
        )
        conn.commit()
        logger.info("Verification outcome updated", outcome_id=outcome_id)

        row = conn.execute(
            "SELECT * FROM verification_outcomes WHERE outcome_id = ?",
            [outcome_id],
        ).fetchone()
        return _row_to_outcome(row)

    finally:
        conn.close()


# ── Delete ─────────────────────────────────────────────────────────


def delete_verification(
    db_path: Path,
    outcome_id: str,
) -> bool:
    """Delete a verification outcome.

    Args:
        db_path: Path to the SQLite database.
        outcome_id: The outcome identifier to delete.

    Returns:
        True if deleted, False if not found.
    """
    conn = _get_write_connection(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM verification_outcomes WHERE outcome_id = ?",
            [outcome_id],
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Verification outcome deleted", outcome_id=outcome_id)
        return deleted
    finally:
        conn.close()


# ── Aggregation ────────────────────────────────────────────────────


def compute_verification_stats(db_path: Path) -> VerificationStats:
    """Compute aggregate verification statistics.

    Only returns percentage statistics when minimum sample threshold (3) is met.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        VerificationStats with counts and optional percentages.
    """
    conn = _get_read_connection(db_path)
    try:
        # Overall status counts
        status_rows = conn.execute(
            "SELECT overall_status, COUNT(*) as cnt "
            "FROM verification_outcomes "
            "WHERE overall_status != 'PENDING' "
            "GROUP BY overall_status"
        ).fetchall()

        counts = {row["overall_status"]: row["cnt"] for row in status_rows}
        total = sum(counts.values())

        useful_count = counts.get("USEFUL", 0)
        partially_useful_count = counts.get("PARTIALLY_USEFUL", 0)
        not_supported_count = counts.get("NOT_SUPPORTED", 0)
        inconclusive_count = counts.get("INCONCLUSIVE", 0)

        # Only compute percentages when we have enough data
        has_enough = total >= MIN_SAMPLE_FOR_STATS

        # Recommendation support percentage
        rec_supported_pct = None
        if has_enough:
            rec_rows = conn.execute(
                "SELECT recommendation_verification, COUNT(*) as cnt "
                "FROM verification_outcomes "
                "WHERE overall_status != 'PENDING' "
                "AND recommendation_verification IS NOT NULL "
                "GROUP BY recommendation_verification"
            ).fetchall()
            rec_counts = {row["recommendation_verification"]: row["cnt"] for row in rec_rows}
            rec_total = sum(rec_counts.values())
            if rec_total >= MIN_SAMPLE_FOR_STATS:
                rec_supported = rec_counts.get("SUPPORTED", 0)
                rec_supported_pct = round((rec_supported / rec_total) * 100, 1) if rec_total > 0 else None

        # Investigation area support percentage
        area_supported_pct = None
        if has_enough:
            area_rows = conn.execute(
                "SELECT investigation_area_verification, COUNT(*) as cnt "
                "FROM verification_outcomes "
                "WHERE overall_status != 'PENDING' "
                "AND investigation_area_verification IS NOT NULL "
                "GROUP BY investigation_area_verification"
            ).fetchall()
            area_counts = {row["investigation_area_verification"]: row["cnt"] for row in area_rows}
            area_total = sum(area_counts.values())
            if area_total >= MIN_SAMPLE_FOR_STATS:
                area_supported = area_counts.get("SUPPORTED", 0)
                area_supported_pct = round((area_supported / area_total) * 100, 1) if area_total > 0 else None

        # Hypothesis hit rate
        hypothesis_hit_rate = None
        if has_enough:
            hyp_rows = conn.execute(
                "SELECT hypothesis_verifications "
                "FROM verification_outcomes "
                "WHERE overall_status != 'PENDING' "
                "AND hypothesis_verifications IS NOT NULL "
                "AND hypothesis_verifications != '[]'"
            ).fetchall()
            total_hyps = 0
            verified_hyps = 0
            for row in hyp_rows:
                try:
                    hyps = json.loads(row["hypothesis_verifications"])
                    for h in hyps:
                        total_hyps += 1
                        if h.get("verified", False):
                            verified_hyps += 1
                except (json.JSONDecodeError, TypeError):
                    continue
            if total_hyps >= MIN_SAMPLE_FOR_STATS:
                hypothesis_hit_rate = round((verified_hyps / total_hyps) * 100, 1) if total_hyps > 0 else None

        return VerificationStats(
            total_verifications=total,
            useful_count=useful_count,
            partially_useful_count=partially_useful_count,
            not_supported_count=not_supported_count,
            inconclusive_count=inconclusive_count,
            recommendation_supported_pct=rec_supported_pct,
            area_supported_pct=area_supported_pct,
            hypothesis_hit_rate=hypothesis_hit_rate,
        )

    finally:
        conn.close()
