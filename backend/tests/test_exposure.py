"""Tests for Exposure Intelligence geometry service.

Covers:
- Wind direction conversions
- Bearing to label mapping
- Wind speed to distance calculation
- Haversine destination point
- Sector polygon generation
- Cone polygon generation
- Full exposure geometry computation (with and without wind)
- API endpoint (standalone + within /analyze response)
- Demo fixture
- Graceful degradation
"""

from __future__ import annotations

import math

import pytest

from app.application.services.exposure import (
    bearing_to_label,
    compute_exposure_geometry,
    create_cone_polygon,
    create_sector_polygon,
    destination_point,
    wind_speed_to_distance_km,
    wind_to_movement_bearing,
)


# ── Wind Direction Helpers ────────────────────────────────────


class TestWindToMovementBearing:
    """Tests for meteorological FROM-degrees to movement bearing conversion."""

    def test_east_becomes_west(self):
        """Wind FROM East (90°) moves TO West (270°)."""
        assert wind_to_movement_bearing(90.0) == 270.0

    def test_north_becomes_south(self):
        """Wind FROM North (0°) moves TO South (180°)."""
        assert wind_to_movement_bearing(0.0) == 180.0

    def test_south_becomes_north(self):
        """Wind FROM South (180°) moves TO North (0°/360°)."""
        assert wind_to_movement_bearing(180.0) == 0.0

    def test_west_becomes_east(self):
        """Wind FROM West (270°) moves TO East (90°)."""
        assert wind_to_movement_bearing(270.0) == 90.0

    def test_northwest_becomes_southeast(self):
        """Wind FROM Northwest (315°) moves TO Southeast (135°)."""
        assert wind_to_movement_bearing(315.0) == 135.0

    def test_wrapping(self):
        """Bearing wraps around 360°."""
        assert wind_to_movement_bearing(300.0) == 120.0
        assert wind_to_movement_bearing(350.0) == 170.0


class TestBearingToLabel:
    """Tests for bearing to human-readable direction label."""

    def test_north(self):
        assert bearing_to_label(0.0) == "North"
        assert bearing_to_label(10.0) == "North"
        assert bearing_to_label(355.0) == "North"

    def test_east(self):
        assert bearing_to_label(90.0) == "East"
        assert bearing_to_label(70.0) == "East"

    def test_south(self):
        assert bearing_to_label(180.0) == "South"
        assert bearing_to_label(170.0) == "South"

    def test_west(self):
        assert bearing_to_label(270.0) == "West"
        assert bearing_to_label(250.0) == "West"

    def test_northeast(self):
        assert bearing_to_label(45.0) == "Northeast"
        assert bearing_to_label(60.0) == "Northeast"

    def test_southeast(self):
        assert bearing_to_label(135.0) == "Southeast"

    def test_southwest(self):
        assert bearing_to_label(225.0) == "Southwest"

    def test_northwest(self):
        assert bearing_to_label(315.0) == "Northwest"


class TestWindSpeedToDistance:
    """Tests for wind speed to conservative exposure distance."""

    def test_default_for_none(self):
        """None wind speed returns default."""
        result = wind_speed_to_distance_km(None)
        assert result == 10.0

    def test_low_wind(self):
        """Low wind returns minimum 3.0 km."""
        result = wind_speed_to_distance_km(0.5)
        assert result == 3.0

    def test_moderate_wind(self):
        """Moderate wind: speed * 3.0."""
        result = wind_speed_to_distance_km(3.0)
        assert result == 9.0

    def test_high_wind_capped(self):
        """High wind capped at 15.0 km."""
        result = wind_speed_to_distance_km(10.0)
        assert result == 15.0

    def test_negative_wind(self):
        """Negative wind returns default."""
        result = wind_speed_to_distance_km(-1.0)
        assert result == 10.0


# ── Coordinate Geometry ────────────────────────────────────────


class TestDestinationPoint:
    """Tests for haversine destination point calculation."""

    def test_move_north(self):
        """Moving north increases latitude."""
        lat, lng = destination_point(31.5204, 74.3587, 0.0, 1.0)
        assert lat > 31.5204
        assert abs(lng - 74.3587) < 0.01  # Should stay near same longitude

    def test_move_east(self):
        """Moving east increases longitude."""
        lat, lng = destination_point(31.5204, 74.3587, 90.0, 1.0)
        assert lng > 74.3587
        assert abs(lat - 31.5204) < 0.01

    def test_move_south(self):
        """Moving south decreases latitude."""
        lat, lng = destination_point(31.5204, 74.3587, 180.0, 1.0)
        assert lat < 31.5204

    def test_move_west(self):
        """Moving west decreases longitude."""
        lat, lng = destination_point(31.5204, 74.3587, 270.0, 1.0)
        assert lng < 74.3587

    def test_zero_distance(self):
        """Zero distance returns same point."""
        lat, lng = destination_point(31.5204, 74.3587, 45.0, 0.0)
        assert abs(lat - 31.5204) < 0.0001
        assert abs(lng - 74.3587) < 0.0001


class TestSectorPolygon:
    """Tests for investigation corridor sector polygon."""

    def test_returns_coordinate_list(self):
        """Sector returns list of [lat, lng] coordinates."""
        coords = create_sector_polygon(31.52, 74.35, 90.0, 60.0, 8.0)
        assert isinstance(coords, list)
        assert len(coords) > 5
        for c in coords:
            assert len(c) == 2

    def test_starts_and_ends_at_center(self):
        """Polygon starts and ends at the center point."""
        coords = create_sector_polygon(31.52, 74.35, 90.0, 60.0, 8.0)
        assert coords[0] == coords[-1]

    def test_deterministic(self):
        """Same inputs produce same output."""
        coords1 = create_sector_polygon(31.52, 74.35, 90.0, 60.0, 8.0)
        coords2 = create_sector_polygon(31.52, 74.35, 90.0, 60.0, 8.0)
        assert coords1 == coords2

    def test_different_directions(self):
        """Different bearings produce different polygons."""
        east = create_sector_polygon(31.52, 74.35, 90.0, 60.0, 8.0)
        west = create_sector_polygon(31.52, 74.35, 270.0, 60.0, 8.0)
        assert east != west


class TestConePolygon:
    """Tests for exposure path cone polygon."""

    def test_returns_coordinate_list(self):
        """Cone returns list of [lat, lng] coordinates."""
        coords = create_cone_polygon(31.52, 74.35, 270.0, 60.0, 9.6)
        assert isinstance(coords, list)
        assert len(coords) > 5
        for c in coords:
            assert len(c) == 2

    def test_starts_at_center(self):
        """Cone starts at the center point."""
        coords = create_cone_polygon(31.52, 74.35, 270.0, 60.0, 9.6)
        assert coords[0] == [31.52, 74.35]

    def test_deterministic(self):
        """Same inputs produce same output."""
        coords1 = create_cone_polygon(31.52, 74.35, 270.0, 60.0, 9.6)
        coords2 = create_cone_polygon(31.52, 74.35, 270.0, 60.0, 9.6)
        assert coords1 == coords2


# ── Full Geometry Computation ──────────────────────────────────


class TestComputeExposureGeometry:
    """Tests for the main compute_exposure_geometry function."""

    def test_returns_required_fields(self):
        """Response includes all required top-level fields."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
            pm25=165.0, severity="episode", trajectory="rising",
        )
        assert "event_location" in result
        assert "investigation_area" in result
        assert "exposure_path" in result
        assert "vulnerable_locations" in result
        assert "metadata" in result

    def test_event_location_populated(self):
        """Event location includes coordinates and readings."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
            pm25=165.0, severity="episode",
        )
        loc = result["event_location"]
        assert loc["lat"] == 31.5204
        assert loc["lng"] == 74.3587
        assert loc["pm25"] == 165.0
        assert loc["severity"] == "episode"

    def test_investigation_area_upwind(self):
        """Investigation area points upwind (FROM direction)."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
        )
        area = result["investigation_area"]
        assert area["type"] == "upwind_investigation_corridor"
        assert area["direction_degrees"] == 90.0
        assert area["direction_label"] == "From East"
        assert area["priority"] == "HIGH"
        assert area["requires_ground_verification"] is True
        assert "coordinates" in area
        assert len(area["coordinates"]) > 5

    def test_exposure_path_downwind(self):
        """Exposure path extends downwind (movement direction)."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
        )
        path = result["exposure_path"]
        assert path["type"] == "approximate_downwind_cone"
        assert path["direction_degrees"] == 270.0
        assert path["direction_label"] == "Moving toward West"
        assert "coordinates" in path
        assert len(path["coordinates"]) > 5

    def test_metadata_populated(self):
        """Metadata includes wind parameters."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
        )
        meta = result["metadata"]
        assert meta["wind_direction_degrees"] == 90.0
        assert meta["movement_bearing"] == 270.0
        assert meta["wind_speed_ms"] == 3.2
        assert meta["computed_at"] is not None

    def test_no_wind_data_returns_radial_zone(self):
        """Missing wind direction returns a radial investigation zone."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=None, wind_speed_ms=None,
        )
        area = result["investigation_area"]
        assert area["type"] == "radial_zone"
        assert result["exposure_path"] is None

    def test_deterministic(self):
        """Same inputs produce same geometry (no AI involved)."""
        r1 = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
            pm25=165.0, severity="episode", trajectory="rising",
        )
        r2 = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
            pm25=165.0, severity="episode", trajectory="rising",
        )
        # Coordinates are deterministic
        assert r1["investigation_area"]["coordinates"] == r2["investigation_area"]["coordinates"]
        assert r1["exposure_path"]["coordinates"] == r2["exposure_path"]["coordinates"]

    def test_vulnerable_locations_structure(self):
        """Vulnerable locations have correct structure."""
        result = compute_exposure_geometry(
            lat=31.5204, lng=74.3587,
            wind_direction_degrees=90.0, wind_speed_ms=3.2,
        )
        vuln = result["vulnerable_locations"]
        assert "schools" in vuln
        assert "hospitals" in vuln
        assert "summary" in vuln
        assert "schools_in_path" in vuln["summary"]
        assert "hospitals_in_path" in vuln["summary"]
