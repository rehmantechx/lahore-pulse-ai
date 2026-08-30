"""Accuracy tracking API endpoints.

Exposes prediction accuracy metrics and historical performance data.

Endpoints:
    GET /api/v1/accuracy/summary
        → Aggregated accuracy stats by horizon

    GET /api/v1/accuracy/recent
        → Recent verified predictions with actual vs predicted

    GET /api/v1/accuracy/trend
        → Accuracy trend over time (rolling window)

Design:
    - Reads from prediction_records table (populated by audit.py)
    - Auto-backfills actual values from observations when target time has passed
    - All metrics use absolute error (MAE-style), not squared error
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from ..auth import require_officer, TokenPayload
from loguru import logger

from ...core.config import get_settings

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


def _resolve_backend_root() -> Path:
    """Resolve the backend/ project root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_db_path() -> Path:
    """Get resolved database path."""
    settings = get_settings()
    db_path = settings.database_url.replace("sqlite:///", "")
    db_path_obj = Path(db_path)
    if not db_path_obj.is_absolute():
        db_path_obj = _resolve_backend_root() / db_path_obj
    return db_path_obj


# Module-level DB path (resolved once at import time)
DB_PATH = _get_db_path()


def _backfill_actuals(db_path: Path) -> int:
    """Match past predictions with actual observations.

    For each prediction whose target_time has passed and has no actual_value,
    look up the closest PM2.5 observation at or after target_time and
    fill in the actual_value and prediction_error.

    Returns:
        Number of records backfilled.
    """
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(str(db_path))
    try:
        # Find predictions that need backfilling
        pending = conn.execute(
            """SELECT prediction_id, target_time, predicted_value
               FROM prediction_records
               WHERE actual_value IS NULL
                 AND target_time < ?
               ORDER BY target_time""",
            (now,),
        ).fetchall()

        backfilled = 0
        for pred_id, target_time_str, predicted_value in pending:
            # Find the closest PM2.5 observation at or after target_time
            row = conn.execute(
                """SELECT value FROM observations
                   WHERE parameter = 'pm25'
                     AND observation_type = 'observation'
                     AND observed_at >= ?
                   ORDER BY observed_at ASC
                   LIMIT 1""",
                (target_time_str,),
            ).fetchone()

            if row is not None:
                actual_value = row[0]
                conn.execute(
                    """UPDATE prediction_records
                       SET actual_value = ?,
                           prediction_error = ABS(predicted_value - ?)
                       WHERE prediction_id = ?""",
                    (actual_value, actual_value, pred_id),
                )
                backfilled += 1

        if backfilled > 0:
            conn.commit()
            logger.info("Backfilled actuals", count=backfilled)

        return backfilled
    finally:
        conn.close()


@router.get("/summary")
async def get_accuracy_summary(
    _auth: TokenPayload = Depends(require_officer),
) -> dict:
    """Aggregated accuracy statistics by forecast horizon.

    Auto-backfills actuals before computing stats.
    Returns MAE, max error, verified count per horizon.
    """
    db_path = _get_db_path()
    _backfill_actuals(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM prediction_records"
        ).fetchone()[0]

        by_horizon = conn.execute(
            """SELECT
                 forecast_horizon,
                 COUNT(*) as total_predictions,
                 COUNT(CASE WHEN actual_value IS NOT NULL THEN 1 END) as verified_count,
                 AVG(CASE WHEN actual_value IS NOT NULL THEN prediction_error END) as avg_error,
                 MAX(CASE WHEN actual_value IS NOT NULL THEN prediction_error END) as max_error,
                 MIN(CASE WHEN actual_value IS NOT NULL THEN prediction_error END) as min_error
               FROM prediction_records
               GROUP BY forecast_horizon
               ORDER BY forecast_horizon"""
        ).fetchall()

        return {
            "total_predictions": total,
            "backfilled_this_call": True,
            "by_horizon": [
                {
                    "horizon": r[0],
                    "total_predictions": r[1],
                    "verified_count": r[2],
                    "avg_error": round(r[3], 4) if r[3] is not None else None,
                    "max_error": round(r[4], 4) if r[4] is not None else None,
                    "min_error": round(r[5], 4) if r[5] is not None else None,
                }
                for r in by_horizon
            ],
        }
    finally:
        conn.close()


@router.get("/recent")
async def get_recent_verified(
    horizon: int | None = Query(None, description="Filter by forecast horizon"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records"),
    _auth: TokenPayload = Depends(require_officer),
) -> dict:
    """Recent predictions that have been verified against actual observations.

    Returns predicted vs actual values, error, and timing info.
    """
    db_path = _get_db_path()
    _backfill_actuals(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if horizon is not None:
            rows = conn.execute(
                """SELECT prediction_id, model_version, algorithm,
                          forecast_horizon, prediction_time, target_time,
                          predicted_value, actual_value, prediction_error
                   FROM prediction_records
                   WHERE actual_value IS NOT NULL
                     AND forecast_horizon = ?
                   ORDER BY target_time DESC
                   LIMIT ?""",
                (horizon, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT prediction_id, model_version, algorithm,
                          forecast_horizon, prediction_time, target_time,
                          predicted_value, actual_value, prediction_error
                   FROM prediction_records
                   WHERE actual_value IS NOT NULL
                   ORDER BY target_time DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

        return {
            "count": len(rows),
            "predictions": [
                {
                    "prediction_id": r["prediction_id"],
                    "model_version": r["model_version"],
                    "algorithm": r["algorithm"],
                    "horizon": r["forecast_horizon"],
                    "prediction_time": r["prediction_time"],
                    "target_time": r["target_time"],
                    "predicted": r["predicted_value"],
                    "actual": r["actual_value"],
                    "error": round(r["prediction_error"], 4) if r["prediction_error"] is not None else None,
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


# ── Phase 10: Prediction Accountability ──────────────────────────


def _run_accountability_query(
    db_path: str | Path,
    horizon: int | None,
    limit: int,
    order: str = "DESC",
) -> dict:
    """Shared query logic for accountability timeline and backfill."""
    db_path_str = str(db_path)
    if horizon is not None:
        _backfill_actuals(Path(db_path_str))

    # Validate order direction to prevent injection
    safe_order = "DESC" if order.upper() == "DESC" else "ASC"

    conn = sqlite3.connect(db_path_str)
    conn.row_factory = sqlite3.Row
    try:
        if horizon is not None:
            rows = conn.execute(
                f"""
                SELECT
                    prediction_id, model_version, algorithm, forecast_horizon,
                    prediction_time, target_time,
                    predicted_value, actual_value, prediction_error,
                    data_timestamp, feature_count, freshness_hours
                FROM prediction_records
                WHERE forecast_horizon = ?
                  AND target_time <= datetime('now')
                ORDER BY target_time {safe_order}
                LIMIT ?
                """,
                (horizon, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT
                    prediction_id, model_version, algorithm, forecast_horizon,
                    prediction_time, target_time,
                    predicted_value, actual_value, prediction_error,
                    data_timestamp, feature_count, freshness_hours
                FROM prediction_records
                WHERE target_time <= datetime('now')
                ORDER BY target_time {safe_order}
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return {
            "count": len(rows),
            "horizon_filter": horizon,
            "timeline": [
                {
                    "prediction_id": r["prediction_id"],
                    "model_version": r["model_version"],
                    "algorithm": r["algorithm"],
                    "horizon": r["forecast_horizon"],
                    "prediction_time": r["prediction_time"],
                    "target_time": r["target_time"],
                    "predicted": r["predicted_value"],
                    "actual": r["actual_value"],
                    "error": round(r["prediction_error"], 4) if r["prediction_error"] is not None else None,
                    "status": "verified" if r["actual_value"] is not None else "pending",
                    "data_timestamp": r["data_timestamp"],
                    "feature_count": r["feature_count"],
                    "data_freshness_hours": (
                        round(r["freshness_hours"], 1)
                        if r["freshness_hours"] is not None
                        else None
                    ),
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


@router.get("/accountability")
async def prediction_accountability(
    horizon: int | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    _auth: TokenPayload = Depends(require_officer),
):
    """Prediction accountability timeline.

    Returns past predictions that have reached their target time,
    including whether they have been verified against observations.

    This is the core differentiator: predictions are tracked, verified,
    and their accuracy is transparently reported.
    """
    db_str = str(DB_PATH)
    conn = sqlite3.connect(db_str)
    total = conn.execute("SELECT COUNT(*) FROM prediction_records").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM prediction_records WHERE target_time > datetime('now')"
    ).fetchone()[0]
    verified = conn.execute(
        "SELECT COUNT(*) FROM prediction_records WHERE actual_value IS NOT NULL AND target_time <= datetime('now')"
    ).fetchone()[0]
    unverified = conn.execute(
        "SELECT COUNT(*) FROM prediction_records WHERE actual_value IS NULL AND target_time <= datetime('now')"
    ).fetchone()[0]
    conn.close()

    result = _run_accountability_query(DB_PATH, horizon, limit, order="DESC")

    return {
        **result,
        "summary": {
            "total_predictions": total,
            "pending": pending,
            "verified": verified,
            "awaiting_verification": unverified,
            "verification_rate": round(verified / max(total, 1) * 100, 1),
        },
    }


@router.post("/verify")
async def trigger_verification(
    _auth: TokenPayload = Depends(require_officer),
):
    """Trigger on-demand backfill of prediction actuals.

    Matches past predictions against observations that became
    available after the prediction was made.
    """
    count = _backfill_actuals(Path(str(DB_PATH)))
    return {
        "status": "completed",
        "backfilled": count,
        "message": f"Verified {count} prediction(s) against available observations.",
    }


@router.get("/horizon-comparison")
async def horizon_comparison(
    _auth: TokenPayload = Depends(require_officer),
):
    """Compare model performance across horizons.

    Returns per-horizon statistics including validation metrics,
    live accuracy, and algorithm details — telling the story of
    why different horizons use different models.
    """
    _backfill_actuals(Path(str(DB_PATH)))

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # Live accuracy per horizon
        rows = conn.execute(
            """
            SELECT
                forecast_horizon,
                COUNT(*) as total,
                SUM(CASE WHEN actual_value IS NOT NULL THEN 1 ELSE 0 END) as verified,
                AVG(CASE WHEN actual_value IS NOT NULL THEN ABS(prediction_error) END) as live_mae,
                AVG(CASE WHEN actual_value IS NOT NULL THEN prediction_error END) as live_bias,
                MAX(CASE WHEN actual_value IS NOT NULL THEN ABS(prediction_error) END) as live_max_error
            FROM prediction_records
            GROUP BY forecast_horizon
            ORDER BY forecast_horizon
            """
        ).fetchall()
    finally:
        conn.close()

    # Model metadata from constants
    model_info = {
        1: {
            "algorithm": "Ridge Regression",
            "val_mae": 4.4965,
            "val_rmse": 7.3983,
            "val_r2": 0.975,
            "why": "Short-horizon prediction is nearly linear — past PM2.5 + weather explains future PM2.5. Regularized linear model is optimal: low variance, fast inference.",
        },
        3: {
            "algorithm": "HistGradientBoosting",
            "val_mae": 10.6141,
            "val_rmse": 14.773,
            "val_r2": 0.9004,
            "why": "3-hour prediction captures non-linear weather-pollutant interactions. Tree-based model handles feature interactions that linear models miss.",
        },
        6: {
            "algorithm": "HistGradientBoosting",
            "val_mae": 14.4482,
            "val_rmse": 19.673,
            "val_r2": 0.8234,
            "why": "6-hour prediction involves weather regime changes. Gradient boosting captures complex non-linear dynamics.",
        },
        12: {
            "algorithm": "HistGradientBoosting",
            "val_mae": 16.3406,
            "val_rmse": 22.7115,
            "val_r2": 0.7649,
            "why": "12-hour prediction spans weather transitions. Tree-based model handles regime shifts better than linear models.",
        },
        24: {
            "algorithm": "Ridge Regression",
            "val_mae": 17.9661,
            "val_rmse": 25.5438,
            "val_r2": 0.7033,
            "why": "24-hour prediction reverts to seasonal/diurnal baseline. Linear model is more robust to the increased noise at long horizons.",
        },
    }

    comparison = []
    for row in rows:
        h = row["forecast_horizon"]
        info = model_info.get(h, {})
        comparison.append({
            "horizon": h,
            "algorithm": info.get("algorithm", "unknown"),
            "why": info.get("why", ""),
            "validation": {
                "val_mae": info.get("val_mae"),
                "val_rmse": info.get("val_rmse"),
                "val_r2": info.get("val_r2"),
            },
            "live": {
                "total_predictions": row["total"],
                "verified_count": row["verified"],
                "live_mae": round(row["live_mae"], 4) if row["live_mae"] is not None else None,
                "live_bias": round(row["live_bias"], 4) if row["live_bias"] is not None else None,
                "live_max_error": round(row["live_max_error"], 4) if row["live_max_error"] is not None else None,
            },
        })

    return {
        "count": len(comparison),
        "horizons": comparison,
    }
