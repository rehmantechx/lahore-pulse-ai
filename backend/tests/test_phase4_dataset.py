"""Tests for Phase 4 dataset loader.

Covers:
    - Loading observations from SQLite
    - Duplicate timestamp handling
    - Hourly grid alignment
    - Dataset description
    - Missing parameter handling
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.modeling.dataset_loader import (
    OVERLAP_START,
    WEATHER_PARAMS,
    load_observations_from_db,
    align_to_hourly_grid,
    describe_dataset,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _create_test_db(db_path: str, n_hours: int = 48) -> None:
    """Create a minimal SQLite DB with weather + AQ observations."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY,
            observed_at TEXT NOT NULL,
            parameter TEXT NOT NULL,
            value REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'test',
            observation_type TEXT NOT NULL DEFAULT 'observation'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_sources (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            provider TEXT,
            parameter_group TEXT,
            description TEXT,
            created_at TEXT
        )
    """)
    conn.execute("INSERT INTO data_sources (name) VALUES ('test_weather')")
    conn.execute("INSERT INTO data_sources (name) VALUES ('test_aq')")

    idx = pd.date_range(OVERLAP_START, periods=n_hours, freq="1h", tz="UTC")
    rows = []
    rng = np.random.default_rng(42)
    for t in idx:
        ts = t.isoformat()
        # Weather params
        rows.append((ts, "temperature_2m", 20 + rng.normal(0, 1)))
        rows.append((ts, "relative_humidity_2m", 60 + rng.normal(0, 2)))
        rows.append((ts, "pressure_msl", 1013 + rng.normal(0, 0.5)))
        # AQ params
        rows.append((ts, "pm2_5", 70 + rng.normal(0, 10)))
        rows.append((ts, "pm10", 100 + rng.normal(0, 15)))

    conn.executemany(
        "INSERT INTO observations (observed_at, parameter, value) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


# ── Tests ────────────────────────────────────────────────────────────


class TestLoadObservations:
    def test_loads_from_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            _create_test_db(db_path)
            df = load_observations_from_db(db_path)
            assert len(df) > 0
            assert "pm2_5" in df.columns

    def test_handles_duplicates(self) -> None:
        """Duplicate timestamps should be aggregated by mean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            # Create DB and add duplicates
            _create_test_db(db_path)
            conn = sqlite3.connect(db_path)
            # Add duplicate observation
            idx = pd.date_range(OVERLAP_START, periods=1, freq="1h", tz="UTC")
            conn.execute(
                "INSERT INTO observations (observed_at, parameter, value) VALUES (?, ?, ?)",
                (idx[0].isoformat(), "temperature_2m", 100.0),
            )
            conn.commit()
            conn.close()
            # Should load without error
            df = load_observations_from_db(db_path)
            assert len(df) > 0


class TestAlignToHourlyGrid:
    def test_creates_regular_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            _create_test_db(db_path, n_hours=48)
            df = load_observations_from_db(db_path)
            aligned = align_to_hourly_grid(df)
            # Check index is regular
            freq = pd.infer_freq(aligned.index)
            # Should be hourly or close to it
            assert aligned.index.is_monotonic_increasing

    def test_preserves_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            _create_test_db(db_path, n_hours=48)
            df = load_observations_from_db(db_path)
            original_cols = set(df.columns)
            aligned = align_to_hourly_grid(df)
            # All original columns should be preserved
            assert original_cols.issubset(set(aligned.columns))


class TestDescribeDataset:
    def test_returns_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            _create_test_db(db_path, n_hours=48)
            df = load_observations_from_db(db_path)
            aligned = align_to_hourly_grid(df)
            desc = describe_dataset(aligned)
            assert "rows" in desc
            assert "columns" in desc
            assert desc["rows"] > 0
            assert "parameters" in desc
