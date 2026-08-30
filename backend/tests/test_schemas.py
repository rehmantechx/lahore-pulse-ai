"""Tests for domain schemas and contracts.

Verifies that:
- Models enforce validation rules
- Field constraints are respected
- Different data types cannot be accidentally confused
- Provenance fields are present where required
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.models.common import (
    Confidence,
    DataQuality,
    DataSourceType,
    MeasurementUnit,
)
from app.domain.models.forecast import Forecast, ForecastHorizon
from app.domain.models.location import LAHORE_CENTER, Area, Coordinates, Station
from app.domain.models.observation import DataSource, Observation
from app.domain.models.prediction import Prediction
from app.domain.models.risk import RiskAssessment, RiskType, Severity

# ── Common Types ──────────────────────────────────────────────────


class TestConfidence:
    def test_valid_confidence(self) -> None:
        c = Confidence(level=0.85)
        assert c.level == 0.85
        assert c.method is None

    def test_confidence_with_method(self) -> None:
        c = Confidence(level=0.9, method="cross_validation")
        assert c.method == "cross_validation"

    def test_confidence_with_interval(self) -> None:
        c = Confidence(level=0.8, interval_lower=0.7, interval_upper=0.9)
        assert c.interval_lower == 0.7
        assert c.interval_upper == 0.9

    def test_confidence_rejects_negative(self) -> None:
        with pytest.raises(ValidationError):
            Confidence(level=-0.1)

    def test_confidence_rejects_above_one(self) -> None:
        with pytest.raises(ValidationError):
            Confidence(level=1.5)

    def test_confidence_boundary_zero(self) -> None:
        c = Confidence(level=0.0)
        assert c.level == 0.0

    def test_confidence_boundary_one(self) -> None:
        c = Confidence(level=1.0)
        assert c.level == 1.0


class TestMeasurementUnit:
    def test_units_are_string_enums(self) -> None:
        assert isinstance(MeasurementUnit.UG_M3.value, str)
        assert MeasurementUnit.UG_M3.value == "ug/m3"

    def test_units_include_key_types(self) -> None:
        expected = {"aqi_index", "ug/m3", "deg_c", "pct", "mm", "m/s", "hPa"}
        actual = {unit.value for unit in MeasurementUnit}
        assert expected.issubset(actual)


class TestDataQuality:
    def test_quality_has_required_states(self) -> None:
        required = {"valid", "suspect", "missing", "interpolated", "unverified"}
        actual = {q.value for q in DataQuality}
        assert required.issubset(actual)


# ── Location Models ───────────────────────────────────────────────


class TestCoordinates:
    def test_valid_coordinates(self) -> None:
        coords = Coordinates(latitude=31.5204, longitude=74.3587)
        assert coords.latitude == 31.5204
        assert coords.longitude == 74.3587

    def test_rejects_latitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            Coordinates(latitude=100.0, longitude=74.3587)

    def test_rejects_longitude_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            Coordinates(latitude=31.5204, longitude=200.0)

    def test_lahore_center_reference(self) -> None:
        assert LAHORE_CENTER.latitude == 31.5204
        assert LAHORE_CENTER.longitude == 74.3587

    def test_optional_altitude(self) -> None:
        coords = Coordinates(latitude=31.5, longitude=74.3, altitude_meters=217.0)
        assert coords.altitude_meters == 217.0


class TestStation:
    def test_station_creation(self) -> None:
        station = Station(
            station_id="openaq-lhr-001",
            name="Lahore Station 1",
            location=Coordinates(latitude=31.52, longitude=74.35),
            source_id="openaq",
        )
        assert station.active is True
        assert station.source_id == "openaq"


class TestArea:
    def test_area_creation(self) -> None:
        area = Area(
            area_id="lahore-d01",
            name="Gulberg",
            center=Coordinates(latitude=31.51, longitude=74.34),
        )
        assert area.area_type == "neighbourhood"


# ── Observation Models ────────────────────────────────────────────


class TestDataSource:
    def test_data_source_creation(self) -> None:
        source = DataSource(
            source_id="openaq",
            name="OpenAQ",
            provider="OpenAQ",
            source_type=DataSourceType.AIR_QUALITY,
        )
        assert source.source_id == "openaq"
        assert source.license is None


class TestObservation:
    def _make_observation(self, **kwargs) -> Observation:
        defaults = {
            "observation_id": "obs-001",
            "source": DataSource(
                source_id="openaq",
                name="OpenAQ",
                provider="OpenAQ",
                source_type=DataSourceType.AIR_QUALITY,
            ),
            "location": Coordinates(latitude=31.5204, longitude=74.3587),
            "timestamp": datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC),
            "parameter": "pm25",
            "value": 42.5,
            "unit": MeasurementUnit.UG_M3,
        }
        defaults.update(kwargs)
        return Observation(**defaults)

    def test_observation_has_provenance(self) -> None:
        """Observations must be traceable to their source."""
        obs = self._make_observation()
        assert obs.source.source_id == "openaq"
        assert obs.timestamp is not None
        assert obs.retrieved_at is not None

    def test_observation_default_quality(self) -> None:
        obs = self._make_observation()
        assert obs.quality == DataQuality.UNVERIFIED

    def test_observation_explicit_quality(self) -> None:
        obs = self._make_observation(quality=DataQuality.VALID)
        assert obs.quality == DataQuality.VALID

    def test_observation_is_not_prediction(self) -> None:
        """Type system should prevent confusion."""
        obs = self._make_observation()
        pred = Prediction(
            prediction_id="pred-001",
            model_id="test-model",
            model_version="v1",
            parameter="pm25",
            location_lat=31.5204,
            location_lon=74.3587,
            created_at=datetime.now(UTC),
            target_time=datetime.now(UTC),
            value=42.5,
            unit=MeasurementUnit.UG_M3,
        )
        # Different types — should not be equal
        assert type(obs) is not type(pred)


# ── Forecast Models ───────────────────────────────────────────────


class TestForecast:
    def test_forecast_creation(self) -> None:
        forecast = Forecast(
            forecast_id="fc-001",
            source_id="open-meteo",
            parameter="temperature",
            location_lat=31.52,
            location_lon=74.35,
            issued_at=datetime(2026, 8, 14, tzinfo=UTC),
            target_time=datetime(2026, 8, 15, tzinfo=UTC),
            value=38.5,
            unit=MeasurementUnit.DEGREES_CELSIUS,
            horizon=ForecastHorizon.DAILY,
        )
        assert forecast.source_id == "open-meteo"
        assert forecast.confidence is None


# ── Prediction Models ─────────────────────────────────────────────


class TestPrediction:
    def test_prediction_creation(self) -> None:
        pred = Prediction(
            prediction_id="pred-001",
            model_id="aqi-forecast-v1",
            model_version="v1.0.0",
            parameter="aqi",
            location_lat=31.52,
            location_lon=74.35,
            created_at=datetime.now(UTC),
            target_time=datetime(2026, 8, 15, tzinfo=UTC),
            value=155.0,
            unit=MeasurementUnit.AQI_INDEX,
            confidence=Confidence(level=0.78),
        )
        assert pred.model_id == "aqi-forecast-v1"
        assert pred.confidence.level == 0.78

    def test_prediction_must_have_model_info(self) -> None:
        """Predictions must be traceable to their model."""
        with pytest.raises(ValidationError):
            Prediction(
                prediction_id="pred-002",
                # Missing model_id and model_version
                parameter="aqi",
                location_lat=31.52,
                location_lon=74.35,
                created_at=datetime.now(UTC),
                target_time=datetime.now(UTC),
                value=100.0,
                unit=MeasurementUnit.AQI_INDEX,
            )


# ── Risk Models ───────────────────────────────────────────────────


class TestRiskAssessment:
    def test_risk_assessment_creation(self) -> None:
        risk = RiskAssessment(
            assessment_id="risk-001",
            risk_type=RiskType.AIR_QUALITY,
            location_lat=31.52,
            location_lon=74.35,
            assessed_at=datetime.now(UTC),
            target_time=datetime(2026, 8, 15, tzinfo=UTC),
            severity=Severity.HIGH,
            score=0.75,
            contributing_factors=["high_pm25", "unfavorable_wind"],
        )
        assert risk.severity == Severity.HIGH
        assert len(risk.contributing_factors) == 2

    def test_risk_score_boundaries(self) -> None:
        """Risk score must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            RiskAssessment(
                assessment_id="risk-002",
                risk_type=RiskType.HEAT,
                location_lat=31.52,
                location_lon=74.35,
                assessed_at=datetime.now(UTC),
                target_time=datetime.now(UTC),
                severity=Severity.LOW,
                score=1.5,  # Invalid
            )
