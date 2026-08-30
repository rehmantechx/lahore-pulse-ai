"""Exposure Intelligence — deterministic wind-driven geometry.

Calculates approximate map geometry for:
1. Upwind investigation corridor (where to investigate first)
2. Downwind exposure cone (where exposure may travel)
3. Vulnerable locations within the exposure path

ALL geometry is deterministic — AI is never involved in coordinate
calculation.  Wind direction is an investigation signal, NOT source
attribution.  The geometry is an APPROXIMATION for decision support.

Scientific constraints:
- Corridor and cone are approximate sector/polygon shapes
- Default cone width is ±30 degrees (60° total)
- Distance defaults based on wind speed (conservative)
- Overpass API results are limited (max 10 per type)
- Graceful degradation: missing data never breaks the response
"""

from __future__ import annotations

import math
import time
from typing import Any

from loguru import logger


# ── Constants ──────────────────────────────────────────────────

EARTH_RADIUS_KM = 6371.0
DEFAULT_CONE_WIDTH_DEGREES = 60.0  # ±30 degrees
DEFAULT_CORRIDOR_WIDTH_DEGREES = 60.0
DEFAULT_CORRIDOR_LENGTH_KM = 8.0
DEFAULT_CONE_LENGTH_KM = 10.0
DEFAULT_VULNERABLE_RADIUS_KM = 5.0
MAX_SCHOOLS = 10
MAX_HOSPITALS = 10

# Overpass API endpoint (read-only, public)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Cache for vulnerable locations (simple time-based)
_vulnerable_cache: dict[str, tuple[float, list[dict]]] = {}
_VULNERABLE_CACHE_TTL = 300  # 5 minutes


# ── Wind Direction Helpers ─────────────────────────────────────

def wind_to_movement_bearing(from_degrees: float) -> float:
    """Convert meteorological FROM-degrees to movement bearing.

    Meteorological convention: degrees indicate where wind COMES FROM.
    Movement bearing is the direction wind is GOING TO.

    Example:
        Wind FROM East (90°) → moves TO West (270°)
        Wind FROM North (0°) → moves TO South (180°)
    """
    return (from_degrees + 180.0) % 360.0


def bearing_to_label(bearing: float) -> str:
    """Convert a bearing in degrees to a human-readable direction label."""
    labels = [
        (22.5, "North"),
        (67.5, "Northeast"),
        (112.5, "East"),
        (157.5, "Southeast"),
        (202.5, "South"),
        (247.5, "Southwest"),
        (292.5, "West"),
        (337.5, "Northwest"),
        (360.0, "North"),
    ]
    for threshold, label in labels:
        if bearing < threshold:
            return label
    return "North"


def wind_speed_to_distance_km(wind_speed_ms: float | None) -> float:
    """Convert wind speed to conservative exposure distance.

    Uses a simple linear approximation for decision support.
    Higher wind speeds push pollutants further downwind.
    """
    if wind_speed_ms is None or wind_speed_ms < 0:
        return DEFAULT_CONE_LENGTH_KM
    # Conservative: 2-3 km per m/s, capped at 15 km
    distance = max(3.0, min(wind_speed_ms * 3.0, 15.0))
    return round(distance, 1)


# ── Coordinate Geometry ────────────────────────────────────────


def destination_point(
    lat: float,
    lng: float,
    bearing_deg: float,
    distance_km: float,
) -> tuple[float, float]:
    """Calculate a destination point given start, bearing, and distance.

    Uses the haversine formula for great-circle distance on Earth.
    """
    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)
    bearing_rad = math.radians(bearing_deg)
    angular_dist = distance_km / EARTH_RADIUS_KM

    dest_lat = math.asin(
        math.sin(lat_rad) * math.cos(angular_dist)
        + math.cos(lat_rad) * math.sin(angular_dist) * math.cos(bearing_rad)
    )
    dest_lng = lng_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat_rad),
        math.cos(angular_dist) - math.sin(lat_rad) * math.sin(dest_lat),
    )

    return (math.degrees(dest_lat), math.degrees(dest_lng))


def create_sector_polygon(
    center_lat: float,
    center_lng: float,
    direction_bearing: float,
    width_degrees: float,
    radius_km: float,
    num_points: int = 16,
) -> list[list[float]]:
    """Create a sector (pie-slice) polygon for an investigation corridor.

    Args:
        center_lat: Center latitude of the sector.
        center_lng: Center longitude of the sector.
        direction_bearing: Direction the sector points (degrees from North).
        width_degrees: Total angular width of the sector.
        radius_km: Radius of the sector in kilometers.
        num_points: Number of points along the arc.

    Returns:
        List of [lat, lng] coordinates forming a closed polygon.
    """
    half_width = width_degrees / 2.0
    start_bearing = (direction_bearing - half_width) % 360.0
    end_bearing = (direction_bearing + half_width) % 360.0

    coords: list[list[float]] = []

    # Center point
    coords.append([center_lat, center_lng])

    # Arc points
    for i in range(num_points + 1):
        t = i / num_points
        if start_bearing < end_bearing:
            bearing = start_bearing + t * (end_bearing - start_bearing)
        else:
            # Wraps around 360°
            bearing = (start_bearing + t * (360.0 - start_bearing + end_bearing)) % 360.0

        pt = destination_point(center_lat, center_lng, bearing, radius_km)
        coords.append([pt[0], pt[1]])

    # Close the polygon
    coords.append(coords[0])

    return coords


def create_cone_polygon(
    center_lat: float,
    center_lng: float,
    direction_bearing: float,
    cone_width_degrees: float,
    length_km: float,
    num_points: int = 20,
) -> list[list[float]]:
    """Create a cone-shaped polygon for an exposure path.

    The cone starts at center and widens as it extends in the given direction.

    Args:
        center_lat: Start point latitude.
        center_lng: Start point longitude.
        direction_bearing: Direction the cone extends (degrees from North).
        cone_width_degrees: Total angular width at the far end.
        length_km: Length of the cone in kilometers.
        num_points: Number of points along each side.

    Returns:
        List of [lat, lng] coordinates forming a closed polygon.
    """
    half_width = cone_width_degrees / 2.0
    left_bearing = (direction_bearing - half_width) % 360.0
    right_bearing = (direction_bearing + half_width) % 360.0

    coords: list[list[float]] = []

    # Start point (tip of cone)
    coords.append([center_lat, center_lng])

    # Left edge points (from near to far)
    for i in range(1, num_points + 1):
        t = i / num_points
        # Cone widens: use linear interpolation of width
        dist = t * length_km
        # Slight curve: widening is proportional to distance
        current_half_width = half_width * t
        left = (direction_bearing - current_half_width) % 360.0
        pt = destination_point(center_lat, center_lng, left, dist)
        coords.append([pt[0], pt[1]])

    # Far end point (center of far edge)
    far_center = destination_point(center_lat, center_lng, direction_bearing, length_km)
    coords.append([far_center[0], far_center[1]])

    # Right edge points (from far to near)
    for i in range(num_points, 0, -1):
        t = i / num_points
        dist = t * length_km
        current_half_width = half_width * t
        right = (direction_bearing + current_half_width) % 360.0
        pt = destination_point(center_lat, center_lng, right, dist)
        coords.append([pt[0], pt[1]])

    # Close the polygon
    coords.append(coords[0])

    return coords


# ── Vulnerable Locations (Overpass API) ────────────────────────


def fetch_vulnerable_locations(
    center_lat: float,
    center_lng: float,
    radius_km: float = DEFAULT_VULNERABLE_RADIUS_KM,
) -> dict[str, Any]:
    """Fetch schools and hospitals near a location using Overpass API.

    Queries OpenStreetMap Overpass API for schools and hospitals within
    the specified radius.  Results are cached for 5 minutes.

    Graceful degradation:
    - API failure returns empty lists (does not break the map)
    - Maximum 10 schools and 10 hospitals returned
    - Only locations with valid coordinates are included

    Args:
        center_lat: Center latitude for the search.
        center_lng: Center longitude for the search.
        radius_km: Search radius in kilometers.

    Returns:
        Dict with 'schools', 'hospitals', and 'summary' keys.
    """
    cache_key = f"{center_lat:.3f},{center_lng:.3f},{radius_km}"
    now = time.time()

    # Check cache
    if cache_key in _vulnerable_cache:
        cached_time, cached_data = _vulnerable_cache[cache_key]
        if now - cached_time < _VULNERABLE_CACHE_TTL:
            logger.debug("Vulnerable locations cache hit")
            return cached_data

    schools: list[dict[str, Any]] = []
    hospitals: list[dict[str, Any]] = []

    try:
        import httpx

        radius_m = int(radius_km * 1000)

        # Overpass QL query for schools and hospitals
        query = f"""
        [out:json][timeout:10];
        (
          node["amenity"="school"](around:{radius_m},{center_lat},{center_lng});
          way["amenity"="school"](around:{radius_m},{center_lat},{center_lng});
          node["amenity"="hospital"](around:{radius_m},{center_lat},{center_lng});
          way["amenity"="hospital"](around:{radius_m},{center_lat},{center_lng});
        );
        out center body;
        """

        response = httpx.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=15.0,
        )
        response.raise_for_status()

        data = response.json()
        elements = data.get("elements", [])

        for element in elements:
            # Extract coordinates (node has lat/lon directly, way has center)
            lat = element.get("lat") or (element.get("center", {}).get("lat"))
            lng = element.get("lon") or (element.get("center", {}).get("lon"))

            if lat is None or lng is None:
                continue

            tags = element.get("tags", {})
            name = tags.get("name", tags.get("name:en", "Unnamed"))
            amenity = tags.get("amenity", "")

            location = {
                "name": name,
                "type": amenity,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
            }

            if amenity == "school" and len(schools) < MAX_SCHOOLS:
                schools.append(location)
            elif amenity == "hospital" and len(hospitals) < MAX_HOSPITALS:
                hospitals.append(location)

    except ImportError:
        logger.warning("httpx not available for Overpass API query")
    except httpx.TimeoutException:
        logger.warning("Overpass API timeout — returning empty vulnerable locations")
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Overpass API HTTP error",
            status=exc.response.status_code,
        )
    except Exception as exc:
        logger.warning("Overpass API query failed", error=str(exc))

    result = {
        "schools": schools,
        "hospitals": hospitals,
        "summary": {
            "schools_in_path": len(schools),
            "hospitals_in_path": len(hospitals),
        },
    }

    # Cache the result
    _vulnerable_cache[cache_key] = (now, result)

    return result


# ── Main Geometry Builder ──────────────────────────────────────


def compute_exposure_geometry(
    lat: float,
    lng: float,
    wind_direction_degrees: float | None,
    wind_speed_ms: float | None,
    pm25: float | None = None,
    severity: str | None = None,
    trajectory: str | None = None,
) -> dict[str, Any]:
    """Compute the full exposure intelligence geometry.

    This is the main entry point.  Given an observation location and
    wind data, returns:
    1. Investigation corridor (upwind)
    2. Exposure path (downwind cone)
    3. Vulnerable locations within the exposure area

    The geometry is deterministic — no AI is involved.

    Args:
        lat: Observation latitude.
        lng: Observation longitude.
        wind_direction_degrees: Meteorological FROM-degrees (0=N, 90=E, etc.)
        wind_speed_ms: Wind speed in meters per second.
        pm25: Current PM2.5 reading (for event label).
        severity: Severity classification (for event label).
        trajectory: Trend direction (for event label).

    Returns:
        Dict with investigation_area, exposure_path, and vulnerable_locations.
    """
    logger.info(
        "Computing exposure geometry",
        lat=lat,
        lng=lng,
        wind_dir=wind_direction_degrees,
        wind_speed=wind_speed_ms,
    )

    # ── Event location ──────────────────────────────────────
    event_location = {
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "pm25": pm25,
        "severity": severity,
        "trajectory": trajectory,
    }

    # ── Handle missing wind data ────────────────────────────
    if wind_direction_degrees is None:
        # No wind data — return event location only with generic geometry
        return {
            "event_location": event_location,
            "investigation_area": {
                "type": "radial_zone",
                "coordinates": create_sector_polygon(
                    lat, lng, 0, 360, 3.0, num_points=8
                ),
                "priority": "MEDIUM",
                "label": "Investigation Zone",
                "requires_ground_verification": True,
                "uncertainty": "Wind direction unavailable — showing radial zone around observation point",
            },
            "exposure_path": None,
            "vulnerable_locations": {
                "schools": [],
                "hospitals": [],
                "summary": {"schools_in_path": 0, "hospitals_in_path": 0},
            },
            "uncertainty": "Wind direction data unavailable. Geometry is approximate.",
        }

    # ── Compute wind movement ───────────────────────────────
    movement_bearing = wind_to_movement_bearing(wind_direction_degrees)
    corridor_bearing = wind_direction_degrees  # Upwind = where wind comes FROM

    # ── Investigation corridor (upwind) ─────────────────────
    corridor_length = DEFAULT_CORRIDOR_LENGTH_KM
    investigation_area = {
        "type": "upwind_investigation_corridor",
        "coordinates": create_sector_polygon(
            lat, lng, corridor_bearing, DEFAULT_CORRIDOR_WIDTH_DEGREES, corridor_length
        ),
        "center": {"lat": round(lat, 6), "lng": round(lng, 6)},
        "direction_degrees": round(wind_direction_degrees, 1),
        "direction_label": f"From {bearing_to_label(wind_direction_degrees)}",
        "distance_km": corridor_length,
        "width_degrees": DEFAULT_CORRIDOR_WIDTH_DEGREES,
        "priority": "HIGH",
        "label": "Priority Investigation Area",
        "requires_ground_verification": True,
        "uncertainty": (
            "Investigation corridor based on current wind direction. "
            "Local atmospheric conditions may alter actual pollutant transport."
        ),
    }

    # ── Exposure path (downwind cone) ───────────────────────
    cone_length = wind_speed_to_distance_km(wind_speed_ms)
    exposure_path = {
        "type": "approximate_downwind_cone",
        "coordinates": create_cone_polygon(
            lat, lng, movement_bearing, DEFAULT_CONE_WIDTH_DEGREES, cone_length
        ),
        "center": {"lat": round(lat, 6), "lng": round(lng, 6)},
        "direction_degrees": round(movement_bearing, 1),
        "direction_label": f"Moving toward {bearing_to_label(movement_bearing)}",
        "distance_km": cone_length,
        "cone_width_degrees": DEFAULT_CONE_WIDTH_DEGREES,
        "confidence": "MODERATE",
        "uncertainty": (
            "Approximate wind-driven trajectory. "
            "Local atmospheric conditions may change the actual dispersion path."
        ),
    }

    # ── Vulnerable locations ────────────────────────────────
    try:
        vulnerable = fetch_vulnerable_locations(
            lat, lng, radius_km=min(cone_length, DEFAULT_VULNERABLE_RADIUS_KM)
        )
    except Exception as exc:
        logger.warning("Vulnerable location fetch failed", error=str(exc))
        vulnerable = {
            "schools": [],
            "hospitals": [],
            "summary": {"schools_in_path": 0, "hospitals_in_path": 0},
        }

    # ── Assemble response ───────────────────────────────────
    result = {
        "event_location": event_location,
        "investigation_area": investigation_area,
        "exposure_path": exposure_path,
        "vulnerable_locations": vulnerable,
        "metadata": {
            "wind_direction_degrees": round(wind_direction_degrees, 1),
            "movement_bearing": round(movement_bearing, 1),
            "wind_speed_ms": wind_speed_ms,
            "corridor_length_km": corridor_length,
            "cone_length_km": cone_length,
            "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }

    logger.info(
        "Exposure geometry computed",
        corridor_bearing=corridor_bearing,
        cone_bearing=movement_bearing,
        cone_length=cone_length,
        schools=len(vulnerable.get("schools", [])),
        hospitals=len(vulnerable.get("hospitals", [])),
    )

    return result
