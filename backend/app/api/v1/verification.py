"""Investigation Verification API endpoints (Phase 5 — Learning Loop).

Endpoints:
    POST   /api/v1/verification
        → Submit a verification outcome for an investigation

    GET    /api/v1/verification
        → List all verification outcomes (with optional status filter)

    GET    /api/v1/verification/{outcome_id}
        → Get a specific verification outcome

    PUT    /api/v1/verification/{outcome_id}
        → Update a verification outcome

    DELETE /api/v1/verification/{outcome_id}
        → Delete a verification outcome

    GET    /api/v1/verification/stats
        → Get aggregated verification statistics

    GET    /api/v1/verification/context/{investigation_id}
        → Get verification context for an investigation

Design:
    - Verification is stored SEPARATELY from AI analysis
    - AI analysis is NEVER modified when verification is stored
    - Minimum 3 verified cases before showing percentage statistics
    - Historical verification is context only, not a guarantee
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..auth import require_officer, TokenPayload
from ...core.config import get_settings
from ...core.errors import ErrorCode
from ...modeling.serving.verification import (
    compute_verification_stats,
    delete_verification,
    get_all_verifications,
    get_verification_by_id,
    get_verification_by_investigation,
    store_verification,
    update_verification,
)
from ...modeling.serving.verification_schemas import (
    VerificationContextResponse,
    VerificationCreateRequest,
    VerificationOutcomeResponse,
    VerificationStats,
    VerificationUpdateRequest,
)

router = APIRouter(prefix="/verification", tags=["verification"])


# ── Helpers ────────────────────────────────────────────────────────


def _resolve_backend_root() -> Path:
    """Resolve the backend/ project root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_db_path() -> Path:
    """Get resolved database path."""
    settings = get_settings()
    backend_dir = _resolve_backend_root()
    db_path = settings.database_url.replace("sqlite:///", "")
    db_path_obj = Path(db_path)
    if not db_path_obj.is_absolute():
        db_path_obj = backend_dir / db_path_obj
    return db_path_obj


def _validate_database(db_path: Path) -> None:
    """Raise HTTP 503 if database doesn't exist."""
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": ErrorCode.DATA_SOURCE_UNAVAILABLE.value,
                    "message": "Database not found",
                    "details": {"error": "Database not available"},
                }
            },
        )


# ── Endpoints ──────────────────────────────────────────────────────


@router.post(
    "",
    summary="Submit investigation verification",
    description=(
        "Store a human verification outcome for an AI investigation. "
        "The AI analysis is NEVER modified — verification is stored separately. "
        "Each investigation can only have one verification outcome."
    ),
    response_model=VerificationOutcomeResponse,
    status_code=201,
)
async def submit_verification(request: VerificationCreateRequest, _auth: TokenPayload = Depends(require_officer)) -> dict:
    """Submit a verification outcome for an investigation.

    The verification links to an investigation_id and stores:
    - overall_status: USEFUL / PARTIALLY_USEFUL / NOT_SUPPORTED / INCONCLUSIVE
    - recommendation_verification: Was the recommended corridor supported?
    - investigation_area_verification: Was the area verified in the field?
    - hypothesis_verifications: Per-hypothesis verification results
    - field_notes: Free-text notes from the investigation
    """
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        result = store_verification(db_path, request)
        return result.model_dump()
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": ErrorCode.CLIENT_INVALID_REQUEST.value,
                    "message": str(exc),
                }
            },
        )
    except Exception as exc:
        logger.error("Verification storage failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.get(
    "/stats",
    summary="Get aggregated verification statistics",
    description=(
        "Returns aggregate verification statistics across all outcomes. "
        "Percentage statistics are only shown when minimum sample threshold (3) is met. "
        "This provides transparent context, not AI accuracy claims."
    ),
    response_model=VerificationStats,
)
async def get_verification_statistics() -> dict:
    """Get aggregated verification statistics.

    Returns counts by status and optional percentages.
    Percentages are null when fewer than 3 verified cases exist.
    """
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        stats = compute_verification_stats(db_path)
        return stats.model_dump()
    except Exception as exc:
        logger.error("Verification stats computation failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.get(
    "/context/{investigation_id}",
    summary="Get verification context for an investigation",
    description=(
        "Returns the verification outcome (if any) for a specific investigation, "
        "along with aggregate statistics. Provides transparent context for ongoing "
        "investigations without claiming AI accuracy."
    ),
    response_model=VerificationContextResponse,
)
async def get_verification_context(investigation_id: str) -> dict:
    """Get verification context for a specific investigation.

    Returns:
    - current_outcome: The verification outcome for this investigation (if verified)
    - stats: Aggregate verification statistics
    - disclaimer: Note that verification is context, not a guarantee
    """
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        outcome = get_verification_by_investigation(db_path, investigation_id)
        stats = compute_verification_stats(db_path)

        return VerificationContextResponse(
            current_outcome=outcome,
            stats=stats,
        ).model_dump()
    except Exception as exc:
        logger.error("Verification context retrieval failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.get(
    "/{outcome_id}",
    summary="Get a specific verification outcome",
    description="Retrieve a verification outcome by its ID.",
    response_model=VerificationOutcomeResponse,
)
async def get_verification(outcome_id: str) -> dict:
    """Get a specific verification outcome by ID."""
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        result = get_verification_by_id(db_path, outcome_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ErrorCode.CLIENT_INVALID_REQUEST.value,
                        "message": f"Verification outcome '{outcome_id}' not found",
                    }
                },
            )
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Verification retrieval failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.get(
    "",
    summary="List verification outcomes",
    description=(
        "List all verification outcomes with optional status filter. "
        "Results ordered by most recent first."
    ),
)
async def list_verifications(
    status: str | None = Query(
        default=None,
        description="Filter by overall_status (USEFUL, PARTIALLY_USEFUL, NOT_SUPPORTED, INCONCLUSIVE, PENDING)",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> dict:
    """List verification outcomes with optional filters."""
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        results = get_all_verifications(db_path, status=status, limit=limit, offset=offset)
        return {
            "outcomes": [r.model_dump() for r in results],
            "count": len(results),
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        logger.error("Verification listing failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.put(
    "/{outcome_id}",
    summary="Update a verification outcome",
    description=(
        "Update an existing verification outcome. Only provided fields are updated. "
        "The linked AI analysis is NEVER modified."
    ),
    response_model=VerificationOutcomeResponse,
)
async def update_outcome(outcome_id: str, request: VerificationUpdateRequest, _auth: TokenPayload = Depends(require_officer)) -> dict:
    """Update a verification outcome by ID."""
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        result = update_verification(db_path, outcome_id, request)
        return result.model_dump()
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": ErrorCode.CLIENT_INVALID_REQUEST.value,
                    "message": str(exc),
                }
            },
        )
    except Exception as exc:
        logger.error("Verification update failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )


@router.delete(
    "/{outcome_id}",
    summary="Delete a verification outcome",
    description="Delete a verification outcome by its ID.",
    status_code=204,
)
async def delete_outcome(outcome_id: str, _auth: TokenPayload = Depends(require_officer)) -> None:
    """Delete a verification outcome by ID."""
    db_path = _get_db_path()
    _validate_database(db_path)

    try:
        deleted = delete_verification(db_path, outcome_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ErrorCode.CLIENT_INVALID_REQUEST.value,
                        "message": f"Verification outcome '{outcome_id}' not found",
                    }
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Verification deletion failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An internal error occurred",
                }
            },
        )
