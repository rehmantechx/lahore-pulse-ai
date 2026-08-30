"""Quality gates — automated checks that determine modeling readiness.

Evaluates the collected dataset against a series of pass/fail gates.
Each gate tests a specific aspect of data quality. The final verdict
is either MODEL_READY or NOT_MODEL_READY.

Gates:
1. DATA_SUFFICIENCY: Minimum observation count per parameter
2. TEMPORAL_COVERAGE: Minimum date span (hours)
3. TARGET_AVAILABILITY: PM2.5 coverage ratio
4. MISSINGNESS: Maximum overall missingness ratio
5. TEMPORAL_CONTINUITY: Maximum gap size
6. DUPLICATE_INTEGRITY: Zero duplicates expected
7. PROVENANCE_COMPLETENESS: All obs have source tracking
8. PARAMETER_COMPLETENESS: Minimum number of parameters
9. VALUE_VALIDITY: No out-of-range values
10. SEASONAL_REPRESENTATION: Data across multiple seasons

Reference: Phase 3 Specification §14, §15
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from ..infrastructure.database import Database
from .coverage import CoverageReport


# ── Gate Thresholds ───────────────────────────────────────────────────


@dataclass(frozen=True)
class GateThresholds:
    """Configurable thresholds for quality gates.

    These can be tuned per project requirements.
    """

    # Data sufficiency
    min_observations_per_parameter: int = 10_000
    min_total_observations: int = 100_000

    # Temporal coverage
    min_coverage_hours: int = 8760  # 1 year
    min_coverage_days: int = 365

    # Target availability
    min_pm25_coverage_ratio: float = 0.80

    # Missingness
    max_missingness_ratio: float = 0.30

    # Temporal continuity
    max_gap_hours: int = 72  # 3 days

    # Provenance
    expected_source_count: int = 1

    # Parameter completeness
    min_parameters: int = 5
    min_weather_parameters: int = 5
    min_aq_parameters: int = 3

    # Seasonal representation
    min_seasons_covered: int = 2


# ── Gate Result ────────────────────────────────────────────────────────


@dataclass
class GateResult:
    """Result of a single quality gate check."""

    gate_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # "error" = blocks readiness, "warning" = advisory


@dataclass
class QualityGateReport:
    """Complete quality gate evaluation report."""

    verdict: str = "NOT_MODEL_READY"  # "MODEL_READY" or "NOT_MODEL_READY"
    generated_at: str = ""
    gates: list[GateResult] = field(default_factory=list)
    total_gates: int = 0
    passed_gates: int = 0
    failed_gates: int = 0
    warning_gates: int = 0
    blocking_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "verdict": self.verdict,
            "generated_at": self.generated_at,
            "total_gates": self.total_gates,
            "passed_gates": self.passed_gates,
            "failed_gates": self.failed_gates,
            "warning_gates": self.warning_gates,
            "blocking_failures": self.blocking_failures,
            "gates": [
                {
                    "gate_name": g.gate_name,
                    "passed": g.passed,
                    "severity": g.severity,
                    "message": g.message,
                    "details": g.details,
                }
                for g in self.gates
            ],
        }


# ── QualityGates ──────────────────────────────────────────────────────


class QualityGates:
    """Evaluates dataset quality against predefined gates.

    Usage:
        gates = QualityGates(db)
        report = gates.evaluate(coverage_report)
        if report.verdict == "MODEL_READY":
            proceed_to_modeling()
    """

    def __init__(
        self,
        db: Database,
        thresholds: GateThresholds | None = None,
    ) -> None:
        self._db = db
        self._thresholds = thresholds or GateThresholds()

    def evaluate(
        self,
        coverage_report: CoverageReport | None = None,
    ) -> QualityGateReport:
        """Run all quality gates and produce a verdict.

        Args:
            coverage_report: Optional pre-computed coverage report.
                           If None, will compute basic stats from DB.

        Returns:
            QualityGateReport with verdict and per-gate results.
        """
        logger.info("Running quality gate evaluation")
        t = self._thresholds

        report = QualityGateReport(
            generated_at=datetime.now(UTC).isoformat(),
        )

        # Gather stats from DB
        stats = self._gather_stats()

        # ── Gate 1: Data Sufficiency ──────────────────────────────
        total_obs = stats["total_observations"]
        min_per_param = stats["min_obs_per_param"]
        report.gates.append(
            GateResult(
                gate_name="DATA_SUFFICIENCY",
                passed=total_obs >= t.min_total_observations
                and min_per_param >= t.min_observations_per_parameter,
                message=(
                    f"Total: {total_obs:,} (min {t.min_total_observations:,}), "
                    f"min per param: {min_per_param:,} (min {t.min_observations_per_parameter:,})"
                ),
                details={
                    "total_observations": total_obs,
                    "min_per_parameter": min_per_param,
                    "threshold_total": t.min_total_observations,
                    "threshold_per_param": t.min_observations_per_parameter,
                },
            )
        )

        # ── Gate 2: Temporal Coverage ─────────────────────────────
        coverage_hours = stats.get("coverage_hours", 0)
        report.gates.append(
            GateResult(
                gate_name="TEMPORAL_COVERAGE",
                passed=coverage_hours >= t.min_coverage_hours,
                message=f"Coverage: {coverage_hours:,} hours (min {t.min_coverage_hours:,})",
                details={
                    "coverage_hours": coverage_hours,
                    "threshold_hours": t.min_coverage_hours,
                },
            )
        )

        # ── Gate 3: Target Availability (PM2.5) ──────────────────
        pm25_count = stats.get("parameter_counts", {}).get("pm2_5", 0)
        pm25_coverage = pm25_count / max(coverage_hours, 1)
        report.gates.append(
            GateResult(
                gate_name="TARGET_AVAILABILITY",
                passed=pm25_coverage >= t.min_pm25_coverage_ratio,
                message=f"PM2.5 coverage: {pm25_coverage:.2%} (min {t.min_pm25_coverage_ratio:.0%})",
                details={
                    "pm25_count": pm25_count,
                    "pm25_coverage_ratio": round(pm25_coverage, 4),
                    "threshold": t.min_pm25_coverage_ratio,
                },
            )
        )

        # ── Gate 4: Missingness ───────────────────────────────────
        missingness = stats.get("estimated_missingness", 0.0)
        report.gates.append(
            GateResult(
                gate_name="MISSINGNESS",
                passed=missingness <= t.max_missingness_ratio,
                message=f"Missingness: {missingness:.2%} (max {t.max_missingness_ratio:.0%})",
                details={
                    "missingness_ratio": round(missingness, 4),
                    "threshold": t.max_missingness_ratio,
                },
            )
        )

        # ── Gate 5: Temporal Continuity ───────────────────────────
        # Use coverage report if available
        longest_gap = 0
        if coverage_report and coverage_report.parameters:
            longest_gap = max(
                (pc.longest_gap_hours for pc in coverage_report.parameters),
                default=0,
            )
        else:
            # Rough estimate from DB
            longest_gap = stats.get("longest_gap_hours", 0)

        report.gates.append(
            GateResult(
                gate_name="TEMPORAL_CONTINUITY",
                passed=longest_gap <= t.max_gap_hours,
                message=f"Longest gap: {longest_gap}h (max {t.max_gap_hours}h)",
                details={
                    "longest_gap_hours": longest_gap,
                    "threshold": t.max_gap_hours,
                },
            )
        )

        # ── Gate 6: Duplicate Integrity ───────────────────────────
        dup_count = stats.get("duplicate_count", 0)
        report.gates.append(
            GateResult(
                gate_name="DUPLICATE_INTEGRITY",
                passed=dup_count == 0,
                message=f"Duplicates found: {dup_count}",
                details={"duplicate_count": dup_count},
            )
        )

        # ── Gate 7: Provenance Completeness ───────────────────────
        # Check that all observations have source_id
        obs_with_source = stats.get("observations_with_source", 0)
        provenance_ratio = obs_with_source / max(total_obs, 1)
        report.gates.append(
            GateResult(
                gate_name="PROVENANCE_COMPLETENESS",
                passed=provenance_ratio >= 0.99,
                message=f"Provenance coverage: {provenance_ratio:.2%}",
                details={
                    "with_source": obs_with_source,
                    "total": total_obs,
                    "ratio": round(provenance_ratio, 4),
                },
            )
        )

        # ── Gate 8: Parameter Completeness ────────────────────────
        param_count = stats.get("parameter_count", 0)
        weather_params = stats.get("weather_param_count", 0)
        aq_params = stats.get("aq_param_count", 0)
        report.gates.append(
            GateResult(
                gate_name="PARAMETER_COMPLETENESS",
                passed=(
                    param_count >= t.min_parameters
                    and weather_params >= t.min_weather_parameters
                    and aq_params >= t.min_aq_parameters
                ),
                message=(
                    f"Parameters: {param_count} total "
                    f"({weather_params} weather, {aq_params} AQ)"
                ),
                details={
                    "total_params": param_count,
                    "weather_params": weather_params,
                    "aq_params": aq_params,
                },
            )
        )

        # ── Gate 9: Value Validity ────────────────────────────────
        # Check for obviously invalid values (NaN counts in DB)
        invalid_count = stats.get("invalid_value_count", 0)
        report.gates.append(
            GateResult(
                gate_name="VALUE_VALIDITY",
                passed=invalid_count == 0,
                message=f"Invalid values: {invalid_count}",
                details={"invalid_count": invalid_count},
            )
        )

        # ── Gate 10: Seasonal Representation ──────────────────────
        seasons_covered = stats.get("seasons_covered", 0)
        report.gates.append(
            GateResult(
                gate_name="SEASONAL_REPRESENTATION",
                passed=seasons_covered >= t.min_seasons_covered,
                message=f"Seasons covered: {seasons_covered} (min {t.min_seasons_covered})",
                details={
                    "seasons_covered": seasons_covered,
                    "threshold": t.min_seasons_covered,
                },
            )
        )

        # ── Compute Verdict ───────────────────────────────────────
        report.total_gates = len(report.gates)
        report.passed_gates = sum(1 for g in report.gates if g.passed)
        report.failed_gates = sum(
            1 for g in report.gates if not g.passed and g.severity == "error"
        )
        report.warning_gates = sum(
            1 for g in report.gates if not g.passed and g.severity == "warning"
        )
        report.blocking_failures = [
            g.gate_name for g in report.gates if not g.passed and g.severity == "error"
        ]

        report.verdict = "MODEL_READY" if report.failed_gates == 0 else "NOT_MODEL_READY"

        logger.info(
            "Quality gate evaluation complete",
            verdict=report.verdict,
            passed=report.passed_gates,
            failed=report.failed_gates,
            warnings=report.warning_gates,
        )

        return report

    def _gather_stats(self) -> dict[str, Any]:
        """Gather database statistics needed for gate evaluation."""
        stats: dict[str, Any] = {}

        # Total observations
        stats["total_observations"] = self._db.table_row_count("observations")

        # Per-parameter counts
        param_rows = self._db.fetch_all(
            """SELECT parameter, COUNT(*) as cnt
            FROM observations
            GROUP BY parameter"""
        )
        param_counts = {r["parameter"]: r["cnt"] for r in param_rows}
        stats["parameter_counts"] = param_counts
        stats["parameter_count"] = len(param_counts)

        # Min per parameter
        stats["min_obs_per_param"] = min(param_counts.values()) if param_counts else 0

        # Weather vs AQ parameter counts
        weather_params = {
            "temperature_2m", "relative_humidity_2m", "dew_point_2m",
            "apparent_temperature", "precipitation", "rain", "cloud_cover",
            "pressure_msl", "surface_pressure", "wind_speed_10m",
            "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation",
            "vapour_pressure_deficit", "soil_temperature_0_to_7cm",
            "soil_moisture_0_to_7cm",
        }
        aq_params = {
            "pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide",
            "ozone", "carbon_monoxide",
        }
        stats["weather_param_count"] = len(set(param_counts.keys()) & weather_params)
        stats["aq_param_count"] = len(set(param_counts.keys()) & aq_params)

        # Date range and coverage hours
        date_range = self._db.fetch_one(
            """SELECT MIN(observed_at) as earliest, MAX(observed_at) as latest
            FROM observations"""
        )
        if date_range and date_range.get("earliest") and date_range.get("latest"):
            from datetime import datetime as dt

            try:
                earliest = dt.fromisoformat(date_range["earliest"].replace("Z", "+00:00"))
                latest = dt.fromisoformat(date_range["latest"].replace("Z", "+00:00"))
                stats["coverage_hours"] = int((latest - earliest).total_seconds() // 3600)
            except (ValueError, TypeError):
                stats["coverage_hours"] = 0
        else:
            stats["coverage_hours"] = 0

        # Seasons covered
        season_rows = self._db.fetch_all(
            """SELECT DISTINCT strftime('%m', observed_at) as month
            FROM observations"""
        )
        from .coverage import SEASON_MAP

        months = {int(r["month"]) for r in season_rows if r.get("month")}
        seasons = {SEASON_MAP.get(m) for m in months}
        seasons.discard(None)
        stats["seasons_covered"] = len(seasons)

        # Duplicate count (based on unique constraint)
        dup_rows = self._db.fetch_one(
            """SELECT COUNT(*) as cnt FROM (
                SELECT source_id, station_id, parameter, observed_at,
                       COUNT(*) as dupes
                FROM observations
                GROUP BY source_id, station_id, parameter, observed_at
                HAVING dupes > 1
            )"""
        )
        stats["duplicate_count"] = dup_rows["cnt"] if dup_rows else 0

        # Provenance
        source_rows = self._db.fetch_one(
            """SELECT COUNT(*) as cnt FROM observations
            WHERE source_id IS NOT NULL AND source_id != ''"""
        )
        stats["observations_with_source"] = source_rows["cnt"] if source_rows else 0

        # Invalid values (NaN in value column — shouldn't happen but check)
        invalid_rows = self._db.fetch_one(
            """SELECT COUNT(*) as cnt FROM observations
            WHERE value IS NULL OR CAST(value AS TEXT) = ''"""
        )
        stats["invalid_value_count"] = invalid_rows["cnt"] if invalid_rows else 0

        # Longest gap (rough: check pm2_5 or first parameter)
        stats["longest_gap_hours"] = 0
        if param_counts:
            first_param = list(param_counts.keys())[0]
            obs_times = self._db.fetch_all(
                """SELECT observed_at FROM observations
                WHERE parameter = ?
                ORDER BY observed_at""",
                (first_param,),
            )
            if len(obs_times) >= 2:
                from datetime import datetime as dt

                max_gap = 0
                for i in range(1, len(obs_times)):
                    try:
                        t1 = dt.fromisoformat(
                            obs_times[i - 1]["observed_at"].replace("Z", "+00:00")
                        )
                        t2 = dt.fromisoformat(
                            obs_times[i]["observed_at"].replace("Z", "+00:00")
                        )
                        gap = int((t2 - t1).total_seconds() // 3600)
                        max_gap = max(max_gap, gap)
                    except (ValueError, TypeError):
                        continue
                stats["longest_gap_hours"] = max_gap

        # Estimated missingness (very rough: 1 - (actual / expected))
        expected_total = stats["coverage_hours"] * stats["parameter_count"]
        if expected_total > 0:
            stats["estimated_missingness"] = max(
                0.0,
                1.0 - (stats["total_observations"] / expected_total),
            )
        else:
            stats["estimated_missingness"] = 1.0

        return stats

    def generate_markdown_report(
        self,
        report: QualityGateReport,
    ) -> str:
        """Generate a human-readable Markdown quality gate report.

        Args:
            report: QualityGateReport to render.

        Returns:
            Markdown string.
        """
        lines: list[str] = []

        lines.append("# Quality Gate Report")
        lines.append("")
        lines.append(f"**Generated:** {report.generated_at}")

        # Verdict
        if report.verdict == "MODEL_READY":
            lines.append("## ✅ Verdict: MODEL_READY")
            lines.append("")
            lines.append(
                "The dataset passes all quality gates and is suitable "
                "for model development."
            )
        else:
            lines.append("## ❌ Verdict: NOT_MODEL_READY")
            lines.append("")
            lines.append("The dataset does NOT pass all quality gates.")
            if report.blocking_failures:
                lines.append("")
                lines.append("**Blocking failures:**")
                for bf in report.blocking_failures:
                    lines.append(f"  - `{bf}`")

        lines.append("")
        lines.append(
            f"**Summary:** {report.passed_gates}/{report.total_gates} passed, "
            f"{report.failed_gates} failed, {report.warning_gates} warnings"
        )
        lines.append("")

        # Gate details
        lines.append("## Gate Results")
        lines.append("")
        lines.append("| Gate | Status | Severity | Message |")
        lines.append("|------|--------|----------|---------|")
        for g in report.gates:
            status = "✅ PASS" if g.passed else "❌ FAIL"
            lines.append(f"| {g.gate_name} | {status} | {g.severity} | {g.message} |")
        lines.append("")

        return "\n".join(lines)
