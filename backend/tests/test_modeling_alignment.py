"""Tests for temporal alignment.

Verifies that observations are correctly aligned to a regular hourly
UTC grid and that gap-filling behaves as expected.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.modeling.alignment import (
    align_to_hourly_grid,
    compute_alignment_stats,
    observations_to_dataframe,
)


class TestObservationsToDataframe:
    """Tests for observations_to_dataframe()."""

    def test_basic_pivot(self) -> None:
        rows = [
            {"observed_at": "2024-01-01T00:00:00Z", "parameter": "temperature_2m", "value": 10.0},
            {"observed_at": "2024-01-01T00:00:00Z", "parameter": "humidity", "value": 60.0},
            {"observed_at": "2024-01-01T01:00:00Z", "parameter": "temperature_2m", "value": 11.0},
            {"observed_at": "2024-01-01T01:00:00Z", "parameter": "humidity", "value": 58.0},
        ]
        df = observations_to_dataframe(rows)
        assert "temperature_2m" in df.columns
        assert "humidity" in df.columns
        assert len(df) == 2

    def test_empty_input(self) -> None:
        df = observations_to_dataframe([])
        assert df.empty

    def test_missing_observed_at(self) -> None:
        rows = [{"parameter": "temperature_2m", "value": 10.0}]
        with pytest.raises(ValueError, match="observed_at"):
            observations_to_dataframe(rows)

    def test_utc_index(self) -> None:
        rows = [
            {"observed_at": "2024-01-01T00:00:00Z", "parameter": "temp", "value": 10.0},
        ]
        df = observations_to_dataframe(rows)
        assert df.index.tz is not None


class TestAlignToHourlyGrid:
    """Tests for align_to_hourly_grid()."""

    def test_creates_complete_grid(self) -> None:
        idx = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
        df = pd.DataFrame({"temp": [10.0, 11.0, 12.0, 13.0, 14.0]}, index=idx)
        df.index.name = "time"
        result = align_to_hourly_grid(df)
        assert len(result) == 5

    def test_fills_short_gaps(self) -> None:
        # Create data with a 2-hour gap
        idx = pd.to_datetime(
            ["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 04:00"],
            utc=True,
        )
        df = pd.DataFrame({"temp": [10.0, 11.0, 14.0]}, index=idx)
        df.index.name = "time"
        from app.modeling.config import AlignmentConfig

        cfg = AlignmentConfig(max_gap_hours=3)
        result = align_to_hourly_grid(df, cfg)
        assert len(result) == 5
        # Gap should be filled via forward-fill
        assert not result["temp"].isna().all()

    def test_preserves_values(self) -> None:
        idx = pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC")
        values = list(range(10))
        df = pd.DataFrame({"temp": values}, index=idx)
        df.index.name = "time"
        result = align_to_hourly_grid(df)
        for i, v in enumerate(values):
            assert result["temp"].iloc[i] == pytest.approx(v)

    def test_empty_input(self) -> None:
        df = pd.DataFrame()
        result = align_to_hourly_grid(df)
        assert result.empty


class TestAlignmentStats:
    """Tests for compute_alignment_stats()."""

    def test_basic_stats(self) -> None:
        idx = pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC")
        original = pd.DataFrame({"temp": range(10)}, index=idx)
        original.index.name = "time"
        aligned = align_to_hourly_grid(original)
        stats = compute_alignment_stats(original, aligned)
        assert stats["original_rows"] == 10
        assert stats["aligned_rows"] == 10

    def test_expansion_ratio(self) -> None:
        idx = pd.to_datetime(
            ["2024-01-01 00:00", "2024-01-01 03:00"],
            utc=True,
        )
        original = pd.DataFrame({"temp": [10.0, 13.0]}, index=idx)
        original.index.name = "time"
        aligned = align_to_hourly_grid(original)
        stats = compute_alignment_stats(original, aligned)
        assert stats["expansion_ratio"] == 2.0  # 4 rows / 2 rows
