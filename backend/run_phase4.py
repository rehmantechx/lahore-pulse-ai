"""Phase 4 CLI — Run model training and evaluation.

Usage:
    python run_phase4.py
    python run_phase4.py --horizons 1 6 24
    python run_phase4.py --db-path data/lahore_pulse.db --output-dir data/models
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger


def main() -> None:
    """Run the Phase 4 model training and evaluation pipeline."""
    parser = argparse.ArgumentParser(
        description="Phase 4: Model Training & Evaluation",
    )
    parser.add_argument(
        "--db-path",
        default="data/lahore_pulse.db",
        help="Path to the SQLite database (default: data/lahore_pulse.db)",
    )
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=[1, 3, 6, 12, 24],
        help="Forecast horizons in hours (default: 1 3 6 12 24)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/models",
        help="Output directory for model artifacts (default: data/models)",
    )
    parser.add_argument(
        "--report-dir",
        default="data/reports",
        help="Output directory for reports (default: data/reports)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: only horizons 1, 6, 24",
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

    horizons = args.horizons
    if args.quick:
        horizons = [1, 6, 24]

    logger.info("=" * 60)
    logger.info("Lahore Pulse AI — Phase 4")
    logger.info("Predictive Forecasting Engine")
    logger.info("=" * 60)
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Horizons: {horizons}")
    logger.info(f"Output: {args.output_dir}")

    from app.modeling.orchestrator import Phase4Orchestrator

    orchestrator = Phase4Orchestrator(
        db_path=args.db_path,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        horizons=horizons,
    )

    try:
        report = orchestrator.run()
        logger.info("\nPhase 4 completed successfully!")
        logger.info(f"Results saved to {args.report_dir}/phase4_results.json")
    except Exception as e:
        logger.error(f"Phase 4 failed: {e}")
        raise


if __name__ == "__main__":
    main()
