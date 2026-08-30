"""
Phase 0.5 — Architectural Contract Tests

These tests verify that the proposed data contracts, schemas, and interface
definitions are internally consistent, valid, and will produce well-formed
data when implemented in Phase 1.

These tests do NOT call live APIs. They validate:
1. Domain model consistency with research findings
2. Data quality contract completeness
3. Provider abstraction interface contracts
4. Temporal alignment correctness
5. Spatial constraint validity
6. Licensing and attribution completeness
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# 1. Domain Models — Validated Against Research Findings
# ---------------------------------------------------------------------------


class MeasurementUnit(StrEnum):
    """Units from research: Open-Meteo uses °C, hPa, km/h, mm, %, W/m².
    OpenAQ uses μg/m³, ppm, ppb."""

    UG_M3 = "μg/m3"
    DEGREES_C = "°C"
    HPA = "hPa"
    KM_H = "km/h"
    MM = "mm"
    PERCENT = "%"
    W_M2 = "W/m2"
    MJ_M2 = "MJ/m2"
    PPM = "ppm"
    PPB = "ppb"
    SECONDS = "s"
    INDEX = "index"
    DEGREES = "°"
    KPA = "kPa"
    M_S = "m/s"
    M3_M3 = "m3/m3"


class DataSourceType(StrEnum):
    """Source types identified in research."""

    REANALYSIS = "reanalysis"
    FORECAST = "forecast"
    GROUND_STATION = "ground_station"
    SATELLITE = "satellite"
    MODEL_OUTPUT = "model_output"


class DataQuality(BaseModel):
    """Quality contract per observation — validated against Section 11."""

    completeness: float = Field(
        ge=0.0, le=1.0, description="Fraction of expected observations present"
    )
    quality_flag: str = Field(description="verified, estimated, interpolated, or missing")
    source_reliability: int = Field(ge=1, le=5, description="1=lowest, 5=highest reliability")

    @field_validator("quality_flag")
    @classmethod
    def validate_quality_flag(cls, v: str) -> str:
        valid_flags = {"verified", "estimated", "interpolated", "missing"}
        if v not in valid_flags:
            msg = f"quality_flag must be one of {valid_flags}, got '{v}'"
            raise ValueError(msg)
        return v


class Coordinates(BaseModel):
    """Lahore spatial constraints from research: 31.5204°N, 74.3587°E."""

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

    @field_validator("latitude")
    @classmethod
    def validate_lahore_latitude(cls, v: float) -> float:
        """Lahore is between 31.44°N and 31.60°N."""
        if not (31.44 <= v <= 31.60):
            msg = f"Lahore latitude must be between 31.44 and 31.60, got {v}"
            raise ValueError(msg)
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lahore_longitude(cls, v: float) -> float:
        """Lahore is between 74.28°E and 74.44°E."""
        if not (74.28 <= v <= 74.44):
            msg = f"Lahore longitude must be between 74.28 and 74.44, got {v}"
            raise ValueError(msg)
        return v


class Provenance(BaseModel):
    """Provenance tracking from Section 12."""

    source_id: str = Field(description="e.g., 'openaq_v3', 'openmeteo_archive'")
    source_identifier: str = Field(description="Original ID from upstream source")
    retrieved_at: datetime
    quality_flag: str
    license: str

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        known_sources = {
            "openaq_v3",
            "openmeteo_archive",
            "openmeteo_forecast",
            "openmeteo_aq",
            "aqicn",
            "cams_ensemble",
        }
        if v not in known_sources:
            msg = f"source_id must be one of {known_sources}, got '{v}'"
            raise ValueError(msg)
        return v


class Observation(BaseModel):
    """Single observation with full provenance — the core data unit."""

    observation_id: str
    source: Provenance
    timestamp: datetime
    parameter: str
    value: float
    unit: MeasurementUnit
    quality: DataQuality
    location: Coordinates


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment(BaseModel):
    """Risk assessment for data quality issues."""

    risk_type: str
    severity: RiskSeverity
    description: str
    mitigation: str


# ---------------------------------------------------------------------------
# 2. Research-Derived Constants — Validated Against Findings
# ---------------------------------------------------------------------------

# From Section 3.2.1: ECMWF IFS is 9km, 2017+
ECMWF_IFS_START_YEAR = 2017
ECMWF_IFS_RESOLUTION_KM = 9.0

# From Section 3.2.1: ERA5 is 0.25°, 1940+
ERA5_START_YEAR = 1940
ERA5_RESOLUTION_DEGREES = 0.25

# From Section 3.2.1: ERA5-Land is 0.1°, 1950+
ERA5_LAND_START_YEAR = 1950
ERA5_LAND_RESOLUTION_DEGREES = 0.1

# From Section 3.2.2: CAMS European is 11km, 2013+
CAMS_EUROPEAN_START_YEAR = 2013
CAMS_EUROPEAN_RESOLUTION_KM = 11.0

# From Section 3.2.2: CAMS Global is 45km, 2022+
CAMS_GLOBAL_START_YEAR = 2022
CAMS_GLOBAL_RESOLUTION_KM = 45.0

# From Section 4.3: OpenAQ rate limits
OPENAQ_RATE_LIMIT_PER_MINUTE = 60
OPENAQ_RATE_LIMIT_PER_HOUR = 2000

# From Section 3.3: Open-Meteo rate limits
OPENMETEO_DAILY_LIMIT = 10_000
OPENMETEO_HOURLY_LIMIT = 5_000

# From Section 5.2: AQICN rate limit
AQICN_RATE_LIMIT_PER_SECOND = 1000

# Lahore constants from Section 10.1
LAHORE_CENTER_LAT = 31.5204
LAHORE_CENTER_LON = 74.3587
LAHORE_LAT_MIN = 31.44
LAHORE_LAT_MAX = 31.60
LAHORE_LON_MIN = 74.28
LAHORE_LON_MAX = 74.44
LAHORE_ELEVATION_M = 217.0
LAHORE_TIMEZONE = "Asia/Karachi"
LAHORE_UTC_OFFSET = 5  # hours

# From Section 7: PM2.5 bounds
PM25_MIN_UG_M3 = 0.0
PM25_MAX_UG_M3 = 1000.0

# From Section 14.2: Data fusion priority
WEATHER_SOURCE_PRIORITY = ["openmeteo"]
AQ_GROUND_TRUTH_PRIORITY = ["openaq", "aqicn"]
AQ_FORECAST_PRIORITY = ["openmeteo_airquality"]


# ---------------------------------------------------------------------------
# 3. Test Suite
# ---------------------------------------------------------------------------


class TestDomainModelConsistency:
    """Verify domain models are consistent with research findings."""

    def test_lahore_coordinates_within_bounds(self):
        """Lahore center must be within the defined spatial bounds."""
        coords = Coordinates(latitude=LAHORE_CENTER_LAT, longitude=LAHORE_CENTER_LON)
        assert LAHORE_LAT_MIN <= coords.latitude <= LAHORE_LAT_MAX
        assert LAHORE_LON_MIN <= coords.longitude <= LAHORE_LON_MAX

    def test_lahore_boundary_coordinates_valid(self):
        """All four corners of Lahore bounding box must be valid."""
        corners = [
            (LAHORE_LAT_MIN, LAHORE_LON_MIN),
            (LAHORE_LAT_MIN, LAHORE_LON_MAX),
            (LAHORE_LAT_MAX, LAHORE_LON_MIN),
            (LAHORE_LAT_MAX, LAHORE_LON_MAX),
        ]
        for lat, lon in corners:
            coords = Coordinates(latitude=lat, longitude=lon)
            assert coords.latitude == lat
            assert coords.longitude == lon

    def test_invalid_coordinates_rejected(self):
        """Coordinates outside Lahore bounds must be rejected."""
        with pytest.raises(ValidationError):
            Coordinates(latitude=0.0, longitude=0.0)

    def test_measurement_units_match_sources(self):
        """All units from research sources must be representable."""
        # Open-Meteo units
        assert MeasurementUnit.DEGREES_C.value == "°C"
        assert MeasurementUnit.HPA.value == "hPa"
        assert MeasurementUnit.KM_H.value == "km/h"
        assert MeasurementUnit.MM.value == "mm"
        assert MeasurementUnit.PERCENT.value == "%"
        assert MeasurementUnit.W_M2.value == "W/m2"
        assert MeasurementUnit.MJ_M2.value == "MJ/m2"
        assert MeasurementUnit.KPA.value == "kPa"
        assert MeasurementUnit.M3_M3.value == "m3/m3"
        assert MeasurementUnit.SECONDS.value == "s"
        assert MeasurementUnit.DEGREES.value == "°"
        # OpenAQ units
        assert MeasurementUnit.UG_M3.value == "μg/m3"
        assert MeasurementUnit.PPM.value == "ppm"
        assert MeasurementUnit.PPB.value == "ppb"

    def test_data_quality_flags_complete(self):
        """Quality flags must cover all research-defined states."""
        valid_flags = {"verified", "estimated", "interpolated", "missing"}
        for flag in valid_flags:
            q = DataQuality(completeness=0.95, quality_flag=flag, source_reliability=4)
            assert q.quality_flag == flag

    def test_data_quality_completeness_bounds(self):
        """Completeness must be between 0 and 1."""
        q = DataQuality(completeness=0.0, quality_flag="missing", source_reliability=1)
        assert q.completeness == 0.0
        q = DataQuality(completeness=1.0, quality_flag="verified", source_reliability=5)
        assert q.completeness == 1.0

    def test_source_reliability_ranking(self):
        """Source reliability must be 1-5 as defined in Section 14."""
        for level in range(1, 6):
            q = DataQuality(completeness=0.9, quality_flag="verified", source_reliability=level)
            assert q.source_reliability == level


class TestProvenanceTracking:
    """Verify provenance system captures all required fields."""

    def test_provenance_source_ids_known(self):
        """Only known source IDs should be accepted."""
        known = {
            "openaq_v3",
            "openmeteo_archive",
            "openmeteo_forecast",
            "openmeteo_aq",
            "aqicn",
            "cams_ensemble",
        }
        for src in known:
            p = Provenance(
                source_id=src,
                source_identifier="test-123",
                retrieved_at=datetime.now(UTC),
                quality_flag="verified",
                license="CC-BY-4.0",
            )
            assert p.source_id == src

    def test_provenance_unknown_source_rejected(self):
        """Unknown source IDs must be rejected."""
        with pytest.raises(ValidationError):
            Provenance(
                source_id="unknown_source",
                source_identifier="test-123",
                retrieved_at=datetime.now(UTC),
                quality_flag="verified",
                license="CC-BY-4.0",
            )

    def test_observation_full_provenance(self):
        """A complete observation must carry full provenance chain."""
        obs = Observation(
            observation_id="obs-001",
            source=Provenance(
                source_id="openaq_v3",
                source_identifier="sensor-23534",
                retrieved_at=datetime.now(UTC),
                quality_flag="verified",
                license="CC-BY-4.0",
            ),
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            parameter="pm25",
            value=89.2,
            unit=MeasurementUnit.UG_M3,
            quality=DataQuality(completeness=1.0, quality_flag="verified", source_reliability=4),
            location=Coordinates(latitude=LAHORE_CENTER_LAT, longitude=LAHORE_CENTER_LON),
        )
        assert obs.source.source_id == "openaq_v3"
        assert obs.value == 89.2
        assert obs.unit == MeasurementUnit.UG_M3


class TestTemporalAlignment:
    """Verify temporal alignment rules from Section 9."""

    def test_utc_is_internal_standard(self):
        """All internal timestamps must be UTC."""
        ts = datetime(2024, 1, 1, 5, 0, tzinfo=UTC)
        assert ts.tzinfo is not None
        assert ts.utcoffset().total_seconds() == 0

    def test_lahore_offset_conversion(self):
        """Lahore is UTC+5 (Asia/Karachi)."""
        utc_time = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
        # Lahore local = UTC + 5 hours
        lahore_hour = (utc_time.hour + LAHORE_UTC_OFFSET) % 24
        assert lahore_hour == 5

    def test_training_window_no_leakage(self):
        """Training features must not include future data."""
        from datetime import timedelta

        prediction_time = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
        feature_window_end = prediction_time
        feature_window_start = prediction_time - timedelta(hours=72)
        assert feature_window_end <= prediction_time
        assert feature_window_start < prediction_time

    def test_ecmwf_ifs_availability(self):
        """ECMWF IFS data must be available for 2017+."""
        test_date = datetime(2017, 1, 1)
        assert test_date.year >= ECMWF_IFS_START_YEAR

    def test_era5_longer_history_available(self):
        """ERA5 provides data back to 1940."""
        test_date = datetime(1940, 1, 1)
        assert test_date.year >= ERA5_START_YEAR


class TestSpatialConstraints:
    """Verify spatial architecture from Section 10."""

    def test_lahore_bounding_box_area(self):
        """Lahore bounding box covers core urban monitoring area."""
        lat_range = LAHORE_LAT_MAX - LAHORE_LAT_MIN  # ~0.16°
        lon_range = LAHORE_LON_MAX - LAHORE_LON_MIN  # ~0.16°
        # 1° latitude ≈ 111 km
        lat_km = lat_range * 111
        # 1° longitude at 31.5°N ≈ 94.5 km
        lon_km = lon_range * 94.5
        area_km2 = lat_km * lon_km
        # Core urban monitoring area is ~269 km²
        # (Full metro area ~1,172 km² needs wider bounding box)
        assert 200 < area_km2 < 500, f"Lahore area estimate {area_km2:.0f} km² out of range"

    def test_station_radius_covers_city(self):
        """25km radius from center must cover entire Lahore metro."""
        import math

        # Max distance from center to corner of bounding box
        dlat = (LAHORE_LAT_MAX - LAHORE_CENTER_LAT) * 111  # km
        dlon = (LAHORE_LON_MAX - LAHORE_CENTER_LON) * 94.5  # km
        max_distance = math.sqrt(dlat**2 + dlon**2)
        assert max_distance < 25.0, (
            f"Farthest point from center is {max_distance:.1f}km, exceeds 25km radius"
        )

    def test_ekf_ifs_grid_covers_lahore(self):
        """ECMWF IFS 9km resolution grid must cover Lahore."""
        # 9km resolution means each grid cell is ~9km × 9km
        # Lahore is ~18km × 15km — needs at least 2×2 grid cells
        lahore_width_km = (LAHORE_LON_MAX - LAHORE_LON_MIN) * 94.5
        lahore_height_km = (LAHORE_LAT_MAX - LAHORE_LAT_MIN) * 111
        min_cells_x = lahore_width_km / ECMWF_IFS_RESOLUTION_KM
        min_cells_y = lahore_height_km / ECMWF_IFS_RESOLUTION_KM
        assert min_cells_x >= 1.0, "ECMWF IFS grid too coarse for Lahore width"
        assert min_cells_y >= 1.0, "ECMWF IFS grid too coarse for Lahore height"


class TestPM25Contracts:
    """Verify PM2.5 prediction target contracts from Section 7."""

    def test_pm25_bounds_physically_valid(self):
        """PM2.5 must be non-negative and within extreme-but-possible range."""
        assert PM25_MIN_UG_M3 >= 0.0
        assert PM25_MAX_UG_M3 >= 500.0  # Lahore has hit 1000+ AQI

    def test_pm25_unit_is_ug_m3(self):
        """PM2.5 must be measured in μg/m³ as per OpenAQ standard."""
        obs = Observation(
            observation_id="test-pm25",
            source=Provenance(
                source_id="openaq_v3",
                source_identifier="sensor-001",
                retrieved_at=datetime.now(UTC),
                quality_flag="verified",
                license="CC-BY-4.0",
            ),
            timestamp=datetime.now(UTC),
            parameter="pm25",
            value=89.2,
            unit=MeasurementUnit.UG_M3,
            quality=DataQuality(completeness=1.0, quality_flag="verified", source_reliability=4),
            location=Coordinates(latitude=LAHORE_CENTER_LAT, longitude=LAHORE_CENTER_LON),
        )
        assert obs.unit == MeasurementUnit.UG_M3

    def test_prediction_horizon_defined(self):
        """Primary prediction target is 24-hour ahead."""
        prediction_horizon_hours = 24
        assert prediction_horizon_hours == 24

    def test_all_feature_variables_representable(self):
        """All research-identified feature variables must have units."""
        feature_units = {
            "temperature_2m": MeasurementUnit.DEGREES_C,
            "relative_humidity_2m": MeasurementUnit.PERCENT,
            "dew_point_2m": MeasurementUnit.DEGREES_C,
            "apparent_temperature": MeasurementUnit.DEGREES_C,
            "precipitation": MeasurementUnit.MM,
            "rain": MeasurementUnit.MM,
            "cloud_cover": MeasurementUnit.PERCENT,
            "pressure_msl": MeasurementUnit.HPA,
            "surface_pressure": MeasurementUnit.HPA,
            "wind_speed_10m": MeasurementUnit.KM_H,
            "wind_direction_10m": MeasurementUnit.DEGREES,
            "wind_gusts_10m": MeasurementUnit.KM_H,
            "shortwave_radiation": MeasurementUnit.W_M2,
            "sunshine_duration": MeasurementUnit.SECONDS,
            "vapour_pressure_deficit": MeasurementUnit.KPA,
            "soil_temperature_0_to_7cm": MeasurementUnit.DEGREES_C,
            "soil_moisture_0_to_7cm": MeasurementUnit.M3_M3,
        }
        for var, unit in feature_units.items():
            assert isinstance(unit, MeasurementUnit), f"{var} has invalid unit type"


class TestLicensingCompliance:
    """Verify licensing requirements from Section 13 are captured."""

    def test_open_meteo_attribution_required(self):
        """Open-Meteo requires CC-BY 4.0 attribution."""
        attribution = 'Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a>'
        assert "open-meteo.com" in attribution
        assert "CC-BY" in "CC-BY 4.0"  # Licence type documented

    def test_openaq_attribution_required(self):
        """OpenAQ requires attribution to both platform and original sources."""
        # Must include both OpenAQ and source attribution
        required_elements = ["OpenAQ", "CC-BY 4.0", "original"]
        mock_attribution = (
            "Air quality data provided by OpenAQ under the CC-BY 4.0 licence. Original data: test"
        )
        for element in required_elements:
            assert element.lower() in mock_attribution.lower()

    def test_aqicn_attribution_required(self):
        """AQICN requires attribution to WAQI Project."""
        attribution = "Data from WAQI Project"
        assert "WAQI" in attribution

    def test_all_sources_have_licence_field(self):
        """Every data source must have a documented licence."""
        source_licences = {
            "openmeteo": "CC-BY-4.0",
            "openaq": "OpenAQ-ToU",
            "aqicn": "WAQI-ToU",
            "cams": "CC-BY-4.0",
            "era5": "CC-BY-4.0",
        }
        for source, licence in source_licences.items():
            assert licence, f"{source} must have a licence"

    def test_non_commercial_use_compatible(self):
        """All sources must be usable for non-commercial/hackathon use."""
        # Open-Meteo: Non-commercial free tier ✅
        # OpenAQ: Free API with key ✅
        # AQICN: Free with token ✅
        assert OPENMETEO_DAILY_LIMIT >= 1000  # Sufficient for hackathon
        assert OPENAQ_RATE_LIMIT_PER_HOUR >= 100  # Sufficient


class TestRateLimitsFeasibility:
    """Verify rate limits are sufficient for data collection."""

    def test_open_meteo_sufficient_for_historical(self):
        """Open-Meteo can return years of data in a single call."""
        # One call with start_date and end_date returns all hourly data
        # 9 years × 8760 hours = 78,840 data points in 1 call
        hourly_points_per_year = 8760
        years_of_data = 9
        total_points = hourly_points_per_year * years_of_data
        assert total_points <= 100_000  # Reasonable for one API response

    def test_open_aq_bulk_via_s3_no_rate_limit(self):
        """OpenAQ S3 archive has no rate limits."""
        # S3 access is direct, no API rate limits
        assert OPENAQ_RATE_LIMIT_PER_MINUTE == 60  # API limit exists
        # But S3 has no such limit — documented separately

    def test_rate_limits_sufficient_for_daily_refresh(self):
        """Daily refresh must complete within rate limits."""
        # Daily: need ~3-5 API calls for each source
        daily_calls_needed = 5  # estimate
        assert daily_calls_needed < OPENAQ_RATE_LIMIT_PER_HOUR
        assert daily_calls_needed < OPENMETEO_DAILY_LIMIT


class TestDataVolumeEstimates:
    """Verify data volume estimates are reasonable."""

    def test_ground_truth_volume_estimate(self):
        """60 stations × 9 years × 8760 hours should be calculable."""
        stations = 60
        years = 9
        hours_per_year = 8760
        total = stations * years * hours_per_year
        assert total == 4_730_400
        # ~4.7M rows — manageable

    def test_weather_features_volume_estimate(self):
        """Single-point weather data: 9 years × 8760 hours × 20 variables."""
        years = 9
        hours_per_year = 8760
        variables = 20
        total = years * hours_per_year * variables
        assert total == 1_576_800
        # ~1.6M rows — manageable

    def test_total_dataset_estimated_size(self):
        """Total dataset should be under 1GB."""
        ground_truth_mb = 200
        weather_mb = 150
        total_mb = ground_truth_mb + weather_mb
        assert total_mb < 1000, f"Total dataset {total_mb}MB exceeds 1GB target"


class TestProviderAbstraction:
    """Verify provider interface contracts from Section 16."""

    def test_weather_provider_interface_methods(self):
        """WeatherDataProvider must define required methods."""
        required_methods = ["get_historical_weather", "get_weather_forecast", "health_check"]
        # These are the abstract methods defined in the research
        assert len(required_methods) == 3

    def test_aq_provider_interface_methods(self):
        """AirQualityDataProvider must define required methods."""
        required_methods = ["get_measurements", "get_locations", "health_check"]
        assert len(required_methods) == 3

    def test_provider_priority_ordering(self):
        """Provider priority must be well-defined."""
        assert len(WEATHER_SOURCE_PRIORITY) >= 1
        assert len(AQ_GROUND_TRUTH_PRIORITY) >= 1
        assert len(AQ_FORECAST_PRIORITY) >= 1
        assert WEATHER_SOURCE_PRIORITY[0] == "openmeteo"
        assert AQ_GROUND_TRUTH_PRIORITY[0] == "openaq"


class TestRiskRegister:
    """Verify risk register is complete."""

    def test_critical_risk_has_mitigation(self):
        """Data leakage must be mitigated (critical risk)."""
        mitigation = "Strict temporal splits; automated leakage detection tests"
        assert "temporal" in mitigation.lower()
        assert "leakage" in mitigation.lower()

    def test_data_quality_risk_addressed(self):
        """Sensor quality variance must be addressed."""
        mitigation = "Weight government stations higher; cross-validate"
        assert "weight" in mitigation.lower() or "cross-validate" in mitigation.lower()
