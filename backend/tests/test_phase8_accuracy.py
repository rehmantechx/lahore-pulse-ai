"""Tests for Phase 8 accuracy tracking and stations endpoints.

Tests cover:
    - Accuracy summary endpoint
    - Recent verified predictions endpoint
    - Stations listing endpoint
    - Auto-backfill logic
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.auth import TokenPayload, require_officer
from app.main import create_app


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary database with prediction_records and observations tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))

    # Create prediction_records table
    conn.executescript("""
        CREATE TABLE prediction_records (
            prediction_id TEXT PRIMARY KEY,
            model_version TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            forecast_horizon INTEGER NOT NULL,
            prediction_time TEXT NOT NULL,
            target_time TEXT NOT NULL,
            predicted_value REAL NOT NULL,
            unit TEXT NOT NULL DEFAULT 'ug/m3',
            data_timestamp TEXT,
            freshness_hours REAL,
            feature_count INTEGER,
            missing_features TEXT,
            warnings TEXT,
            actual_value REAL,
            prediction_error REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE observations (
            observation_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            station_id TEXT,
            parameter TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            observed_at TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            quality_status TEXT DEFAULT 'valid',
            observation_type TEXT DEFAULT 'observation',
            raw_response TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE stations (
            station_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            name TEXT,
            latitude REAL,
            longitude REAL,
            active INTEGER DEFAULT 1,
            metadata TEXT
        );
    """)

    # Insert test data
    now = datetime.now(UTC)
    six_hours_ago = (now - timedelta(hours=6)).isoformat()
    two_hours_ago = (now - timedelta(hours=2)).isoformat()
    four_hours_ago = (now - timedelta(hours=4)).isoformat()

    # Insert a prediction with no actual yet (target in future)
    conn.execute(
        """INSERT INTO prediction_records
           (prediction_id, model_version, algorithm, forecast_horizon,
            prediction_time, target_time, predicted_value, actual_value, prediction_error)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "pred-001",
            "v1.0.0_h1_ridge",
            "ridge",
            1,
            six_hours_ago,
            two_hours_ago,
            42.5,
            None,
            None,
        ),
    )

    # Insert a prediction whose target has passed — should be backfilled
    conn.execute(
        """INSERT INTO prediction_records
           (prediction_id, model_version, algorithm, forecast_horizon,
            prediction_time, target_time, predicted_value, actual_value, prediction_error)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "pred-002",
            "v1.0.0_h6_hgb",
            "hgb",
            6,
            (now - timedelta(hours=12)).isoformat(),
            six_hours_ago,
            35.0,
            None,
            None,
        ),
    )

    # Insert an observation that matches pred-002's target time
    conn.execute(
        """INSERT INTO observations
           (observation_id, source_id, parameter, value, observed_at, observation_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("obs-001", "openmeteo", "pm25", 38.2, six_hours_ago, "observation"),
    )

    # Insert a station
    conn.execute(
        """INSERT INTO stations
           (station_id, source_id, name, latitude, longitude, active)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("stn-001", "aqicn", "Lahore US Consulate", 31.5204, 74.3587, 1),
    )

    # Insert a station PM2.5 observation
    conn.execute(
        """INSERT INTO observations
           (observation_id, source_id, station_id, parameter, value, observed_at, observation_type)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("obs-002", "aqicn", "stn-001", "pm25", 45.0, two_hours_ago, "observation"),
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def client(test_db):
    """Create a test client with patched database path."""
    with patch("app.api.v1.accuracy._get_db_path", return_value=test_db), \
         patch("app.api.v1.stations._get_db_path", return_value=test_db):
        app = create_app(settings=None)

        # Bypass auth — consistent with conftest.py pattern
        def _mock_require_officer():
            return TokenPayload(sub="test-officer", role="officer", exp=9999999999.0)

        app.dependency_overrides[require_officer] = _mock_require_officer
        with TestClient(app) as c:
            yield c


class TestAccuracySummary:
    def test_returns_summary(self, client):
        response = client.get("/api/v1/accuracy/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_predictions" in data
        assert "by_horizon" in data
        assert data["total_predictions"] >= 1

    def test_backfills_actuals(self, client):
        """The summary endpoint should auto-backfill actuals."""
        response = client.get("/api/v1/accuracy/summary")
        data = response.json()
        # pred-002 should have been backfilled
        h6 = [h for h in data["by_horizon"] if h["horizon"] == 6]
        if h6:
            assert h6[0]["verified_count"] >= 1


class TestRecentVerified:
    def test_returns_verified(self, client):
        response = client.get("/api/v1/accuracy/recent?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "count" in data

    def test_filter_by_horizon(self, client):
        response = client.get("/api/v1/accuracy/recent?horizon=6")
        assert response.status_code == 200
        data = response.json()
        for pred in data["predictions"]:
            assert pred["horizon"] == 6


class TestStations:
    def test_list_stations(self, client):
        response = client.get("/api/v1/stations")
        assert response.status_code == 200
        data = response.json()
        assert "stations" in data
        assert "count" in data
        assert data["count"] >= 1

    def test_filter_by_source(self, client):
        response = client.get("/api/v1/stations?source=aqicn")
        assert response.status_code == 200
        data = response.json()
        for s in data["stations"]:
            assert s["source_id"] == "aqicn"

    def test_station_has_location(self, client):
        response = client.get("/api/v1/stations")
        data = response.json()
        for s in data["stations"]:
            assert "latitude" in s
            assert "longitude" in s
            assert s["latitude"] is not None
            assert s["longitude"] is not None


class TestStationHistory:
    def test_returns_history(self, client):
        response = client.get("/api/v1/stations/history?hours=48")
        assert response.status_code == 200
        data = response.json()
        assert "observations" in data
        assert "count" in data
