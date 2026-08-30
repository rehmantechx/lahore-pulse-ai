"""Coverage analysis — temporal, parameter, and seasonal data completeness.

Analyzes the historical dataset for coverage gaps, completeness,
and temporal distribution. Produces both human-readable and
machine-readable coverage matrices.

Coverage dimensions:
1. Monthly coverage (per parameter)
2. Seasonal coverage (winter/summer/monsoon/post-monsoon)
3. Day vs. night coverage (6am-6pm vs 6pm-6am PKT)
4. Weekday vs. weekend coverage
5. Parameter co-availability (how many params available per hour)
6. Gap analysis (longest gaps, total gap hours)

Reference: Phase 3 Specification §8, §9
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd
from loguru import logger

from ..infrastructure.database import Database

# ── Lahore Season Definitions (PKT months) ────────────────────────────
# Winter: Nov-Feb, Spring: Mar-Apr, Summer: May-Jun,
# Monsoon: Jul-Aug, Post-monsoon: Sep-Oct
SEASON_MAP = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "summer",
    6: "summer",
    7: "monsoon",
    8: "monsoon",
    9: "post-monsoon",
    10: "post-monsoon",
    11: "winter",
    12: "winter",
}


# ── Data Classes ──────────────────────────────────────────────────────


@dataclass
class MonthlyCoverage:
    """Coverage for a specific parameter in a specific month."""

    year: int
    month: int
    parameter: str
    expected_hours: int = 0
    actual_count: int = 0
    coverage_ratio: float = 0.0
    null_values: int = 0
    min_value: float = 0.0
    max_value: float = 0.0
    mean_value: float = 0.0


@dataclass
class SeasonalCoverage:
    """Aggregated seasonal coverage for a parameter."""

    season: str
    parameter: str
    years_covered: int = 0
    total_expected_hours: int = 0
    total_actual_count: int = 0
    coverage_ratio: float = 0.0


@dataclass
class TimeOfDayCoverage:
    """Day/night or weekday/weekend coverage."""

    label: str  # "day", "night", "weekday", "weekend"
    parameter: str
    expected_hours: int = 0
    actual_count: int = 0
    coverage_ratio: float = 0.0


@dataclass
class GapInfo:
    """Information about a single gap in the data."""

    parameter: str
    gap_start: str
    gap_end: str
    gap_hours: int
    gap_type: str  # "missing", "null_block"


@dataclass
class ParameterCoverage:
    """Overall coverage summary for a single parameter."""

    parameter: str
    first_observation: str = ""
    last_observation: str = ""
    total_hours_in_range: int = 0
    actual_count: int = 0
    coverage_ratio: float = 0.0
    longest_gap_hours: int = 0
    total_gap_hours: int = 0
    gap_count: int = 0
    null_count: int = 0


@dataclass
class CoverageReport:
    """Complete coverage analysis report."""

    generated_at: str = ""
    total_observations: int = 0
    date_range_start: str = ""
    date_range_end: str = ""
    parameters: list[ParameterCoverage] = field(default_factory=list)
    monthly: list[MonthlyCoverage] = field(default_factory=list)
    seasonal: list[SeasonalCoverage] = field(default_factory=list)
    time_of_day: list[TimeOfDayCoverage] = field(default_factory=list)
    gaps: list[GapInfo] = field(default_factory=list)
    co_availability: dict[str, float] = field(default_factory=dict)
    overall_coverage_score: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "generated_at": self.generated_at,
            "total_observations": self.total_observations,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "overall_coverage_score": self.overall_coverage_score,
            "parameters": [
                {
                    "parameter": p.parameter,
                    "first": p.first_observation,
                    "last": p.last_observation,
                    "coverage_ratio": p.coverage_ratio,
                    "longest_gap_hours": p.longest_gap_hours,
                    "total_gap_hours": p.total_gap_hours,
                    "gap_count": p.gap_count,
                }
                for p in self.parameters
            ],
            "co_availability": self.co_availability,
            "monthly_count": len(self.monthly),
            "seasonal_count": len(self.seasonal),
            "time_of_day_count": len(self.time_of_day),
            "gap_count": len(self.gaps),
        }


# ── CoverageAnalyzer ──────────────────────────────────────────────────


class CoverageAnalyzer:
    """Analyzes temporal and parameter coverage of the collected dataset.

    Usage:
        analyzer = CoverageAnalyzer(db)
        report = analyzer.analyze()
        print(report.overall_coverage_score)
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    def analyze(
        self,
        parameters: list[str] | None = None,
        include_gaps: bool = True,
        max_gaps_reported: int = 50,
    ) -> CoverageReport:
        """Run full coverage analysis on the database.

        Args:
            parameters: Specific parameters to analyze (None = all).
            include_gaps: Whether to compute gap details (slower).
            max_gaps_reported: Maximum number of gaps to report.

        Returns:
            CoverageReport with all analysis dimensions.
        """
        logger.info("Starting coverage analysis")

        # Load all observations into a DataFrame
        if parameters:
            placeholders = ",".join("?" * len(parameters))
            rows = self._db.fetch_all(
                f"""SELECT parameter, value, observed_at, quality_status
                FROM observations
                WHERE parameter IN ({placeholders})
                ORDER BY parameter, observed_at""",
                tuple(parameters),
            )
        else:
            rows = self._db.fetch_all(
                """SELECT parameter, value, observed_at, quality_status
                FROM observations
                ORDER BY parameter, observed_at"""
            )

        if not rows:
            logger.warning("No observations found for coverage analysis")
            return CoverageReport(
                generated_at=datetime.now(UTC).isoformat(),
            )

        df = pd.DataFrame(rows)
        # Handle mixed timestamp formats (e.g. "2026-06-15T00:00" vs "2026-06-11T00:00:00+00:00")
        df["observed_at"] = pd.to_datetime(df["observed_at"], format="mixed", utc=True)

        report = CoverageReport(
            generated_at=datetime.now(UTC).isoformat(),
            total_observations=len(df),
        )

        if len(df) > 0:
            report.date_range_start = df["observed_at"].min().isoformat()
            report.date_range_end = df["observed_at"].max().isoformat()

        # ── Per-parameter analysis ─────────────────────────────────
        all_params = sorted(df["parameter"].unique())
        coverage_scores: list[float] = []

        for param in all_params:
            param_df = df[df["parameter"] == param].copy()
            pc = self._compute_parameter_coverage(param, param_df)
            report.parameters.append(pc)
            if pc.coverage_ratio > 0:
                coverage_scores.append(pc.coverage_ratio)

        # Overall coverage score: geometric mean of parameter coverage ratios
        if coverage_scores:
            import numpy as np

            report.overall_coverage_score = float(
                np.exp(sum(np.log(max(s, 0.001)) for s in coverage_scores) / len(coverage_scores))
            )

        # ── Monthly coverage ──────────────────────────────────────
        for param in all_params:
            param_df = df[df["parameter"] == param]
            report.monthly.extend(self._compute_monthly_coverage(param, param_df))

        # ── Seasonal coverage ─────────────────────────────────────
        for param in all_params:
            param_df = df[df["parameter"] == param]
            report.seasonal.extend(self._compute_seasonal_coverage(param, param_df))

        # ── Time of day coverage ──────────────────────────────────
        for param in all_params:
            param_df = df[df["parameter"] == param]
            report.time_of_day.extend(self._compute_time_of_day_coverage(param, param_df))

        # ── Gap analysis ──────────────────────────────────────────
        if include_gaps:
            for param in all_params:
                param_df = df[df["parameter"] == param]
                gaps = self._compute_gaps(param, param_df)
                report.gaps.extend(gaps[:max_gaps_reported // len(all_params)])

        # ── Co-availability ───────────────────────────────────────
        report.co_availability = self._compute_co_availability(df)

        logger.info(
            "Coverage analysis complete",
            parameters=len(all_params),
            overall_score=round(report.overall_coverage_score, 4),
        )

        return report

    def _compute_parameter_coverage(
        self,
        param: str,
        param_df: pd.DataFrame,
    ) -> ParameterCoverage:
        """Compute overall coverage for a single parameter."""
        pc = ParameterCoverage(parameter=param)

        if param_df.empty:
            return pc

        pc.first_observation = param_df["observed_at"].min().isoformat()
        pc.last_observation = param_df["observed_at"].max().isoformat()

        # Expected hours in the date range
        time_range = param_df["observed_at"].max() - param_df["observed_at"].min()
        pc.total_hours_in_range = max(int(time_range.total_seconds() // 3600), 1)
        pc.actual_count = len(param_df)
        pc.coverage_ratio = min(pc.actual_count / pc.total_hours_in_range, 1.0)
        pc.null_count = int(param_df["value"].isna().sum())

        # Gap analysis
        gaps = self._compute_gaps(param, param_df)
        if gaps:
            pc.longest_gap_hours = max(g.gap_hours for g in gaps)
            pc.total_gap_hours = sum(g.gap_hours for g in gaps)
            pc.gap_count = len(gaps)

        return pc

    def _compute_monthly_coverage(
        self,
        param: str,
        param_df: pd.DataFrame,
    ) -> list[MonthlyCoverage]:
        """Compute monthly coverage for a parameter."""
        if param_df.empty:
            return []

        result: list[MonthlyCoverage] = []
        param_df = param_df.copy()
        param_df["year"] = param_df["observed_at"].dt.year
        param_df["month"] = param_df["observed_at"].dt.month

        for (year, month), group in param_df.groupby(["year", "month"]):
            # Expected: all hours in the month
            import calendar

            days_in_month = calendar.monthrange(year, month)[1]
            expected = days_in_month * 24

            values = group["value"].dropna()
            mc = MonthlyCoverage(
                year=int(year),
                month=int(month),
                parameter=param,
                expected_hours=expected,
                actual_count=len(values),
                coverage_ratio=min(len(values) / expected, 1.0) if expected > 0 else 0.0,
                null_values=int(group["value"].isna().sum()),
            )
            if len(values) > 0:
                mc.min_value = float(values.min())
                mc.max_value = float(values.max())
                mc.mean_value = round(float(values.mean()), 4)

            result.append(mc)

        return sorted(result, key=lambda x: (x.year, x.month))

    def _compute_seasonal_coverage(
        self,
        param: str,
        param_df: pd.DataFrame,
    ) -> list[SeasonalCoverage]:
        """Compute seasonal coverage for a parameter."""
        if param_df.empty:
            return []

        param_df = param_df.copy()
        param_df["month"] = param_df["observed_at"].dt.month
        param_df["season"] = param_df["month"].map(SEASON_MAP)
        param_df["year"] = param_df["observed_at"].dt.year

        result: list[SeasonalCoverage] = []
        for (season, year), group in param_df.groupby(["season", "year"]):
            if pd.isna(season):
                continue
            values = group["value"].dropna()
            time_range = group["observed_at"].max() - group["observed_at"].min()
            expected = max(int(time_range.total_seconds() // 3600), 1)

            sc = SeasonalCoverage(
                season=str(season),
                parameter=param,
                years_covered=1,
                total_expected_hours=expected,
                total_actual_count=len(values),
                coverage_ratio=min(len(values) / expected, 1.0) if expected > 0 else 0.0,
            )
            result.append(sc)

        return sorted(result, key=lambda x: (x.season, x.parameter))

    def _compute_time_of_day_coverage(
        self,
        param: str,
        param_df: pd.DataFrame,
    ) -> list[TimeOfDayCoverage]:
        """Compute day/night coverage for a parameter.

        Day = 06:00-18:00 PKT (UTC+5) = 01:00-13:00 UTC
        Night = 18:00-06:00 PKT (UTC+5) = 13:00-01:00 UTC
        """
        if param_df.empty:
            return []

        # Convert to PKT (UTC+5)
        pkt_hours = (param_df["observed_at"].dt.hour + 5) % 24

        is_day = (pkt_hours >= 6) & (pkt_hours < 18)
        is_weekday = param_df["observed_at"].dt.dayofweek < 5

        result: list[TimeOfDayCoverage] = []

        for label, mask in [
            ("day", is_day),
            ("night", ~is_day),
            ("weekday", is_weekday),
            ("weekend", ~is_weekday),
        ]:
            subset = param_df[mask]
            values = subset["value"].dropna()
            time_range_hours = max(
                int(
                    (param_df["observed_at"].max() - param_df["observed_at"].min()).total_seconds()
                    // 3600
                ),
                1,
            )
            half_range = time_range_hours // 2

            tc = TimeOfDayCoverage(
                label=label,
                parameter=param,
                expected_hours=half_range,
                actual_count=len(values),
                coverage_ratio=min(len(values) / half_range, 1.0) if half_range > 0 else 0.0,
            )
            result.append(tc)

        return result

    def _compute_gaps(
        self,
        param: str,
        param_df: pd.DataFrame,
    ) -> list[GapInfo]:
        """Identify gaps in the time series for a parameter.

        A gap is a period > 1 hour where no observations exist.
        """
        if param_df.empty:
            return []

        sorted_times = param_df["observed_at"].sort_values()
        gaps: list[GapInfo] = []

        for i in range(1, len(sorted_times)):
            prev = sorted_times.iloc[i - 1]
            curr = sorted_times.iloc[i]
            diff_hours = int((curr - prev).total_seconds() // 3600)

            if diff_hours > 1:
                gaps.append(
                    GapInfo(
                        parameter=param,
                        gap_start=prev.isoformat(),
                        gap_end=curr.isoformat(),
                        gap_hours=diff_hours,
                        gap_type="missing",
                    )
                )

        # Sort by gap size (largest first)
        gaps.sort(key=lambda g: g.gap_hours, reverse=True)
        return gaps

    def _compute_co_availability(
        self,
        df: pd.DataFrame,
    ) -> dict[str, float]:
        """Compute what fraction of hours have data for 1, 2, 3, ... N parameters.

        Returns a dict like:
        {
            "all_22_params": 0.95,   # 95% of hours have all 22 params
            "at_least_20_params": 0.98,
            "at_least_15_params": 1.0,
            "at_least_1_weather": 1.0,
            "at_least_1_aq": 0.70,
        }
        """
        if df.empty:
            return {}

        # Pivot: each row is an hour, each column is a parameter
        df_copy = df[["parameter", "value", "observed_at"]].copy()
        df_copy["hour"] = df_copy["observed_at"].dt.floor("h")

        # Count non-null values per (hour, parameter)
        pivot = df_copy.pivot_table(
            index="hour",
            columns="parameter",
            values="value",
            aggfunc="count",
        )

        total_hours = len(pivot)
        if total_hours == 0:
            return {}

        result: dict[str, float] = {}
        n_params = len(pivot.columns)

        # How many params are available per hour
        params_per_hour = pivot.notna().sum(axis=1)

        for threshold in [n_params, n_params - 2, n_params - 5, max(n_params - 10, 1), 3, 1]:
            fraction = float((params_per_hour >= threshold).sum()) / total_hours
            result[f"at_least_{threshold}_params"] = round(fraction, 4)

        result[f"all_{n_params}_params"] = round(
            float((params_per_hour == n_params).sum()) / total_hours, 4
        )

        # Weather vs AQ specific
        weather_params = [
            c for c in pivot.columns
            if c in ("temperature_2m", "relative_humidity_2m", "dew_point_2m",
                      "apparent_temperature", "precipitation", "rain", "cloud_cover",
                      "pressure_msl", "surface_pressure", "wind_speed_10m",
                      "wind_direction_10m", "wind_gusts_10m", "shortwave_radiation",
                      "vapour_pressure_deficit", "soil_temperature_0_to_7cm",
                      "soil_moisture_0_to_7cm")
        ]
        aq_params = [
            c for c in pivot.columns
            if c in ("pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide",
                      "ozone", "carbon_monoxide")
        ]

        if weather_params:
            weather_available = pivot[weather_params].notna().any(axis=1)
            result["at_least_1_weather"] = round(
                float(weather_available.sum()) / total_hours, 4
            )

        if aq_params:
            aq_available = pivot[aq_params].notna().any(axis=1)
            result["at_least_1_aq"] = round(float(aq_available.sum()) / total_hours, 4)

        return result

    def generate_coverage_matrix_csv(
        self,
        report: CoverageReport,
        output_path: str,
    ) -> str:
        """Generate a machine-readable coverage matrix as CSV.

        Rows = (year, month), Columns = parameters, Values = coverage ratio.

        Args:
            report: CoverageReport to export.
            output_path: Path to write the CSV file.

        Returns:
            Path to the generated CSV file.
        """
        if not report.monthly:
            logger.warning("No monthly data to export")
            return output_path

        rows: dict[tuple[int, int], dict] = {}
        for mc in report.monthly:
            key = (mc.year, mc.month)
            if key not in rows:
                rows[key] = {"year": mc.year, "month": mc.month}
            rows[key][mc.parameter] = round(mc.coverage_ratio, 4)

        df = pd.DataFrame(rows.values())
        df = df.sort_values(["year", "month"])
        df.to_csv(output_path, index=False)
        logger.info("Coverage matrix exported", path=output_path, rows=len(df))
        return output_path

    def generate_coverage_report_markdown(
        self,
        report: CoverageReport,
    ) -> str:
        """Generate a human-readable Markdown coverage report.

        Args:
            report: CoverageReport to render.

        Returns:
            Markdown string.
        """
        lines: list[str] = []

        lines.append("# Historical Data Coverage Report")
        lines.append("")
        lines.append(f"**Generated:** {report.generated_at}")
        lines.append(f"**Total Observations:** {report.total_observations:,}")
        if report.date_range_start and report.date_range_end:
            lines.append(f"**Date Range:** {report.date_range_start} → {report.date_range_end}")
        lines.append(f"**Overall Coverage Score:** {report.overall_coverage_score:.4f}")
        lines.append("")

        # Parameter summary
        lines.append("## Parameter Coverage")
        lines.append("")
        lines.append("| Parameter | Coverage | First Obs | Last Obs | Longest Gap | Total Gaps |")
        lines.append("|-----------|----------|-----------|----------|-------------|------------|")
        for pc in report.parameters:
            lines.append(
                f"| {pc.parameter} | {pc.coverage_ratio:.2%} | "
                f"{pc.first_observation[:10]} | {pc.last_observation[:10]} | "
                f"{pc.longest_gap_hours}h | {pc.gap_count} |"
            )
        lines.append("")

        # Monthly matrix (abbreviated)
        if report.monthly:
            lines.append("## Monthly Coverage Matrix (Top Parameters)")
            lines.append("")
            top_params = ["temperature_2m", "pm2_5", "pm10", "relative_humidity_2m", "wind_speed_10m"]
            available_params = [p for p in top_params if p in {mc.parameter for mc in report.monthly}]
            if available_params:
                header = "| Year-Month | " + " | ".join(available_params) + " |"
                sep = "|------------|" + "|".join(["----------"] * len(available_params)) + "|"
                lines.append(header)
                lines.append(sep)

                # Group by year-month
                monthly_by_ym: dict[tuple[int, int], dict[str, float]] = {}
                for mc in report.monthly:
                    key = (mc.year, mc.month)
                    if key not in monthly_by_ym:
                        monthly_by_ym[key] = {}
                    monthly_by_ym[key][mc.parameter] = mc.coverage_ratio

                for ym in sorted(monthly_by_ym.keys()):
                    vals = monthly_by_ym[ym]
                    row = f"| {ym[0]}-{ym[1]:02d} | "
                    row += " | ".join(f"{vals.get(p, 0):.0%}" for p in available_params)
                    row += " |"
                    lines.append(row)
                lines.append("")

        # Co-availability
        if report.co_availability:
            lines.append("## Parameter Co-Availability")
            lines.append("")
            for key, value in report.co_availability.items():
                lines.append(f"- **{key}:** {value:.2%}")
            lines.append("")

        # Seasonal
        if report.seasonal:
            lines.append("## Seasonal Coverage")
            lines.append("")
            lines.append("| Season | Parameter | Coverage |")
            lines.append("|--------|-----------|----------|")
            for sc in report.seasonal:
                lines.append(f"| {sc.season} | {sc.parameter} | {sc.coverage_ratio:.2%} |")
            lines.append("")

        # Time of day
        if report.time_of_day:
            lines.append("## Day/Night & Weekday/Weekend Coverage")
            lines.append("")
            lines.append("| Label | Parameter | Coverage |")
            lines.append("|-------|-----------|----------|")
            for tc in report.time_of_day:
                lines.append(f"| {tc.label} | {tc.parameter} | {tc.coverage_ratio:.2%} |")
            lines.append("")

        # Top gaps
        if report.gaps:
            lines.append("## Top Gaps (by Duration)")
            lines.append("")
            lines.append("| Parameter | Start | End | Duration |")
            lines.append("|-----------|-------|-----|----------|")
            for g in sorted(report.gaps, key=lambda x: x.gap_hours, reverse=True)[:20]:
                lines.append(
                    f"| {g.parameter} | {g.gap_start[:19]} | "
                    f"{g.gap_end[:19]} | {g.gap_hours}h |"
                )
            lines.append("")

        return "\n".join(lines)
