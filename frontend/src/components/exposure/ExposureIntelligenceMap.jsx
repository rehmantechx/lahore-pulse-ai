/**
 * ExposureIntelligenceMap — Wind-driven exposure visualization.
 *
 * NOT a generic AQI map. This component visually explains:
 * 1. Where the pollution event is being observed (event marker)
 * 2. Which UPWIND area should be investigated first (corridor polygon)
 * 3. Which DOWNWIND areas may experience exposure (cone polygon)
 * 4. Which vulnerable locations exist inside the exposure path
 *
 * DATA SOURCE:
 *   - Exposure geometry from GET /api/v1/investigation/exposure
 *   - Wind data from episode.source_compass
 *
 * Uses raw Leaflet API (consistent with OperationsMap.jsx pattern).
 * Does NOT use react-leaflet despite it being installed.
 *
 * COGNITIVE DESIGN:
 *   - Investigation corridor: ORANGE dashed outline → "investigate here"
 *   - Exposure path: RED semi-transparent fill → "exposure may reach here"
 *   - Event location: large PULSING marker → "this is where it is"
 *   - Vulnerable locations: BLUE squares (schools) / RED crosses (hospitals)
 *   - Legend overlay explains every visual element
 *   - Map communicates in 5 seconds: where, which direction, what's at risk
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Maximize2, Minimize2, AlertTriangle, Search, Shield } from 'lucide-react';
import { LAHORE_CENTER, LAHORE_ZOOM, MIN_ZOOM, MAX_ZOOM, MAP_TILES } from '../../constants';

// Fix default Leaflet marker icon paths (Vite bundling issue)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// ── Color Palette ────────────────────────────────────────────

const COLORS = {
  // Investigation corridor (upwind) — "investigate here"
  corridor: {
    fill: '#F59E0B',       // amber-500
    fillOpacity: 0.12,
    stroke: '#D97706',     // amber-600
    weight: 2.5,
    dashArray: '8, 6',
  },
  // Exposure path (downwind) — "exposure may reach here"
  exposure: {
    fill: '#EF4444',       // red-500
    fillOpacity: 0.10,
    stroke: '#DC2626',     // red-600
    weight: 2,
    dashArray: null,
  },
  // Event location — "this is where it is"
  event: {
    fill: '#DC2626',       // red-600
    stroke: '#ffffff',
    radius: 10,
  },
  // Vulnerable locations
  school: {
    fill: '#3B82F6',       // blue-500
    stroke: '#1D4ED8',     // blue-700
    radius: 6,
  },
  hospital: {
    fill: '#EF4444',       // red-500
    stroke: '#B91C1C',     // red-700
    radius: 6,
  },
};

// ── Helper: Create custom div icon for event marker ──────────

function createEventIcon() {
  return L.divIcon({
    className: 'exposure-event-marker',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    html: `
      <div style="
        width: 24px; height: 24px;
        background: ${COLORS.event.fill};
        border: 3px solid ${COLORS.event.stroke};
        border-radius: 50%;
        box-shadow: 0 0 12px rgba(220,38,38,0.5);
        animation: exposure-pulse 2s infinite;
      "></div>
    `,
  });
}

function createSchoolIcon() {
  return L.divIcon({
    className: 'exposure-school-marker',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    html: `
      <div style="
        width: 14px; height: 14px;
        background: ${COLORS.school.fill};
        border: 2px solid ${COLORS.school.stroke};
        border-radius: 3px;
        display: flex; align-items: center; justify-content: center;
        font-size: 8px; color: white; font-weight: bold;
      ">🏫</div>
    `,
  });
}

function createHospitalIcon() {
  return L.divIcon({
    className: 'exposure-hospital-marker',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    html: `
      <div style="
        width: 14px; height: 14px;
        background: ${COLORS.hospital.fill};
        border: 2px solid ${COLORS.hospital.stroke};
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 8px; color: white; font-weight: bold;
      ">🏥</div>
    `,
  });
}

// ── Build popup HTML ─────────────────────────────────────────

function buildEventPopup(eventLocation) {
  const pm25 = eventLocation.pm25;
  const severity = eventLocation.severity || 'unknown';
  const trajectory = eventLocation.trajectory || 'unknown';
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; min-width: 180px;">
      <div style="font-weight: 600; margin-bottom: 4px; color: #DC2626;">📍 Observation Point</div>
      <div style="color: #374151; font-weight: 600; font-size: 15px;">
        PM2.5: ${pm25 !== null && pm25 !== undefined ? `${pm25.toFixed(1)} μg/m³` : 'N/A'}
      </div>
      <div style="color: #6B7280; font-size: 11px; margin-top: 2px;">
        ${severity.charAt(0).toUpperCase() + severity.slice(1)} · ${trajectory}
      </div>
      <div style="color: #94a3b8; font-size: 10px; margin-top: 4px;">
        ${eventLocation.lat.toFixed(4)}, ${eventLocation.lng.toFixed(4)}
      </div>
    </div>
  `;
}

function buildCorridorPopup(area) {
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; min-width: 200px;">
      <div style="font-weight: 600; margin-bottom: 4px; color: #D97706;">
        <span style="margin-right: 4px;">🔍</span> Investigation Priority Area
      </div>
      <div style="color: #374151; font-size: 12px;">
        Wind FROM: <strong>${area.direction_label || 'N/A'}</strong> at ${area.distance_km || 8} km
      </div>
      <div style="color: #D97706; font-size: 11px; font-weight: 600; margin-top: 4px;">
        ⚠ Requires ground verification
      </div>
      <div style="color: #6B7280; font-size: 10px; margin-top: 4px; font-style: italic;">
        ${area.uncertainty || 'Investigation corridor based on current wind direction.'}
      </div>
    </div>
  `;
}

function buildExposurePopup(path) {
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; min-width: 200px;">
      <div style="font-weight: 600; margin-bottom: 4px; color: #DC2626;">
        <span style="margin-right: 4px;">⚠️</span> Exposure Path
      </div>
      <div style="color: #374151; font-size: 12px;">
        Moving toward: <strong>${path.direction_label || 'N/A'}</strong> · ~${path.distance_km || 0} km
      </div>
      <div style="color: #DC2626; font-size: 11px; margin-top: 4px;">
        Confidence: ${path.confidence || 'MODERATE'}
      </div>
      <div style="color: #6B7280; font-size: 10px; margin-top: 4px; font-style: italic;">
        ${path.uncertainty || 'Approximate wind-driven trajectory.'}
      </div>
    </div>
  `;
}

function buildVulnerablePopup(location) {
  const icon = location.type === 'hospital' ? '🏥' : '🏫';
  return `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; min-width: 160px;">
      <div style="font-weight: 600; margin-bottom: 4px;">
        ${icon} ${location.name}
      </div>
      <div style="color: #6B7280; font-size: 11px;">
        ${location.type === 'hospital' ? 'Hospital' : 'School'} — Vulnerable population
      </div>
      <div style="color: #94a3b8; font-size: 10px; margin-top: 2px;">
        ${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}
      </div>
    </div>
  `;
}

/**
 * @param {object} props
 * @param {object} props.exposure - Exposure geometry response from API
 * @param {boolean} [props.allowFullscreen=true] - Show fullscreen toggle
 * @param {string} [props.className] - Additional CSS class
 */
export default function ExposureIntelligenceMap({
  exposure = null,
  allowFullscreen = true,
  className = '',
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersRef = useRef([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // ── Initialize map ────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, {
      center: LAHORE_CENTER,
      zoom: LAHORE_ZOOM,
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM,
      zoomControl: true,
      scrollWheelZoom: true,
      attributionControl: false,
    });

    L.tileLayer(MAP_TILES.base.url, {
      attribution: MAP_TILES.attribution,
      maxZoom: MAP_TILES.base.maxZoom,
    }).addTo(map);

    if (MAP_TILES.labels.url) {
      L.tileLayer(MAP_TILES.labels.url, {
        maxZoom: MAP_TILES.labels.maxZoom,
        pane: 'overlayPane',
      }).addTo(map);
    }

    L.control.attribution({ position: 'bottomleft', prefix: false })
      .addAttribution('© <a href="https://www.openstreetmap.org/copyright" style="color:#94a3b8">OSM</a>')
      .addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Render exposure layers ────────────────────────────────
  useEffect(() => {
    if (!mapInstanceRef.current || !exposure) return;

    // Clear existing layers
    for (const layer of layersRef.current) {
      layer.remove();
    }
    layersRef.current = [];

    const map = mapInstanceRef.current;
    const bounds = [];

    // ── 1. Investigation corridor (upwind, dashed orange) ──
    const corridor = exposure.investigation_area;
    if (corridor?.coordinates?.length > 0) {
      const latLngs = corridor.coordinates.map(c => [c[0], c[1]]);
      const corridorPolygon = L.polygon(latLngs, {
        fillColor: COLORS.corridor.fill,
        fillOpacity: COLORS.corridor.fillOpacity,
        color: COLORS.corridor.stroke,
        weight: COLORS.corridor.weight,
        dashArray: COLORS.corridor.dashArray,
        interactive: true,
      }).addTo(map);
      corridorPolygon.bindPopup(buildCorridorPopup(corridor));
      layersRef.current.push(corridorPolygon);
      latLngs.forEach(c => bounds.push(c));
    }

    // ── 2. Exposure path (downwind, semi-transparent red) ──
    const path = exposure.exposure_path;
    if (path?.coordinates?.length > 0) {
      const latLngs = path.coordinates.map(c => [c[0], c[1]]);
      const exposurePolygon = L.polygon(latLngs, {
        fillColor: COLORS.exposure.fill,
        fillOpacity: COLORS.exposure.fillOpacity,
        color: COLORS.exposure.stroke,
        weight: COLORS.exposure.weight,
        dashArray: COLORS.exposure.dashArray,
        interactive: true,
      }).addTo(map);
      exposurePolygon.bindPopup(buildExposurePopup(path));
      layersRef.current.push(exposurePolygon);
      latLngs.forEach(c => bounds.push(c));
    }

    // ── 3. Event location marker (pulsing red dot) ──
    const eventLoc = exposure.event_location;
    if (eventLoc) {
      const eventMarker = L.marker([eventLoc.lat, eventLoc.lng], {
        icon: createEventIcon(),
        interactive: true,
      }).addTo(map);
      eventMarker.bindPopup(buildEventPopup(eventLoc));
      layersRef.current.push(eventMarker);
      bounds.push([eventLoc.lat, eventLoc.lng]);
    }

    // ── 4. Vulnerable locations ──
    const vuln = exposure.vulnerable_locations;
    if (vuln) {
      // Schools
      if (vuln.schools) {
        for (const school of vuln.schools) {
          const marker = L.marker([school.lat, school.lng], {
            icon: createSchoolIcon(),
            interactive: true,
          }).addTo(map);
          marker.bindPopup(buildVulnerablePopup(school));
          layersRef.current.push(marker);
          bounds.push([school.lat, school.lng]);
        }
      }
      // Hospitals
      if (vuln.hospitals) {
        for (const hospital of vuln.hospitals) {
          const marker = L.marker([hospital.lat, hospital.lng], {
            icon: createHospitalIcon(),
            interactive: true,
          }).addTo(map);
          marker.bindPopup(buildVulnerablePopup(hospital));
          layersRef.current.push(marker);
          bounds.push([hospital.lat, hospital.lng]);
        }
      }
    }

    // Fit map to show all geometry
    if (bounds.length > 0) {
      const pad = 0.02;
      const lats = bounds.map(b => b[0]);
      const lngs = bounds.map(b => b[1]);
      map.fitBounds([
        [Math.min(...lats) - pad, Math.min(...lngs) - pad],
        [Math.max(...lats) + pad, Math.max(...lngs) + pad],
      ], { padding: [30, 30] });
    }

    return () => {
      for (const layer of layersRef.current) {
        layer.remove();
      }
      layersRef.current = [];
    };
  }, [exposure]);

  // ── Fullscreen toggle ─────────────────────────────────────
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
    setTimeout(() => {
      if (mapInstanceRef.current) mapInstanceRef.current.invalidateSize();
    }, 300);
  }, []);

  // ── Summary stats for legend ──────────────────────────────
  const stats = useMemo(() => {
    if (!exposure) return null;
    const vuln = exposure.vulnerable_locations || {};
    return {
      schools: vuln.summary?.schools_in_path || 0,
      hospitals: vuln.summary?.hospitals_in_path || 0,
      corridor: exposure.investigation_area?.direction_label || 'N/A',
      exposure: exposure.exposure_path?.direction_label || 'N/A',
      windSpeed: exposure.metadata?.wind_speed_ms,
    };
  }, [exposure]);

  // ── No data state ─────────────────────────────────────────
  if (!exposure) {
    return (
      <div
        className={`map-container ${className}`}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--lp-bg-surface)', borderRadius: 'var(--lp-radius-md)',
          minHeight: 370,
        }}
        role="img"
        aria-label="Exposure intelligence map — no data available"
      >
        <div style={{ textAlign: 'center', color: 'var(--lp-text-muted)' }}>
          <AlertTriangle size={24} style={{ marginBottom: 8, opacity: 0.5 }} />
          <div style={{ fontSize: 13 }}>Exposure geometry unavailable</div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`map-container ${isFullscreen ? 'map-container--fullscreen' : ''} ${className}`}
      role="img"
      aria-label="Exposure intelligence map showing investigation corridor and exposure path"
      style={isFullscreen ? {
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        zIndex: 9999, borderRadius: 0, margin: 0,
        height: '100vh', width: '100vw',
      } : {}}
    >
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />

      {/* Fullscreen toggle */}
      {allowFullscreen && (
        <button
          onClick={toggleFullscreen}
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          aria-label={isFullscreen ? 'Exit fullscreen map' : 'View map fullscreen'}
          style={{
            position: 'absolute', top: 8, right: 8, zIndex: 1000,
            width: 32, height: 32,
            background: 'var(--lp-bg-surface)',
            border: '1px solid var(--lp-border-subtle)',
            borderRadius: 'var(--lp-radius-md)',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      )}

      {/* Legend overlay */}
      <div style={{
        position: 'absolute', bottom: 8, left: 8, zIndex: 1000,
        background: 'rgba(255,255,255,0.95)',
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        padding: '8px 10px',
        fontSize: 11,
        lineHeight: 1.6,
        maxWidth: 220,
        boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
      }}>
        <div style={{ fontWeight: 600, marginBottom: 4, color: '#111827', fontSize: 12 }}>
          Exposure Intelligence
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span style={{ display: 'inline-block', width: 14, height: 3, background: COLORS.corridor.stroke, borderTop: `2px dashed ${COLORS.corridor.stroke}` }} />
          <span style={{ color: '#374151' }}>
            <Search size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />
            Investigation area (upwind)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span style={{ display: 'inline-block', width: 14, height: 3, background: COLORS.exposure.stroke }} />
          <span style={{ color: '#374151' }}>
            <Shield size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />
            Exposure path (downwind)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, background: COLORS.event.fill, borderRadius: '50%' }} />
          <span style={{ color: '#374151' }}>Observation point</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, background: COLORS.school.fill, borderRadius: 2 }} />
          <span style={{ color: '#374151' }}>School (vulnerable)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, background: COLORS.hospital.fill, borderRadius: '50%' }} />
          <span style={{ color: '#374151' }}>Hospital (vulnerable)</span>
        </div>

        {/* Stats summary */}
        {stats && (
          <div style={{
            borderTop: '1px solid var(--lp-border-subtle)',
            marginTop: 6, paddingTop: 6,
            fontSize: 10, color: '#6B7280',
          }}>
            {stats.windSpeed != null && (
              <div>Wind: {stats.windSpeed} m/s · {stats.corridor}</div>
            )}
            <div>
              {stats.schools} school{stats.schools !== 1 ? 's' : ''} · {stats.hospitals} hospital{stats.hospitals !== 1 ? 's' : ''} in area
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
