/**
 * StationsOverlay — Adds ground-level station markers to a Leaflet map.
 *
 * Shows real monitoring stations from AQICN/WAQI and OpenAQ
 * with their latest PM2.5 readings. Each station is a circleMarker
 * colored by severity level.
 *
 * This provides ground-truth spatial information alongside the
 * 45km CAMS grid indicator, helping users understand that actual
 * measurements exist at specific locations.
 *
 * Does NOT fabricate station data — only shows what the backend reports.
 */

import { useEffect } from 'react';
import L from 'leaflet';
import { PM25_LEVELS } from '../../constants';

function getSeverityColor(pm25) {
  if (pm25 === null || pm25 === undefined) return '#94a3b8';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.color;
  }
  return '#7f1d1d';
}

function getSeverityLabel(pm25) {
  if (pm25 === null || pm25 === undefined) return 'Unknown';
  for (const level of PM25_LEVELS) {
    if (pm25 <= level.max) return level.label;
  }
  return 'Hazardous';
}

/**
 * @param {object} props
 * @param {object|null} props.mapInstance - Leaflet map instance (from ref)
 * @param {Array} props.stations - Array of station objects from API
 */
export default function StationsOverlay({ mapInstance, stations = [] }) {
  useEffect(() => {
    if (!mapInstance || !stations.length) return;

    const markers = [];

    for (const station of stations) {
      if (station.latitude == null || station.longitude == null) continue;

      const color = getSeverityColor(station.latest_pm25);

      const marker = L.circleMarker(
        [station.latitude, station.longitude],
        {
          radius: 6,
          fillColor: color,
          fillOpacity: 0.7,
          color: '#ffffff',
          weight: 2,
        },
      ).addTo(mapInstance);

      const popupContent = `
        <div style="font-family: var(--font-sans); font-size: 13px; line-height: 1.5; min-width: 150px;">
          <div style="font-weight: 600; margin-bottom: 4px;">${station.name || station.station_id}</div>
          <div style="color: #475569;">
            <strong>${station.latest_pm25 != null ? getSeverityLabel(station.latest_pm25) : 'No data'}</strong>
          </div>`
          <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">
            Source: ${station.source_id} · ${station.latest_observed_at ? new Date(station.latest_observed_at).toLocaleString() : 'Unknown time'}
          </div>
          <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">
            ${station.latitude.toFixed(4)}, ${station.longitude.toFixed(4)}
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      markers.push(marker);
    }

    return () => {
      for (const m of markers) {
        m.remove();
      }
    };
  }, [mapInstance, stations]);

  return null; // This is a side-effect-only component
}
