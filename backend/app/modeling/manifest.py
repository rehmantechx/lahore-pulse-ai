"""Dataset manifest — versioned snapshots of dataset metadata.

Generates machine-readable manifests that capture the exact state of
the dataset at a point in time, enabling reproducibility and audit.

The manifest records:
- Dataset version and generation timestamp
- Configuration used
- Collection parameters and provenance
- Coverage statistics
- Quality gate verdict
- Database file hash

Reference: Phase 3 Specification §13
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from ..infrastructure.database import Database
from .coverage import CoverageReport
from .historical_collector import CollectionReport
from .quality_gates import QualityGateReport


@dataclass
class DatasetManifest:
    """Versioned snapshot of the dataset state.

    This is the authoritative metadata file for any dataset generation.
    It should be stored alongside the database file and included in
    any dataset distribution.
    """

    # Identity
    schema_version: str = "1.0.0"
    dataset_version: str = "1.0.0"
    generated_at: str = ""
    generator: str = "lahore-pulse-ai/phase3-historical-collection"

    # Geographic scope
    latitude: float = 31.5204
    longitude: float = 74.3587

    # Database info
    database_file: str = ""
    database_file_hash: str = ""
    database_file_size_bytes: int = 0

    # Collection summary
    collection_reports: list[dict[str, Any]] = field(default_factory=list)

    # Coverage summary
    date_range_start: str = ""
    date_range_end: str = ""
    total_observations: int = 0
    parameters: list[str] = field(default_factory=list)
    parameter_count: int = 0
    overall_coverage_score: float = 0.0

    # Quality gate verdict
    quality_verdict: str = ""
    quality_gates_passed: int = 0
    quality_gates_total: int = 0

    # Data provenance
    weather_provider: str = "Open-Meteo ECMWF IFS 9km"
    weather_model: str = "ecmwf_ifs"
    weather_resolution: str = "9km"
    weather_start_date: str = "2017-01-01"
    aq_provider: str = "Open-Meteo CAMS Global"
    aq_domain: str = "cams_global"
    aq_resolution: str = "45km"
    aq_start_date: str = "2022-08-01"

    # Licensing
    weather_license: str = "CC-BY 4.0 (Open-Meteo)"
    aq_license: str = "CC-BY 4.0 (Open-Meteo / Copernicus)"

    # Constraints
    data_type: str = "reanalysis_grid_cell"
    station_id: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str) -> None:
        """Save manifest to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())
        logger.info("Manifest saved", path=path)

    @classmethod
    def load(cls, path: str) -> DatasetManifest:
        """Load manifest from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ManifestBuilder:
    """Builds a DatasetManifest from current database state and reports.

    Usage:
        builder = ManifestBuilder(db)
        manifest = builder.build(
            weather_reports=[weather_report],
            aq_reports=[aq_report],
            coverage_report=coverage,
            quality_report=quality,
        )
        manifest.save("data/manifest.json")
    """

    def __init__(self, db: Database, database_path: str = "") -> None:
        self._db = db
        self._database_path = database_path

    def build(
        self,
        weather_reports: list[CollectionReport] | None = None,
        aq_reports: list[CollectionReport] | None = None,
        coverage_report: CoverageReport | None = None,
        quality_report: QualityGateReport | None = None,
        latitude: float = 31.5204,
        longitude: float = 74.3587,
        notes: list[str] | None = None,
    ) -> DatasetManifest:
        """Build a complete manifest from current state.

        Args:
            weather_reports: Weather collection reports.
            aq_reports: AQ collection reports.
            coverage_report: Coverage analysis results.
            quality_report: Quality gate evaluation results.
            latitude: Collection latitude.
            longitude: Collection longitude.
            notes: Additional notes to include.

        Returns:
            Fully populated DatasetManifest.
        """
        manifest = DatasetManifest(
            generated_at=datetime.now(UTC).isoformat(),
            latitude=latitude,
            longitude=longitude,
            notes=notes or [],
        )

        # Database info
        if self._database_path:
            manifest.database_file = self._database_path
            try:
                path = Path(self._database_path)
                if path.exists():
                    manifest.database_file_size_bytes = path.stat().st_size
                    with open(path, "rb") as f:
                        manifest.database_file_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception as e:
                logger.warning("Could not hash database file", error=str(e))
                manifest.notes.append(f"Database hash failed: {e}")

        # Collection reports
        all_reports: list[CollectionReport] = []
        if weather_reports:
            all_reports.extend(weather_reports)
            manifest.collection_reports.extend([r.to_dict() for r in weather_reports])
        if aq_reports:
            all_reports.extend(aq_reports)
            manifest.collection_reports.extend([r.to_dict() for r in aq_reports])

        # Database statistics
        total_obs = self._db.table_row_count("observations")
        manifest.total_observations = total_obs

        # Parameters
        param_rows = self._db.fetch_all(
            """SELECT DISTINCT parameter FROM observations ORDER BY parameter"""
        )
        manifest.parameters = [r["parameter"] for r in param_rows]
        manifest.parameter_count = len(manifest.parameters)

        # Date range
        date_range = self._db.fetch_one(
            """SELECT MIN(observed_at) as earliest, MAX(observed_at) as latest
            FROM observations"""
        )
        if date_range:
            manifest.date_range_start = date_range.get("earliest", "")
            manifest.date_range_end = date_range.get("latest", "")

        # Coverage
        if coverage_report:
            manifest.overall_coverage_score = coverage_report.overall_coverage_score

        # Quality gates
        if quality_report:
            manifest.quality_verdict = quality_report.verdict
            manifest.quality_gates_passed = quality_report.passed_gates
            manifest.quality_gates_total = quality_report.total_gates

        # Notes about constraints
        manifest.notes.append(
            "AQ data for Lahore is only available from Aug 2022 "
            "(CAMS Global, non-European location)"
        )
        manifest.notes.append(
            "Weather data uses ECMWF IFS 9km reanalysis (from 2017)"
        )
        manifest.notes.append(
            "All data is reanalysis/satellite-derived, not ground station measurements"
        )

        return manifest
