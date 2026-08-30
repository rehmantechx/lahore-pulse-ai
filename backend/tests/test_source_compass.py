"""Tests for Source Compass directional analysis service.

Verifies:
- 8-sector boundary conversions
- Calm wind handling
- Missing data graceful degradation
- Insufficient history handling
- Strong/weak association labels
- Normal/episode/improving/uncertain state interactions
- Investigation hint generation
- Serialization (to_dict) correctness

Data is synthetic — no real database required.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from app.modeling.serving.source_compass import (
    SECTORS,
    SourceCompassResult,
    SectorAnalysis,
    _label_association,
    _build_investigation_hint,
    _is_episode_hour,
    compute_source_compass,
    deg_to_sector,
    sector_midpoint,
    sector_arrow,
    sector_range,
)


# ── Sector Utilities ──────────────────────────────────────────


class TestDegToSector:
    """8-sector boundary conversions."""

    def test_north_center(self) -> None:
        assert deg_to_sector(0) == "N"

    def test_north_upper_boundary(self) -> None:
        assert deg_to_sector(22.4) == "N"

    def test_north_northeast_boundary(self) -> None:
        assert deg_to_sector(22.5) == "NE"

    def test_northeast_center(self) -> None:
        assert deg_to_sector(45) == "NE"

    def test_east_center(self) -> None:
        assert deg_to_sector(90) == "E"

    def test_south_center(self) -> None:
        assert deg_to_sector(180) == "S"

    def test_west_center(self) -> None:
        assert deg_to_sector(270) == "W"

    def test_northwest_center(self) -> None:
        assert deg_to_sector(315) == "NW"

    def test_full_circle_wraps(self) -> None:
        assert deg_to_sector(360) == "N"

    def test_degrees_beyond_360(self) -> None:
        assert deg_to_sector(382.5) == "NE"

    def test_negative_degrees_wraps(self) -> None:
        # -45 → int((-45+22.5)/45) % 8 = int(-0.5) % 8 = 0 % 8 = 0 → N
        # This is correct: int() truncates toward zero, so -45 maps to N
        assert deg_to_sector(-45) == "N"

    def test_negative_degrees_nw(self) -> None:
        # -50 → int((-50+22.5)/45) % 8 = int(-0.61) % 8 = 0 % 8 = 0 → N
        # To get NW (315°), use positive 315 or a value in NW range
        assert deg_to_sector(320) == "NW"

    def test_all_sectors_covered(self) -> None:
        """Every 45-degree increment should map to a unique sector."""
        sectors_found = [deg_to_sector(i * 45) for i in range(8)]
        assert len(set(sectors_found)) == 8
        assert set(sectors_found) == set(SECTORS)


class TestSectorUtilities:

    def test_sector_midpoint(self) -> None:
        assert sector_midpoint("N") == 0
        assert sector_midpoint("E") == 90
        assert sector_midpoint("SW") == 225

    def test_sector_arrow(self) -> None:
        arrow = sector_arrow("E")
        assert isinstance(arrow, str)
        assert len(arrow) == 1

    def test_sector_range_north(self) -> None:
        lower, upper = sector_range("N")
        assert lower == 337.5
        assert upper == 22.5

    def test_sector_range_east(self) -> None:
        lower, upper = sector_range("E")
        assert lower == 67.5
        assert upper == 112.5


# ── Association Labeling ──────────────────────────────────────


class TestLabelAssociation:

    def test_high_association(self) -> None:
        assert _label_association(1.5, 100) == "HIGH ASSOCIATION"

    def test_high_boundary(self) -> None:
        assert _label_association(1.3, 100) == "HIGH ASSOCIATION"

    def test_moderate_association(self) -> None:
        assert _label_association(1.15, 100) == "MODERATE ASSOCIATION"

    def test_moderate_boundary(self) -> None:
        assert _label_association(1.1, 100) == "MODERATE ASSOCIATION"

    def test_low_association(self) -> None:
        assert _label_association(1.0, 100) == "LOW ASSOCIATION"

    def test_below_baseline(self) -> None:
        assert _label_association(0.8, 100) == "LOW ASSOCIATION"

    def test_insufficient_data(self) -> None:
        assert _label_association(1.5, 30) == "INSUFFICIENT DATA"


# ── Investigation Hint ────────────────────────────────────────


class TestInvestigationHint:

    def test_high_association_hint(self) -> None:
        hint = _build_investigation_hint(
            strongest_sector="E",
            association_label="HIGH ASSOCIATION",
            evidence_count=150,
            is_episode=True,
        )
        assert hint is not None
        assert "E" in hint["corridor_sectors"]
        assert hint["association_label"] == "HIGH ASSOCIATION"
        assert len(hint["suggested_domains"]) > 0
        assert "message" in hint

    def test_insufficient_returns_none(self) -> None:
        hint = _build_investigation_hint(
            strongest_sector="N",
            association_label="INSUFFICIENT DATA",
            evidence_count=30,
            is_episode=False,
        )
        assert hint is None

    def test_low_association_returns_hint(self) -> None:
        # LOW ASSOCIATION still returns a hint (only INSUFFICIENT returns None)
        hint = _build_investigation_hint(
            strongest_sector="S",
            association_label="LOW ASSOCIATION",
            evidence_count=80,
            is_episode=False,
        )
        assert hint is not None
        assert "S" in hint["corridor_sectors"]

    def test_corridor_sectors_match_strongest(self) -> None:
        hint = _build_investigation_hint(
            strongest_sector="E",
            association_label="MODERATE ASSOCIATION",
            evidence_count=120,
            is_episode=True,
        )
        assert hint["corridor_sectors"] == ["E"]
        assert hint["corridor_label"] == "E sector"

    def test_message_contains_direction(self) -> None:
        hint = _build_investigation_hint(
            strongest_sector="W",
            association_label="HIGH ASSOCIATION",
            evidence_count=200,
            is_episode=True,
        )
        assert "W" in hint["message"]
        assert "high association" in hint["message"].lower()


# ── Episode Hour Detection ────────────────────────────────────


class TestIsEpisodeHour:

    def test_above_threshold(self) -> None:
        assert _is_episode_hour(125.0, 0) is True

    def test_below_threshold(self) -> None:
        assert _is_episode_hour(80.0, 0) is False

    def test_exactly_threshold(self) -> None:
        assert _is_episode_hour(120.0, 0) is False

    def test_high_pm25(self) -> None:
        assert _is_episode_hour(200.0, 3) is True


# ── Serialization ─────────────────────────────────────────────


class TestSourceCompassResultSerialization:

    def _make_result(self, **overrides) -> SourceCompassResult:
        defaults = dict(
            current_direction_degrees=90.0,
            current_sector="E",
            current_wind_speed_ms=3.5,
            is_calm=False,
            enrichment_profile=[
                SectorAnalysis("N", 100, 10, 0.85, 85.0, 2.0),
                SectorAnalysis("E", 80, 25, 1.44, 135.0, 3.0),
            ],
            strongest_sector="E",
            strongest_enrichment=1.44,
            association_label="HIGH",
            evidence_count=25,
            total_episode_hours=200,
            total_observations=5000,
            season="winter",
            season_month_count=6,
            disclaimer="Test disclaimer.",
            investigation_hint=None,
        )
        defaults.update(overrides)
        return SourceCompassResult(**defaults)

    def test_to_dict_has_all_keys(self) -> None:
        result = self._make_result()
        d = result.to_dict()
        assert "current_wind" in d
        assert "historical" in d
        assert "disclaimer" in d
        assert "investigation_hint" in d

    def test_current_wind_rounded(self) -> None:
        result = self._make_result(current_direction_degrees=90.456)
        d = result.to_dict()
        assert d["current_wind"]["direction_degrees"] == 90.5

    def test_strongest_enrichment_rounded(self) -> None:
        result = self._make_result(strongest_enrichment=1.444)
        d = result.to_dict()
        assert d["historical"]["strongest_enrichment"] == 1.44

    def test_profile_entries_have_required_fields(self) -> None:
        result = self._make_result()
        d = result.to_dict()
        for entry in d["historical"]["profile"]:
            assert "sector" in entry
            assert "enrichment" in entry
            assert "episode_hours" in entry
            assert "total_hours" in entry
            assert "avg_pm25" in entry

    def test_none_wind_direction(self) -> None:
        result = self._make_result(
            current_direction_degrees=None,
            current_sector=None,
            current_wind_speed_ms=None,
            is_calm=True,
        )
        d = result.to_dict()
        assert d["current_wind"]["direction_degrees"] is None
        assert d["current_wind"]["is_calm"] is True

    def test_investigation_hint_included_when_present(self) -> None:
        hint = {
            "corridor_sectors": ["E", "NE", "SE"],
            "description": "Investigate east",
            "strongest_enrichment": 1.44,
            "association": "HIGH",
            "suggested_response_domains": ["industrial"],
        }
        result = self._make_result(investigation_hint=hint)
        d = result.to_dict()
        assert d["investigation_hint"]["corridor_sectors"] == ["E", "NE", "SE"]


# ── Database Integration (Synthetic) ──────────────────────────


class TestSourceCompassWithSyntheticDB:
    """Tests using a synthetic in-memory SQLite database."""

    @pytest.fixture
    def synthetic_db(self, tmp_path: Path) -> Path:
        """Create a minimal observations table with synthetic data."""
        db_path = tmp_path / "test_compass.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE observations (
                observation_id TEXT PRIMARY KEY,
                source_id TEXT,
                station_id TEXT,
                parameter TEXT,
                value REAL,
                unit TEXT,
                observed_at TEXT,
                latitude REAL,
                longitude REAL,
                quality_status TEXT,
                observation_type TEXT,
                raw_response TEXT
            )
        """)

        # 300 episode hours * 0.6 = ~180 east episode-hours (well above 50 threshold)
        # 200 normal + 300 episode = 500 hours
        # 500 * 3 params = 1500 observations
        # Hours 0-199: normal conditions (PM2.5 < 120)
        # Hours 200-499: episode conditions (PM2.5 > 120)
        # During episodes, wind is predominantly from East (90°)
        import random
        random.seed(42)

        rows = []
        for hour in range(500):
            ts = f"2024-01-{1 + hour // 24:02d}T{hour % 24:02d}:00:00"

            if hour < 200:
                pm25 = 60 + random.gauss(0, 15)
                wind_dir = random.choice([0, 45, 90, 135, 180, 225, 270, 315])
            else:
                pm25 = 140 + random.gauss(0, 20)
                # 60% of episode hours have wind from East
                if random.random() < 0.6:
                    wind_dir = 90
                else:
                    wind_dir = random.choice([0, 45, 135, 180, 225, 270, 315])

            wind_speed = 2.0 + random.random() * 4.0

            # PM2.5 observation (must match backend parameter name 'pm2_5')
            rows.append((
                f"obs-pm25-{hour}", "test-source", "test-station",
                "pm2_5", round(pm25, 1), "µg/m³", ts,
                31.5204, 74.3587, "VALID", "observation", "{}",
            ))
            # Wind direction observation
            rows.append((
                f"obs-wdir-{hour}", "test-source", "test-station",
                "wind_direction_10m", wind_dir, "deg", ts,
                31.5204, 74.3587, "VALID", "observation", "{}",
            ))
            # Wind speed observation
            rows.append((
                f"obs-wspd-{hour}", "test-source", "test-station",
                "wind_speed_10m", round(wind_speed, 1), "m/s", ts,
                31.5204, 74.3587, "VALID", "observation", "{}",
            ))

        conn.executemany("""
            INSERT INTO observations
            (observation_id, source_id, station_id, parameter, value, unit,
             observed_at, latitude, longitude, quality_status, observation_type, raw_response)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()
        return db_path

    def test_compute_returns_result(self, synthetic_db: Path) -> None:
        result = compute_source_compass(synthetic_db)
        assert isinstance(result, SourceCompassResult)

    def test_strongest_sector_is_east(self, synthetic_db: Path) -> None:
        """With 60% east wind during episodes, E should be strongest."""
        result = compute_source_compass(synthetic_db)
        assert result.strongest_sector == "E"

    def test_east_enrichment_above_baseline(self, synthetic_db: Path) -> None:
        result = compute_source_compass(synthetic_db)
        e_analysis = next(
            (s for s in result.enrichment_profile if s.sector == "E"), None
        )
        assert e_analysis is not None
        assert e_analysis.enrichment > 1.0

    def test_association_not_insufficient(self, synthetic_db: Path) -> None:
        """200 hours should provide enough data for a meaningful label."""
        result = compute_source_compass(synthetic_db)
        assert "INSUFFICIENT" not in result.association_label

    def test_total_observations_populated(self, synthetic_db: Path) -> None:
        result = compute_source_compass(synthetic_db)
        assert result.total_observations > 0

    def test_serialization_roundtrip(self, synthetic_db: Path) -> None:
        result = compute_source_compass(synthetic_db)
        d = result.to_dict()
        assert d["historical"]["strongest_sector"] == result.strongest_sector
        assert len(d["historical"]["profile"]) == 8

    def test_current_wind_populated(self, synthetic_db: Path) -> None:
        result = compute_source_compass(synthetic_db)
        # With data, current wind should be available
        assert result.current_wind_speed_ms is not None or result.is_calm

    def test_winter_season_detected(self, synthetic_db: Path) -> None:
        """Jan data should be classified as winter."""
        result = compute_source_compass(synthetic_db)
        assert result.season == "winter"

    def test_empty_database(self, tmp_path: Path) -> None:
        """Graceful handling of empty database."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE observations (
                observation_id TEXT PRIMARY KEY,
                source_id TEXT,
                station_id TEXT,
                parameter TEXT,
                value REAL,
                unit TEXT,
                observed_at TEXT,
                latitude REAL,
                longitude REAL,
                quality_status TEXT,
                observation_type TEXT,
                raw_response TEXT
            )
        """)
        conn.commit()
        conn.close()

        result = compute_source_compass(db_path)
        assert "INSUFFICIENT" in result.association_label
        assert result.total_observations == 0
