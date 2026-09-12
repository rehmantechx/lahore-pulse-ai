"""Prediction audit trail — logs every prediction to the database.

Every prediction produced by the serving layer must be traceable.
This module writes prediction records to SQLite so that:
    - Every prediction has a unique ID
    - Model version and horizon are recorded
    - Input data freshness is logged
    - Feature completeness is tracked
    - Actual vs predicted values can be compared later

Design:
    - Appends a `prediction_records` table to the existing schema
    - Uses the same Database class for consistency
    - Writes are synchronous (appropriate for SQLite single-writer)
    - No external dependencies (no Redis, Kafka, etc.)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from ...core.db import get_db_connection, is_cloud_db

# ── Schema Extension ──────────────────────────────────────────────

PREDICTION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prediction_records (
    prediction_id   TEXT PRIMARY KEY,
    model_version   TEXT NOT NULL,
    algorithm       TEXT NOT NULL,
    forecast_horizon INTEGER NOT NULL,
    prediction_time TEXT NOT NULL,
    target_time     TEXT NOT NULL,
    predicted_value REAL NOT NULL,
    unit            TEXT NOT NULL DEFAULT 'ug/m3',
    data_timestamp  TEXT,
    freshness_hours REAL,
    feature_count   INTEGER,
    missing_features TEXT,
    warnings        TEXT,
    actual_value    REAL,
    prediction_error REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pred_horizon ON prediction_records(forecast_horizon);
CREATE INDEX IF NOT EXISTS idx_pred_model ON prediction_records(model_version);
CREATE INDEX IF NOT EXISTS idx_pred_time ON prediction_records(prediction_time);
CREATE INDEX IF NOT EXISTS idx_pred_target ON prediction_records(target_time);
"""


def ensure_prediction_schema(db_path: str | Path) -> None:
    """Ensure the prediction_records table exists in the database.

    Idempotent — safe to call multiple times.
    """
    conn = get_db_connection(db_path=db_path)
    try:
        conn.executescript(PREDICTION_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    logger.debug("Prediction schema ensured", path=str(db_path))


# ── Record Storage ────────────────────────────────────────────────


def record_prediction(
    db_path: str | Path,
    model_version: str,
    algorithm: str,
    forecast_horizon: int,
    prediction_time: datetime,
    target_time: datetime,
    predicted_value: float,
    data_timestamp: datetime | None = None,
    freshness_hours: float | None = None,
    feature_count: int | None = None,
    missing_features: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Write a prediction record to the audit trail.

    Args:
        db_path: Path to SQLite database.
        model_version: Model version used.
        algorithm: Algorithm name (ridge, hgb, etc.).
        forecast_horizon: Forecast horizon in hours.
        prediction_time: When the prediction was made.
        target_time: What time the prediction is for.
        predicted_value: The predicted PM2.5 value.
        data_timestamp: Timestamp of the most recent observation used.
        freshness_hours: Hours between data and prediction time.
        feature_count: Number of features used.
        missing_features: Features that were missing/NaN.
        warnings: Any warnings from feature assembly.

    Returns:
        The prediction_id (UUID).
    """
    prediction_id = str(uuid.uuid4())

    # Ensure schema exists
    ensure_prediction_schema(db_path)

    conn = get_db_connection(db_path=db_path)
    try:
        conn.execute(
            """INSERT INTO prediction_records
               (prediction_id, model_version, algorithm, forecast_horizon,
                prediction_time, target_time, predicted_value, unit,
                data_timestamp, freshness_hours, feature_count,
                missing_features, warnings)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                prediction_id,
                model_version,
                algorithm,
                forecast_horizon,
                prediction_time.isoformat(),
                target_time.isoformat(),
                predicted_value,
                "ug/m3",
                data_timestamp.isoformat() if data_timestamp else None,
                freshness_hours,
                feature_count,
                json.dumps(missing_features) if missing_features else None,
                json.dumps(warnings) if warnings else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Prediction recorded",
        prediction_id=prediction_id,
        model_version=model_version,
        horizon=forecast_horizon,
        predicted_value=round(predicted_value, 2),
    )
    return prediction_id


def record_actual(
    db_path: str | Path,
    prediction_id: str,
    actual_value: float,
) -> None:
    """Update a prediction record with the actual (observed) value.

    Called later when the actual PM2.5 observation becomes available.

    Args:
        db_path: Path to SQLite database.
        prediction_id: The prediction to update.
        actual_value: The observed PM2.5 value.
    """
    conn = get_db_connection(db_path=db_path)
    try:
        error = abs(actual_value)  # placeholder; actual calc below
        conn.execute(
            """UPDATE prediction_records
               SET actual_value = ?,
                   prediction_error = ABS(predicted_value - ?)
               WHERE prediction_id = ?""",
            (actual_value, actual_value, prediction_id),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Actual value recorded",
        prediction_id=prediction_id,
        actual_value=round(actual_value, 2),
    )


def get_recent_predictions(
    db_path: str | Path,
    horizon: int | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve recent prediction records.

    Args:
        db_path: Path to SQLite database.
        horizon: Optional filter by forecast horizon.
        limit: Maximum records to return.

    Returns:
        List of prediction record dicts.
    """
    conn = get_db_connection(row_factory=sqlite3.Row, db_path=db_path)
    try:
        if horizon is not None:
            rows = conn.execute(
                """SELECT * FROM prediction_records
                   WHERE forecast_horizon = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (horizon, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM prediction_records
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_predictions(db_path: str | Path) -> dict[str, Any]:
    """Count prediction records with summary statistics.

    Returns:
        Dict with total count, counts by horizon, and avg prediction error.
    """
    conn = get_db_connection(db_path=db_path)
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM prediction_records"
        ).fetchone()[0]

        by_horizon = conn.execute(
            """SELECT forecast_horizon, COUNT(*) as count
               FROM prediction_records
               GROUP BY forecast_horizon"""
        ).fetchall()

        error_stats = conn.execute(
            """SELECT forecast_horizon,
                      AVG(prediction_error) as avg_error,
                      MAX(prediction_error) as max_error,
                      COUNT(CASE WHEN actual_value IS NOT NULL THEN 1 END) as verified_count
               FROM prediction_records
               WHERE actual_value IS NOT NULL
               GROUP BY forecast_horizon"""
        ).fetchall()

        return {
            "total_predictions": total,
            "by_horizon": [
                {"horizon": r[0], "count": r[1]} for r in by_horizon
            ],
            "error_stats": [
                {
                    "horizon": r[0],
                    "avg_error": round(r[1], 4) if r[1] else None,
                    "max_error": round(r[2], 4) if r[2] else None,
                    "verified_count": r[3],
                }
                for r in error_stats
            ],
        }
    finally:
        conn.close()
