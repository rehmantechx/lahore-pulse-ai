/**
 * LahoreMap — Interactive Leaflet map focused on Lahore.
 *
 * Shows:
 * - Lahore geographic area at appropriate zoom
 * - CAMS data resolution note (45km grid, acknowledged limitation)
 * - Severity indicator at city center based on current forecast
 * - Clean, functional map — not decorative
 *
 * Does NOT fabricate station points or false spatial resolution.
 * The Phase 4 report acknowledges 45 km CAMS resolution limitation.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Maximize2, Minimize2, MapPin } from 'lucide-react';
import { LAHORE_CENTER, LAHORE_ZOOM, MIN_ZOOM, MAX_ZOOM, MAP_TILES, PM25_LEVELS } from '../../constants';

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

/* EPA PM2.5 → AQI breakpoint conversion */
const PM25_BREAKPOINTS = [
  { cLow: 0, cHigh: 12, iLow: 0, iHigh: 50 },
  { cLow: 12.1, cHigh: 35.4, iLow: 51, iHigh: 100 },
  { cLow: 35.5, cHigh: 55.4, iLow: 101, iHigh: 150 },
  { cLow: 55.5, cHigh: 150.4, iLow: 151, iHigh: 200 },
  { cLow: 150.5, cHigh: 250.4, iLow: 201, iHigh: 300 },
  { cLow: 250.5, cHigh: 500.4, iLow: 301, iHigh: 500 },
];

function pm25ToAQI(pm25) {
  if (pm25 == null || isNaN(pm25)) return null;
  for (const bp of PM25_BREAKPOINTS) {
    if (pm25 >= bp.cLow && pm25 <= bp.cHigh) {
      return Math.round(((bp.iHigh - bp.iLow) / (bp.cHigh - bp.cLow)) * (pm25 - bp.cLow) + bp.iLow);
    }
  }
  return pm25 > 500 ? 500 : 0;
}

/**
 * @param {object} props
 * @param {number|null} props.pm25Value - Current PM2.5 for the city center
 * @param {string|null} props.label - Label for the marker popup
 * @param {Array} props.stations - Ground-level monitoring stations to display
 * @param {boolean} props.allowFullscreen - Show fullscreen toggle (default true)
 * @param {boolean} props.showLegend - Show PM2.5 legend overlay (default true)
 * @param {number} props.centerRadius - Radius for city center marker (default 10)
 * @param {number} props.stationRadius - Radius for station markers (default 7)
 * @param {Array} props.areas - Area overlays as large geographic circles [{lat, lng, pm25, name, id}]
 * @param {number} props.areaRadius - Geographic radius in meters for area circles (default 8000)
 * @param {Array} props.mapCenter - Map center coordinates [lat, lng] (default LAHORE_CENTER)
 * @param {number} props.initialZoom - Initial zoom level (default LAHORE_ZOOM)
 */
export default function LahoreMap({ pm25Value = null, label = 'Lahore', stations = [], allowFullscreen = true, showLegend = true, centerRadius = 10, stationRadius = 7, areas = [], areaRadius = 8000, mapCenter, initialZoom }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const buildPopup = useCallback((name, pm25, source, timestamp, lat, lng) => `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; min-width: 160px;">
      <div style="font-weight: 600; margin-bottom: 4px;">${name}</div>
      <div style="color: #475569;">
        <strong>${pm25 != null ? getSeverityLabel(pm25) : 'No data'}</strong>
      </div>
      ${pm25 != null ? `<div style="color: ${getSeverityColor(pm25)}; font-size: 11px; font-weight: 600; margin-top: 2px;">${getSeverityLabel(pm25)}</div>` : ''}
      <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">
        ${source ? `Source: ${source}` : 'CAMS Copernicus'}
        ${timestamp ? ` · ${new Date(timestamp).toLocaleString()}` : ''}
      </div>
      ${lat != null && lng != null ? `<div style="color: #94a3b8; font-size: 10px; margin-top: 2px;">${lat.toFixed(4)}, ${lng.toFixed(4)}</div>` : ''}
    </div>
  `, []);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, {
      center: mapCenter || LAHORE_CENTER,
      zoom: initialZoom || LAHORE_ZOOM,
      minZoom: MIN_ZOOM,
      maxZoom: MAX_ZOOM,
      zoomControl: true,
      scrollWheelZoom: true,
      attributionControl: false,
    });

    // Base tile layer — clean, muted
    L.tileLayer(MAP_TILES.base.url, {
      attribution: MAP_TILES.attribution,
      maxZoom: MAP_TILES.base.maxZoom,
    }).addTo(map);

    // Label overlay (only if URL is provided — OSM standard tiles already include labels)
    if (MAP_TILES.labels.url) {
      L.tileLayer(MAP_TILES.labels.url, {
        maxZoom: MAP_TILES.labels.maxZoom,
        pane: 'overlayPane',
      }).addTo(map);
    }

    // City center marker
    const color = getSeverityColor(pm25Value);
    const marker = L.circleMarker(LAHORE_CENTER, {
      radius: centerRadius,
      fillColor: color,
      fillOpacity: 0.85,
      color: '#ffffff',
      weight: 3,
    }).addTo(map);

    const popupContent = `
      <div style="font-family: var(--font-sans); font-size: 13px; line-height: 1.5; min-width: 140px;">
        <div style="font-weight: 600; margin-bottom: 4px;">${label}</div>
        <div style="color: #475569;">
          ${pm25Value !== null
            ? `<strong>${getSeverityLabel(pm25Value)}</strong>`
            : '<em>No data</em>'
          }
        </div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">
          45 km CAMS resolution
        </div>
      </div>
    `;

    marker.bindPopup(buildPopup(label, pm25Value, 'CAMS Copernicus', null, LAHORE_CENTER[0], LAHORE_CENTER[1]));
    markerRef.current = marker;

    // Attribution control positioned bottom-left
    L.control.attribution({ position: 'bottomleft', prefix: false })
      .addAttribution('© <a href="https://www.openstreetmap.org/copyright" style="color:#94a3b8">OpenStreetMap</a> · <a href="https://atmosphere.copernicus.eu/" style="color:#94a3b8">CAMS</a>')
      .addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Update marker when pm25 changes
  useEffect(() => {
    if (!markerRef.current) return;
    const color = getSeverityColor(pm25Value);
    markerRef.current.setStyle({ fillColor: color });
    markerRef.current.setPopupContent(buildPopup(label, pm25Value, 'CAMS Copernicus', null, LAHORE_CENTER[0], LAHORE_CENTER[1]));
  }, [pm25Value, label, buildPopup]);

  // Update station markers when stations change
  useEffect(() => {
    if (!mapInstanceRef.current || !stations.length) return;

    const markers = [];

    for (const station of stations) {
      if (station.latitude == null || station.longitude == null) continue;

      const color = getSeverityColor(station.latest_pm25);

      const marker = L.circleMarker(
        [station.latitude, station.longitude],
        {
          radius: stationRadius,
          fillOpacity: 0.7,
          fillColor: color,
          color: '#ffffff',
          weight: 2,
        },
      ).addTo(mapInstanceRef.current);

      marker.bindPopup(buildPopup(
        station.name || station.station_id,
        station.latest_pm25,
        station.source_id,
        station.latest_observed_at,
        station.latitude,
        station.longitude,
      ));
      markers.push(marker);
    }

    return () => {
      for (const m of markers) {
        m.remove();
      }
    };
  }, [stations, buildPopup]);

  // Area overlays — large transparent circles for heatmap-style view
  useEffect(() => {
    if (!mapInstanceRef.current || !areas.length) return;

    const circles = [];

    for (const area of areas) {
      if (area.lat == null || area.lng == null) continue;

      const pm25 = area.pm25;
      const color = getSeverityColor(pm25);
      const aqi = pm25ToAQI(pm25);

      // Large transparent circle
      const circle = L.circle([area.lat, area.lng], {
        radius: areaRadius,
        fillColor: color,
        fillOpacity: 0.22,
        color: color,
        weight: 1,
        opacity: 0.4,
      }).addTo(mapInstanceRef.current);

      // AQI value label at center
      const icon = L.divIcon({
        className: 'area-aqi-label',
        html: `<div style="
          font-size: 15px;
          font-weight: 700;
          color: ${color};
          text-shadow: 0 1px 3px rgba(255,255,255,0.9), 0 0px 1px rgba(255,255,255,1);
          text-align: center;
          line-height: 1;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          pointer-events: none;
        ">${aqi ?? ''}</div>`,
        iconSize: [40, 20],
        iconAnchor: [20, 10],
      });

      const marker = L.marker([area.lat, area.lng], { icon, interactive: false }).addTo(mapInstanceRef.current);

      circles.push(circle, marker);
    }

    return () => {
      for (const c of circles) {
        c.remove();
      }
    };
  }, [areas, areaRadius]);

  // Fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
    setTimeout(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    }, 300);
  }, []);

  const hasStations = stations.length > 0 && stations.some(s => s.latitude != null);

  return (
    <div
      className={`map-container ${isFullscreen ? 'map-container--fullscreen' : ''}`}
      role="img"
      aria-label={`Map of Lahore showing air quality: ${pm25Value !== null ? getSeverityLabel(pm25Value) : 'no data'}`}
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
          className="map-control-btn"
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
            transition: 'background 150ms',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--slate-100)'}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--lp-bg-surface)'}
        >
          {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      )}

      {/* Legend overlay — complete 7-level scale (hidden when parent provides its own) */}
      {showLegend && (
      <div className="map-legend" style={{
        background: 'var(--lp-bg-surface)',
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        padding: 'var(--sp-3)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      }}>
        <div className="map-legend__title" style={{ fontWeight: 600, marginBottom: 'var(--sp-2)' }}>
          PM2.5 (μg/m³)
        </div>
        {PM25_LEVELS.map((level, i) => (
          <div key={i} className="map-legend__item" style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '1px 0', fontSize: '0.6875rem',
          }}>
            <span className="map-legend__swatch" style={{
              backgroundColor: level.color,
              width: 10, height: 10,
              borderRadius: 2, flexShrink: 0,
            }} />
            <span style={{ color: 'var(--lp-text-secondary)' }}>
              {level.max === Infinity ? `> ${PM25_LEVELS[i - 1].max}` : `≤ ${level.max}`}
              {' — '}
              {level.label}
            </span>
          </div>
        ))}
        <div style={{
          marginTop: 'var(--sp-2)',
          paddingTop: 'var(--sp-2)',
          borderTop: '1px solid var(--lp-border-subtle)',
          fontSize: 10, color: 'var(--lp-text-muted)',
        }}>
          {hasStations ? `${stations.length} ground stations shown` : 'City-center indicator'}
          {' · '}45 km CAMS resolution
        </div>
      </div>
      )}

      {/* Source attribution badge */}
      <div style={{
        position: 'absolute', bottom: 8, right: 8, zIndex: 1000,
        background: 'var(--lp-bg-surface)',
        border: '1px solid var(--lp-border-subtle)',
        borderRadius: 'var(--lp-radius-md)',
        padding: '4px 8px',
        fontSize: 10,
        color: 'var(--lp-text-muted)',
        display: 'flex', alignItems: 'center', gap: 4,
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      }}>
        <MapPin size={10} />
        <span>Data: CAMS Copernicus · Open-Meteo</span>
      </div>
    </div>
  );
}
