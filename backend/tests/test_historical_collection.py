"""Integration tests for Phase 3 historical data collection.

Tests the full pipeline: collection → persistence → coverage → quality gates.

These tests make real HTTP calls to Open-Meteo APIs (free tier).
They use a temporary database that is cleaned up after each test.
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.core.config import Settings
from app.infrastructure.database import Database
from app.modeling.coverage import CoverageAnalyzer
from app.modeling.historical_collector import (
    AQ_CAMS_GLOBAL_START,
    DEFAULT_AQ_VARIABLES,
    DEFAULT_WEATHER_VARIABLES,
    ChunkResult,
    CollectionReport,
    HistoricalCollector,
    generate_chunks,
)
from app.modeling.manifest import ManifestBuilder
from app.modeling.quality_gates import GateThresholds, QualityGateReport, QualityGates


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    """Create application settings."""
    return Settings()


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_lahore_pulse.db")
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def collector(settings: Settings, temp_db: Database) -> HistoricalCollector:
    """Create a HistoricalCollector with temporary database."""
    return HistoricalCollector(settings, temp_db, chunk_days=7)


# ── Chunk Generator Tests ─────────────────────────────────────────────


class TestChunkGenerator:
    """Tests for the chunk generation logic."""

    def test_single_chunk(self) -> None:
        """A small range fits in one chunk."""
        chunks = generate_chunks(date(2024, 1, 1), date(2024, 1, 7), chunk_days=30)
        assert len(chunks) == 1
        assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 7))

    def test_exact_chunk_boundary(self) -> None:
        """Range exactly equal to chunk size."""
        chunks = generate_chunks(date(2024, 1, 1), date(2024, 1, 30), chunk_days=30)
        assert len(chunks) == 1
        assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 30))

    def test_multiple_chunks(self) -> None:
        """Range spanning multiple chunks."""
        chunks = generate_chunks(date(2024, 1, 1), date(2024, 2, 28), chunk_days=30)
        assert len(chunks) == 2
        assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 30))
        assert chunks[1] == (date(2024, 1, 31), date(2024, 2, 28))

    def test_small_chunks(self) -> None:
        """Very small chunk size creates many chunks."""
        chunks = generate_chunks(date(2024, 1, 1), date(2024, 1, 10), chunk_days=3)
        assert len(chunks) == 4  # 3+3+3+1
        assert chunks[-1] == (date(2024, 1, 10), date(2024, 1, 10))

    def test_single_day(self) -> None:
        """Single-day range."""
        chunks = generate_chunks(date(2024, 6, 15), date(2024, 6, 15), chunk_days=30)
        assert len(chunks) == 1
        assert chunks[0] == (date(2024, 6, 15), date(2024, 6, 15))

    def test_empty_range(self) -> None:
        """Start after end returns empty."""
        chunks = generate_chunks(date(2024, 2, 1), date(2024, 1, 1), chunk_days=30)
        assert len(chunks) == 0

    def test_leap_year(self) -> None:
        """Feb 29 in leap year is handled."""
        chunks = generate_chunks(date(2024, 2, 28), date(2024, 3, 1), chunk_days=2)
        assert len(chunks) == 2
        assert chunks[0] == (date(2024, 2, 28), date(2024, 2, 29))
        assert chunks[1] == (date(2024, 3, 1), date(2024, 3, 1))


# ── CollectionReport Tests ────────────────────────────────────────────


class TestCollectionReport:
    """Tests for CollectionReport metrics."""

    def test_success_rate_empty(self) -> None:
        report = CollectionReport(
            run_id="test",
            data_type="weather",
            provider_model="ecmwf_ifs",
            start_date="2024-01-01",
            end_date="2024-01-30",
            chunk_days=30,
        )
        assert report.success_rate == 0.0

    def test_success_rate_partial(self) -> None:
        report = CollectionReport(
            run_id="test",
            data_type="weather",
            provider_model="ecmwf_ifs",
            start_date="2024-01-01",
            end_date="2024-01-30",
            chunk_days=10,
            total_chunks=3,
            completed_chunks=2,
            failed_chunks=1,
        )
        assert abs(report.success_rate - 2 / 3) < 1e-6

    def test_persistence_rate(self) -> None:
        report = CollectionReport(
            run_id="test",
            data_type="weather",
            provider_model="ecmwf_ifs",
            start_date="2024-01-01",
            end_date="2024-01-30",
            chunk_days=30,
            total_observations_fetched=1000,
            total_observations_persisted=950,
        )
        assert abs(report.overall_persistence_rate - 0.95) < 1e-6

    def test_to_dict(self) -> None:
        report = CollectionReport(
            run_id="test_run",
            data_type="aq",
            provider_model="cams_global",
            start_date="2023-01-01",
            end_date="2023-12-31",
            chunk_days=30,
            total_chunks=12,
            completed_chunks=11,
            failed_chunks=1,
        )
        d = report.to_dict()
        assert d["run_id"] == "test_run"
        assert d["data_type"] == "aq"
        assert d["total_chunks"] == 12
        assert d["success_rate"] == pytest.approx(11 / 12)


# ── ChunkResult Tests ─────────────────────────────────────────────────


class TestChunkResult:
    """Tests for ChunkResult data class."""

    def test_success_chunk(self) -> None:
        result = ChunkResult(
            chunk_id="0000",
            start_date="2024-01-01",
            end_date="2024-01-07",
            status="success",
            observations_fetched=1000,
            observations_persisted=980,
            observations_skipped=20,
        )
        assert result.status == "success"
        assert result.observations_persisted == 980

    def test_failed_chunk(self) -> None:
        result = ChunkResult(
            chunk_id="0001",
            start_date="2024-01-08",
            end_date="2024-01-14",
            status="failed",
            error_message="Connection timeout",
        )
        assert result.status == "failed"
        assert result.error_message == "Connection timeout"


# ── Real API Collection Tests ─────────────────────────────────────────


class TestRealWeatherCollection:
    """Tests that make real HTTP calls to Open-Meteo Weather API.

    These verify the full pipeline: fetch → parse → validate → persist.
    """

    @pytest.mark.slow
    def test_collect_7_day_weather(self, collector: HistoricalCollector) -> None:
        """Collect 7 days of weather data and verify persistence."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        report = collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m", "relative_humidity_2m"],
            model="ecmwf_ifs",
            run_id="test_weather_7day",
        )

        assert report.failed_chunks == 0, f"Failed chunks: {report.errors}"
        assert report.total_observations_persisted > 0
        # 7 days × 24 hours × 2 variables = 336 expected
        assert report.total_observations_persisted >= 300
        assert report.total_observations_persisted <= 336

    @pytest.mark.slow
    def test_collect_weather_idempotent(
        self,
        collector: HistoricalCollector,
        temp_db: Database,
    ) -> None:
        """Collecting the same range twice doesn't create duplicates."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        # First collection
        report1 = collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_idempotent_1",
        )
        count1 = temp_db.table_row_count("observations")

        # Second collection (same range, different run_id)
        report2 = collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_idempotent_2",
        )
        count2 = temp_db.table_row_count("observations")

        # The second collection should not significantly increase the count
        # (INSERT OR IGNORE handles duplicates via unique constraint)
        # Allow small tolerance for timing variations
        assert count2 <= count1 + report2.total_observations_persisted
        # But the key property: no duplicates
        dup_check = temp_db.fetch_one(
            """SELECT COUNT(*) as cnt FROM (
                SELECT source_id, station_id, parameter, observed_at,
                       COUNT(*) as dupes
                FROM observations
                GROUP BY source_id, station_id, parameter, observed_at
                HAVING dupes > 1
            )"""
        )
        assert dup_check["cnt"] == 0


class TestRealAQCollection:
    """Tests that make real HTTP calls to Open-Meteo AQ API."""

    @pytest.mark.slow
    def test_collect_7_day_aq(self, collector: HistoricalCollector) -> None:
        """Collect 7 days of AQ data from CAMS Global."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        report = collector.collect_aq(
            start=start,
            end=end,
            variables=["pm2_5", "pm10"],
            run_id="test_aq_7day",
        )

        assert report.total_observations_persisted > 0
        # CAMS Global is 3-hourly, so ~56 records per variable
        # 7 days × 8 records/day × 2 variables = 112
        assert report.total_observations_persisted >= 50

    @pytest.mark.slow
    def test_aq_clamps_to_cams_start(self, collector: HistoricalCollector) -> None:
        """AQ collection clamps start date to CAMS Global availability."""
        # Request before CAMS Global start
        report = collector.collect_aq(
            start=date(2020, 1, 1),
            end=date(2020, 1, 7),
            variables=["pm2_5"],
            run_id="test_aq_clamp",
        )

        # Should have zero observations since 2020 is before CAMS Global start
        assert report.total_observations_persisted == 0
        assert report.total_chunks == 0


# ── Coverage Analysis Tests ───────────────────────────────────────────


class TestCoverageAnalysis:
    """Tests for the CoverageAnalyzer."""

    @pytest.mark.slow
    def test_coverage_after_collection(self, collector: HistoricalCollector, temp_db: Database) -> None:
        """Run coverage analysis after collecting data."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=13)

        # Collect weather data
        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
            run_id="test_coverage_weather",
        )

        # Analyze coverage
        analyzer = CoverageAnalyzer(temp_db)
        report = analyzer.analyze(parameters=["temperature_2m"])

        assert report.total_observations > 0
        assert len(report.parameters) == 1
        assert report.parameters[0].parameter == "temperature_2m"
        assert report.parameters[0].coverage_ratio > 0
        assert report.overall_coverage_score > 0

    @pytest.mark.slow
    def test_coverage_markdown_generation(
        self, collector: HistoricalCollector, temp_db: Database
    ) -> None:
        """Generate Markdown coverage report."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_coverage_md",
        )

        analyzer = CoverageAnalyzer(temp_db)
        report = analyzer.analyze()
        md = analyzer.generate_coverage_report_markdown(report)

        assert "# Historical Data Coverage Report" in md
        assert "temperature_2m" in md
        assert "Overall Coverage Score" in md

    @pytest.mark.slow
    def test_coverage_csv_generation(
        self, collector: HistoricalCollector, temp_db: Database, tmp_path: Path
    ) -> None:
        """Generate CSV coverage matrix."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=13)

        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_coverage_csv",
        )

        analyzer = CoverageAnalyzer(temp_db)
        report = analyzer.analyze()

        csv_path = str(tmp_path / "coverage.csv")
        analyzer.generate_coverage_matrix_csv(report, csv_path)

        assert Path(csv_path).exists()
        content = Path(csv_path).read_text()
        assert "temperature_2m" in content


# ── Quality Gate Tests ────────────────────────────────────────────────


class TestQualityGates:
    """Tests for the QualityGate evaluation system."""

    def test_gates_empty_database(self, temp_db: Database) -> None:
        """Quality gates handle empty database gracefully."""
        gates = QualityGates(temp_db)
        report = gates.evaluate()

        assert report.verdict == "NOT_MODEL_READY"
        assert report.failed_gates > 0
        assert report.total_gates == 10

    @pytest.mark.slow
    def test_gates_with_data(self, collector: HistoricalCollector, temp_db: Database) -> None:
        """Quality gates evaluate collected data."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=27)

        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
            run_id="test_gates_weather",
        )

        # Use relaxed thresholds for testing (won't have full data)
        thresholds = GateThresholds(
            min_observations_per_parameter=100,
            min_total_observations=300,
            min_coverage_hours=240,  # 10 days
            min_pm25_coverage_ratio=0.0,  # No PM2.5 in this test
            min_parameters=3,
            min_weather_parameters=3,
            min_aq_parameters=0,
        )

        gates = QualityGates(temp_db, thresholds)
        report = gates.evaluate()

        assert report.total_gates == 10
        # Some gates should pass
        assert report.passed_gates > 0

    @pytest.mark.slow
    def test_gates_markdown_report(
        self, collector: HistoricalCollector, temp_db: Database
    ) -> None:
        """Generate Markdown quality gate report."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_gates_md",
        )

        gates = QualityGates(temp_db)
        report = gates.evaluate()
        md = gates.generate_markdown_report(report)

        assert "# Quality Gate Report" in md
        assert "Verdict:" in md
        assert "DATA_SUFFICIENCY" in md


# ── Manifest Tests ────────────────────────────────────────────────────


class TestManifest:
    """Tests for DatasetManifest generation."""

    @pytest.mark.slow
    def test_manifest_generation(
        self,
        collector: HistoricalCollector,
        temp_db: Database,
        tmp_path: Path,
    ) -> None:
        """Generate a dataset manifest."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        weather_report = collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_manifest_weather",
        )

        # Coverage
        analyzer = CoverageAnalyzer(temp_db)
        coverage_report = analyzer.analyze()

        # Quality gates
        gates = QualityGates(temp_db)
        quality_report = gates.evaluate()

        # Manifest
        db_path = str(tmp_path / "test.db")
        builder = ManifestBuilder(temp_db, db_path)
        manifest = builder.build(
            weather_reports=[weather_report],
            coverage_report=coverage_report,
            quality_report=quality_report,
        )

        assert manifest.total_observations > 0
        assert manifest.generated_at != ""
        assert manifest.quality_verdict in ("MODEL_READY", "NOT_MODEL_READY")
        assert len(manifest.parameters) > 0
        assert len(manifest.notes) > 0

        # Save and reload
        manifest_path = str(tmp_path / "manifest.json")
        manifest.save(manifest_path)
        assert Path(manifest_path).exists()

        loaded = manifest.load(manifest_path)
        assert loaded.total_observations == manifest.total_observations
        assert loaded.generated_at == manifest.generated_at

    @pytest.mark.slow
    def test_manifest_to_dict(self, collector: HistoricalCollector, temp_db: Database) -> None:
        """Manifest serializes to dict correctly."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m"],
            run_id="test_manifest_dict",
        )

        builder = ManifestBuilder(temp_db, "/tmp/test.db")
        manifest = builder.build()

        d = manifest.to_dict()
        assert "schema_version" in d
        assert "total_observations" in d
        assert "parameters" in d
        assert isinstance(d["parameters"], list)


# ── Database Stats Tests ──────────────────────────────────────────────


class TestDatabaseStats:
    """Tests for the database statistics endpoint."""

    def test_stats_empty_db(self, collector: HistoricalCollector) -> None:
        """Stats on empty database."""
        stats = collector.get_database_stats()
        assert stats["total_observations"] == 0
        assert stats["total_ingestion_runs"] == 0
        assert stats["parameter_counts"] == {}

    @pytest.mark.slow
    def test_stats_after_collection(
        self, collector: HistoricalCollector, temp_db: Database
    ) -> None:
        """Stats reflect collected data."""
        end = date.today() - timedelta(days=2)
        start = end - timedelta(days=6)

        collector.collect_weather(
            start=start,
            end=end,
            variables=["temperature_2m", "relative_humidity_2m"],
            run_id="test_stats",
        )

        stats = collector.get_database_stats()
        assert stats["total_observations"] > 0
        assert "temperature_2m" in stats["parameter_counts"]
        assert stats["parameter_counts"]["temperature_2m"] > 0
        assert len(stats["recent_runs"]) > 0
