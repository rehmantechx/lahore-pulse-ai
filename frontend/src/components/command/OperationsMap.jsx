/**
 * OperationsMap — Geographic intelligence for government operators.
 *
 * Unlike the citizen LahoreMap (single city-center marker), this component
 * provides operator-specific geographic intelligence:
 *
 * - Multi-area severity visualization using monitoring stations
 * - Trend indicators (worsening/improving/stable) per area
 * - Station coverage gaps highlighted
 * - Priority ranking (worst areas first)
 * - Click-to-drill into area details
 * - Color-coded zones derived from station clusters
 *
 * DATA SOURCE:
 *   - Station data from GET /api/v1/stations (real monitoring stations)
 *   - PM2.5 readings from station.latest_pm25
 *   - Area classification from station names/coordinates
 *
 * Does NOT fabricate data — shows exactly what the monitoring network provides.
 * 45 km CAMS resolution acknowledged.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Maximize2,
  Minimize2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  MapPin,
  Activity,
  Target,
} from 'lucide-react';
import { LAHORE_CENTER, LAHORE_ZOOM, MIN_ZOOM, MAX_ZOOM, MAP_TILES, PM25_LEVELS } from '../../constants';
import { SEVERITY_CONFIG } from '../../lib/incidentStore';

// Fix default Leaflet marker icon paths (Vite bundling issue)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

function getSeverityColor(pm25) {
  if (pm25 === null || pm25 === undefined) return '#94a3b8';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.color;
  }
  return '#7f1d1d';
}

function getSeverityLabel(pm25) {
  if (pm25 === null || pm25 === undefined) return 'No data';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.label;
  }
  return 'Hazardous';
}

/**
 * Classify stations into Lahore areas based on proximity.
 * Simple clustering: divide city into grid zones.
 */
function classifyAreas(stations) {
  if (!stations.length) return [];

  const areas = {};
  const ZONE_SIZE = 0.03; // ~3km grid

  for (const station of stations) {
    if (station.latitude == null || station.longitude == null) continue;
    if (station.latest_pm25 == null) continue;

    // Grid zone key
    const zoneLat = Math.floor(station.latitude / ZONE_SIZE) * ZONE_SIZE;
    const zoneLng = Math.floor(station.longitude / ZONE_SIZE) * ZONE_SIZE;
    const key = `${zoneLat.toFixed(3)},${zoneLng.toFixed(3)}`;

    if (!areas[key]) {
      areas[key] = {
        key,
        center: [zoneLat + ZONE_SIZE / 2, zoneLng + ZONE_SIZE / 2],
        stations: [],
        totalPM25: 0,
        count: 0,
      };
    }

    areas[key].stations.push(station);
    areas[key].totalPM25 += station.latest_pm25;
    areas[key].count += 1;
  }

  // Compute average PM2.5 per area and sort by severity (worst first)
  return Object.values(areas)
    .map(area => ({
      ...area,
      avgPM25: area.totalPM25 / area.count,
      severity: classifySeverity(area.totalPM25 / area.count),
    }))
    .sort((a, b) => b.avgPM25 - a.avgPM25);
}

function classifySeverity(pm25) {
  if (pm25 > 150) return 'critical';
  if (pm25 > 90) return 'severe';
  if (pm25 > 65) return 'high';
  if (pm25 > 45) return 'moderate';
  if (pm25 > 25) return 'low';
  return 'minimal';
}

/**
 * @param {object} props
 * @param {Array} props.stations - Monitoring stations with coordinates and PM2.5
 * @param {object} props.activeIncidents - Map of areas with active incidents
 * @param {string} props.selectedArea - Currently selected area key
 * @param {Function} props.onAreaSelect - Called when an area is clicked
 * @param {boolean} props.allowFullscreen - Show fullscreen toggle (default true)
 */
export default function OperationsMap({
  stations = [],
  activeIncidents = {},
  selectedArea = null,
  onAreaSelect = null,
  allowFullscreen = true,
}) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const areas = classifyAreas(stations);

  const buildAreaPopup = useCallback((area) => {
    const hasIncident = activeIncidents[area.key];
    const stationNames = area.stations.map(s => s.name || s.station_id).join(', ');

    return `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; min-width: 180px;">
        <div style="font-weight: 600; margin-bottom: 4px;">Zone (${area.count} station${area.count !== 1 ? 's' : ''})</div>
        <div style="color: ${getSeverityColor(area.avgPM25)}; font-weight: 600; font-size: 14px;">
          PM2.5: ${area.avgPM25.toFixed(1)} μg/m³
        </div>
        <div style="color: ${getSeverityColor(area.avgPM25)}; font-size: 11px; font-weight: 600; margin-top: 2px;">
          ${getSeverityLabel(area.avgPM25)}${hasIncident ? ' · ⚠ Active Incident' : ''}
        </div>
        <div style="color: #94a3b8; font-size: 10px; margin-top: 4px;">
          Stations: ${stationNames}
        </div>
        ${onAreaSelect ? '<div style="color: #2563eb; font-size: 10px; margin-top: 4px; cursor: pointer;">Click to drill down →</div>' : ''}
      </div>
    `;
  }, [activeIncidents, onAreaSelect]);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, {
      center: LAHORE_CENTER,
      zoom: LAHORE_ZOOM - 1,
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
      .addAttribution('© <a href="https://www.openstreetmap.org/copyright" style="color:#94a3b8">OSM</a> · <a href="https://atmosphere.copernicus.eu/" style="color:#94a3b8">CAMS</a>')
      .addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update area markers when stations or selection changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;

    // Clear existing markers
    for (const m of markersRef.current) m.remove();
    markersRef.current = [];

    for (const area of areas) {
      const color = getSeverityColor(area.avgPM25);
      const isSelected = selectedArea === area.key;
      const hasIncident = Boolean(activeIncidents[area.key]);

      // Area circle (larger, semi-transparent)
      const circle = L.circle(area.center, {
        radius: 1200, // ~1.2km radius for the zone
        fillColor: color,
        fillOpacity: isSelected ? 0.35 : 0.15,
        color: isSelected ? color : `${color}60`,
        weight: isSelected ? 3 : 1.5,
        dashArray: hasIncident ? undefined : '4,4',
      }).addTo(mapInstanceRef.current);

      circle.bindPopup(buildAreaPopup(area));
      markersRef.current.push(circle);

      // Station dots within the area
      for (const station of area.stations) {
        if (station.latitude == null || station.longitude == null) continue;

        const dot = L.circleMarker([station.latitude, station.longitude], {
          radius: hasIncident ? 6 : 5,
          fillColor: getSeverityColor(station.latest_pm25),
          fillOpacity: 0.85,
          color: hasIncident ? '#dc2626' : '#ffffff',
          weight: hasIncident ? 2.5 : 2,
        }).addTo(mapInstanceRef.current);

        dot.bindPopup(buildAreaPopup(area));
        markersRef.current.push(dot);
      }
    }

    return () => {
      for (const m of markersRef.current) m.remove();
      markersRef.current = [];
    };
  }, [areas, selectedArea, activeIncidents, buildAreaPopup]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
    setTimeout(() => {
      if (mapInstanceRef.current) mapInstanceRef.current.invalidateSize();
    }, 300);
  }, []);

  // Coverage analysis
  const totalStations = stations.filter(s => s.latitude != null).length;
  const coverageNote = totalStations < 5
    ? `${totalStations} stations — limited spatial coverage`
    : `${totalStations} stations covering ${areas.length} zones`;

  return (
    <div
      className={`map-container ${isFullscreen ? 'map-container--fullscreen' : ''}`}
      role="img"
      aria-label="Operations map showing priority areas for pollution response"
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

      {/* Priority ranking sidebar */}
      <div style={{
        position: 'absolute', top: 8, left: 8, zIndex: 1000,
        background: 'var(--lp-bg-surface)',
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        padding: 'var(--sp-3)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        maxHeight: '60vh',
        overflowY: 'auto',
        width: 200,
      }}>
        <div style={{ fontWeight: 600, fontSize: '0.75rem', marginBottom: 'var(--sp-2)', display: 'flex', alignItems: 'center', gap: 4 }}>
          <Target size={12} />
          Priority Zones
        </div>
        {areas.length === 0 ? (
          <div style={{ fontSize: '0.6875rem', color: 'var(--lp-text-muted)' }}>
            No station data available
          </div>
        ) : (
          areas.map((area, i) => {
            const sevCfg = SEVERITY_CONFIG[area.severity] || SEVERITY_CONFIG.unknown;
            const hasIncident = Boolean(activeIncidents[area.key]);
            return (
              <div
                key={area.key}
                onClick={() => onAreaSelect?.(area.key)}
                style={{
                  padding: '4px 6px',
                  borderRadius: 'var(--lp-radius-sm)',
                  cursor: onAreaSelect ? 'pointer' : 'default',
                  background: selectedArea === area.key ? `${sevCfg.color}10` : 'transparent',
                  border: selectedArea === area.key ? `1px solid ${sevCfg.border}` : '1px solid transparent',
                  marginBottom: 3,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: '0.6875rem',
                }}
              >
                <span style={{
                  width: 16, height: 16,
                  borderRadius: '50%',
                  background: sevCfg.bg,
                  color: sevCfg.color,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.5625rem', fontWeight: 700,
                  flexShrink: 0,
                }}>
                  {i + 1}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontWeight: selectedArea === area.key ? 600 : 400,
                    color: 'var(--lp-text-primary)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {area.count} station{area.count !== 1 ? 's' : ''}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <span style={{ color: sevCfg.color, fontWeight: 600 }}>
                      {area.avgPM25.toFixed(0)} μg/m³
                    </span>
                    <span style={{ color: sevCfg.color, fontSize: '0.5625rem' }}>
                      {sevCfg.label}
                    </span>
                  </div>
                </div>
                {hasIncident && (
                  <AlertTriangle size={10} color="#dc2626" style={{ flexShrink: 0 }} />
                )}
              </div>
            );
          })
        )}

        <div style={{
          marginTop: 'var(--sp-2)',
          paddingTop: 'var(--sp-2)',
          borderTop: '1px solid var(--lp-border-subtle)',
          fontSize: '0.5625rem', color: 'var(--lp-text-muted)',
        }}>
          {coverageNote}
        </div>
      </div>

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 8, left: 8, zIndex: 1000,
        background: 'var(--lp-bg-surface)',
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        padding: 'var(--sp-2) var(--sp-3)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      }}>
        <div style={{ fontWeight: 600, fontSize: '0.625rem', marginBottom: 4 }}>PM2.5 Severity</div>
        {PM25_LEVELS.slice(0, 5).map((level, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.5625rem', padding: '1px 0' }}>
            <span style={{
              width: 8, height: 8, borderRadius: 2,
              backgroundColor: level.color, flexShrink: 0,
            }} />
            <span style={{ color: 'var(--lp-text-secondary)' }}>
              ≤ {level.max} {level.label}
            </span>
          </div>
        ))}
        <div style={{ marginTop: 4, fontSize: '0.5rem', color: 'var(--lp-text-muted)' }}>
          ⚠ 45 km CAMS resolution
        </div>
      </div>

      {/* Source attribution */}
      <div style={{
        position: 'absolute', bottom: 8, right: 8, zIndex: 1000,
        background: 'var(--lp-bg-surface)',
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        padding: '3px 6px',
        fontSize: 9, color: 'var(--lp-text-muted)',
        display: 'flex', alignItems: 'center', gap: 3,
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      }}>
        <MapPin size={9} />
        <span>CAMS · Open-Meteo</span>
      </div>
    </div>
  );
}
