"""Historical data collection orchestrator — CLI entry point.

Runs the full Phase 3 historical data collection pipeline:
1. Collect weather data (ECMWF IFS, 2017-present)
2. Collect AQ data (CAMS Global, Aug 2022-present)
3. Run coverage analysis
4. Run quality gate evaluation
5. Generate dataset manifest
6. Write reports to data/reports/

Usage:
    cd backend
    python run_historical_collection.py [--weather-only] [--aq-only] [--quick]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import Settings
from app.infrastructure.database import Database
from app.modeling.coverage import CoverageAnalyzer
from app.modeling.historical_collector import HistoricalCollector
from app.modeling.manifest import ManifestBuilder
from app.modeling.quality_gates import QualityGateReport, QualityGates

# ── Configuration ─────────────────────────────────────────────────────

# Database path
DB_PATH = str(Path(__file__).parent / "data" / "lahore_pulse.db")

# Reports directory
REPORTS_DIR = Path(__file__).parent / "data" / "reports"

# Collection parameters
WEATHER_START = date(2017, 1, 1)
AQ_START = date(2022, 8, 1)
CHUNK_DAYS = 30

# Quick mode: shorter date range for testing
QUICK_WEATHER_DAYS = 90
QUICK_AQ_DAYS = 60


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Historical data collection for Lahore Pulse AI",
    )
    parser.add_argument(
        "--weather-only",
        action="store_true",
        help="Only collect weather data (skip AQ)",
    )
    parser.add_argument(
        "--aq-only",
        action="store_true",
        help="Only collect AQ data (skip weather)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: collect only recent data (for testing)",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=CHUNK_DAYS,
        help=f"Days per collection chunk (default: {CHUNK_DAYS})",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DB_PATH,
        help=f"Database file path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--weather-model",
        type=str,
        default="ecmwf_ifs",
        choices=["ecmwf_ifs", "era5"],
        help="Weather model to use (default: ecmwf_ifs)",
    )
    return parser.parse_args()


def write_report(filename: str, content: str) -> None:
    """Write a report file to the reports directory."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"  Report written: {path}")


def main() -> None:
    """Run the full historical data collection pipeline."""
    args = parse_args()
    today = date.today()

    print("=" * 70)
    print("  Lahore Pulse AI — Historical Data Collection")
    print("=" * 70)
    print()

    # ── Initialize ────────────────────────────────────────────────
    settings = Settings()
    db = Database(args.db_path)
    db.initialize()
    collector = HistoricalCollector(settings, db, chunk_days=args.chunk_days)

    weather_reports = []
    aq_reports = []

    # ── Weather Collection ────────────────────────────────────────
    if not args.aq_only:
        print("━━━ Weather Data Collection (ECMWF IFS) ━━━")
        if args.quick:
            weather_start = today - timedelta(days=QUICK_WEATHER_DAYS)
            print(f"  QUICK MODE: {weather_start} → {today}")
        else:
            weather_start = WEATHER_START
            print(f"  FULL MODE: {weather_start} → {today}")

        print(f"  Model: {args.weather_model}")
        print(f"  Chunk size: {args.chunk_days} days")
        print(f"  Variables: 16")
        print()

        weather_report = collector.collect_weather(
            start=weather_start,
            end=today,
            model=args.weather_model,
            run_id=f"phase3_weather_{args.weather_model}_{today.isoformat()}",
        )
        weather_reports.append(weather_report)

        print()
        print(f"  ✓ Weather collection complete")
        print(f"    Chunks: {weather_report.completed_chunks}/{weather_report.total_chunks} completed")
        print(f"    Observations: {weather_report.total_observations_persisted:,} persisted")
        print(f"    Duration: {weather_report.total_duration_seconds:.1f}s")
        if weather_report.errors:
            print(f"    Errors: {len(weather_report.errors)}")
            for e in weather_report.errors[:3]:
                print(f"      - {e[:100]}")
        print()

    # ── AQ Collection ─────────────────────────────────────────────
    if not args.weather_only:
        print("━━━ Air Quality Data Collection (CAMS Global) ━━━")
        if args.quick:
            aq_start = today - timedelta(days=QUICK_AQ_DAYS)
            print(f"  QUICK MODE: {aq_start} → {today}")
        else:
            aq_start = max(AQ_START, date(2022, 8, 1))
            print(f"  FULL MODE: {aq_start} → {today}")

        print(f"  Domain: cams_global")
        print(f"  Chunk size: {args.chunk_days} days")
        print(f"  Variables: 6")
        print()

        aq_report = collector.collect_aq(
            start=aq_start,
            end=today,
            run_id=f"phase3_aq_cams_global_{today.isoformat()}",
        )
        aq_reports.append(aq_report)

        print()
        print(f"  ✓ AQ collection complete")
        print(f"    Chunks: {aq_report.completed_chunks}/{aq_report.total_chunks} completed")
        print(f"    Observations: {aq_report.total_observations_persisted:,} persisted")
        print(f"    Duration: {aq_report.total_duration_seconds:.1f}s")
        if aq_report.errors:
            print(f"    Errors: {len(aq_report.errors)}")
            for e in aq_report.errors[:3]:
                print(f"      - {e[:100]}")
        print()

    # ── Database Statistics ───────────────────────────────────────
    print("━━━ Database Statistics ━━━")
    stats = collector.get_database_stats()
    print(f"  Total observations: {stats['total_observations']:,}")
    print(f"  Total ingestion runs: {stats['total_ingestion_runs']}")
    if stats.get("date_range"):
        dr = stats["date_range"]
        print(f"  Date range: {dr.get('earliest', 'N/A')} → {dr.get('latest', 'N/A')}")
    print()
    print("  Parameter breakdown:")
    for param, count in sorted(stats.get("parameter_counts", {}).items(), key=lambda x: -x[1]):
        print(f"    {param}: {count:,}")
    print()

    # ── Coverage Analysis ─────────────────────────────────────────
    print("━━━ Coverage Analysis ━━━")
    analyzer = CoverageAnalyzer(db)
    coverage_report = analyzer.analyze()

    # Write coverage matrix CSV
    matrix_path = str(REPORTS_DIR / "coverage_matrix.csv")
    analyzer.generate_coverage_matrix_csv(coverage_report, matrix_path)

    # Write coverage Markdown
    coverage_md = analyzer.generate_coverage_report_markdown(coverage_report)
    write_report("coverage_report.md", coverage_md)

    print(f"  Overall coverage score: {coverage_report.overall_coverage_score:.4f}")
    print(f"  Parameters analyzed: {len(coverage_report.parameters)}")
    print(f"  Total gaps found: {len(coverage_report.gaps)}")
    print()

    # ── Quality Gates ─────────────────────────────────────────────
    print("━━━ Quality Gate Evaluation ━━━")
    gates = QualityGates(db)
    quality_report = gates.evaluate(coverage_report)

    quality_md = gates.generate_markdown_report(quality_report)
    write_report("quality_gates_report.md", quality_md)

    print(f"  Verdict: {quality_report.verdict}")
    print(f"  Gates: {quality_report.passed_gates}/{quality_report.total_gates} passed")
    if quality_report.blocking_failures:
        print(f"  Blocking failures: {', '.join(quality_report.blocking_failures)}")
    print()

    # ── Dataset Manifest ──────────────────────────────────────────
    print("━━━ Dataset Manifest ━━━")
    manifest_builder = ManifestBuilder(db, args.db_path)
    manifest = manifest_builder.build(
        weather_reports=weather_reports,
        aq_reports=aq_reports,
        coverage_report=coverage_report,
        quality_report=quality_report,
    )
    manifest_path = str(REPORTS_DIR / "dataset_manifest.json")
    manifest.save(manifest_path)
    print(f"  Version: {manifest.dataset_version}")
    print(f"  Observations: {manifest.total_observations:,}")
    print(f"  Parameters: {manifest.parameter_count}")
    print()

    # ── Summary ───────────────────────────────────────────────────
    print("=" * 70)
    print(f"  COLLECTION COMPLETE")
    print(f"  Database: {args.db_path}")
    print(f"  Reports: {REPORTS_DIR}")
    print(f"  Quality Verdict: {quality_report.verdict}")
    print("=" * 70)

    db.close()


if __name__ == "__main__":
    main()
