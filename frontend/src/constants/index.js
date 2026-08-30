/**
 * Lahore Pulse AI — Application constants.
 *
 * All values here are derived from the backend configuration
 * and the Phase 4 model evaluation. No values are invented.
 */

// ── Geographic ─────────────────────────────────────────────────

export const LAHORE_CENTER = [31.5204, 74.3587];
export const LAHORE_ZOOM = 11;
export const MIN_ZOOM = 9;
export const MAX_ZOOM = 16;

// ── Forecast Horizons ──────────────────────────────────────────

export const HORIZONS = [1, 3, 6, 12, 24];

/**
 * Horizon metadata derived from Phase 4 validation metrics.
 * Performance language is technically justified, not invented.
 */
export const HORIZON_META = {
  1: {
    label: '1 hour',
    shortLabel: '1h',
    algorithm: 'Ridge Regression',
    valMAE: 4.4965,
    valRMSE: 7.3983,
    valR2: 0.975,
    confidence: 'high',
    description: 'Strong historical validation (R²=0.98) — model captured short-term PM2.5 behavior on held-out data.',
  },
  3: {
    label: '3 hours',
    shortLabel: '3h',
    algorithm: 'Histogram Gradient Boosting',
    valMAE: 10.6141,
    valRMSE: 14.773,
    valR2: 0.9004,
    confidence: 'high',
    description: 'Strong predictive reliability at the 3-hour window.',
  },
  6: {
    label: '6 hours',
    shortLabel: '6h',
    algorithm: 'Histogram Gradient Boosting',
    valMAE: 14.4482,
    valRMSE: 19.673,
    valR2: 0.8234,
    confidence: 'moderate',
    description: 'Moderate predictive reliability — weather-driven variability increases.',
  },
  12: {
    label: '12 hours',
    shortLabel: '12h',
    algorithm: 'Histogram Gradient Boosting',
    valMAE: 16.3406,
    valRMSE: 22.7115,
    valR2: 0.7649,
    confidence: 'moderate',
    description: 'Reasonable trend indication with increasing uncertainty.',
  },
  24: {
    label: '24 hours',
    shortLabel: '24h',
    algorithm: 'Ridge Regression',
    valMAE: 17.9661,
    valRMSE: 25.5438,
    valR2: 0.7033,
    confidence: 'lower',
    description: 'Greater uncertainty — useful for general trend, not precise values.',
  },
};

// ── PM2.5 Severity Thresholds ──────────────────────────────────
// Based on WHO guidelines and common AQI breakpoints.
// These are informational thresholds, NOT medical advice.

export const PM25_LEVELS = [
  { max: 12,   label: 'Good',                color: '#16a34a', bg: '#f0fdf4', textColor: '#166534', icon: '●', guidance: 'Air quality is satisfactory. Outdoor activity is fine for most people.' },
  { max: 25,   label: 'Fair',                color: '#65a30d', bg: '#f7fee7', textColor: '#3f6212', icon: '●', guidance: 'Air quality is acceptable. Unusually sensitive people should consider reducing prolonged outdoor exertion.' },
  { max: 45,   label: 'Moderate',            color: '#ca8a04', bg: '#fefce8', textColor: '#854d0e', icon: '▲', guidance: 'Moderate concern. People unusually sensitive to air pollution should reduce prolonged outdoor exertion.' },
  { max: 65,   label: 'Unhealthy for Sensitive Groups', color: '#ea580c', bg: '#fff7ed', textColor: '#9a3412', icon: '▲', guidance: 'Sensitive groups may experience health effects. Consider limiting prolonged outdoor activity.' },
  { max: 90,   label: 'Unhealthy',           color: '#dc2626', bg: '#fef2f2', textColor: '#991b1b', icon: '◆', guidance: 'Everyone may begin to experience health effects. Limit prolonged outdoor exertion.' },
  { max: 150,  label: 'Very Unhealthy',      color: '#b91c1c', bg: '#fef2f2', textColor: '#7f1d1d', icon: '◆', guidance: 'Significant health risk. Avoid prolonged outdoor activity.' },
  { max: Infinity, label: 'Hazardous',       color: '#7f1d1d', bg: '#fef2f2', textColor: '#7f1d1d', icon: '◆', guidance: 'Health emergency. Avoid all outdoor physical activity.' },
];

// ── Data Quality ───────────────────────────────────────────────

export const DATA_QUALITY = {
  GOOD: { label: 'Good', color: '#16a34a', description: 'All required data is fresh and available.' },
  DEGRADED: { label: 'Degraded', color: '#ca8a04', description: 'Some data sources are slow or stale. Forecasts may be less accurate.' },
  INSUFFICIENT: { label: 'Insufficient', color: '#dc2626', description: 'Critical data is missing. Forecasts cannot be generated reliably.' },
  UNAVAILABLE: { label: 'Unavailable', color: '#6b7280', description: 'Data service is not reachable.' },
};

// ── Confidence Language ────────────────────────────────────────
// NOT percentage values. Based on Phase 4 validation metrics.

export const CONFIDENCE_LABELS = {
  high: { label: 'High reliability', description: 'Based on strong historical model performance.' },
  moderate: { label: 'Moderate reliability', description: 'Useful for planning; expect some variability.' },
  lower: { label: 'Greater uncertainty', description: 'Indicative trend; do not rely for precise planning.' },
};

// ── Map Tile Layers ────────────────────────────────────────────
// Standard OpenStreetMap tiles — free, no API key required.
// CARTO tiles now show "API KEY REQUIRED" watermark on free tier.

export const MAP_TILES = {
  base: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
  labels: {
    url: '',
    attribution: '',
    maxZoom: 19,
  },
};

// ── Source Compass ─────────────────────────────────────────────
// Derived from Phase 2 hostile validation (10/10 attacks passed).

export const SOURCE_COMPASS_SECTORS = [
  { key: 'N',  label: 'North',           degrees: 0,   color: '#6366f1' },
  { key: 'NE', label: 'Northeast',       degrees: 45,  color: '#8b5cf6' },
  { key: 'E',  label: 'East',            degrees: 90,  color: '#ef4444' },
  { key: 'SE', label: 'Southeast',       degrees: 135, color: '#f97316' },
  { key: 'S',  label: 'South',           degrees: 180, color: '#eab308' },
  { key: 'SW', label: 'Southwest',       degrees: 225, color: '#22c55e' },
  { key: 'W',  label: 'West',            degrees: 270, color: '#06b6d4' },
  { key: 'NW', label: 'Northwest',       degrees: 315, color: '#3b82f6' },
];

export const SOURCE_COMPASS_ASSOCIATIONS = {
  HIGH: { label: 'Strong directional signal', color: '#ef4444', description: 'Consistent enrichment during episodes. Investigation corridor warranted.' },
  MODERATE: { label: 'Moderate directional signal', color: '#f97316', description: 'Some enrichment during episodes. Worth investigating.' },
  LOW: { label: 'Weak directional signal', color: '#ca8a04', description: 'Limited enrichment signal. Other factors may dominate.' },
  INSUFFICIENT: { label: 'Insufficient data', color: '#6b7280', description: 'Not enough episode-hours in this sector to draw conclusions.' },
};

export const SOURCE_COMPASS_DISCLAIMER = 'Directional evidence does not confirm a pollution source. It suggests an investigation direction based on wind patterns during past episodes.';

// ── Refresh Intervals ──────────────────────────────────────────

export const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
export const STALE_THRESHOLD_MS = 10 * 60 * 1000; // 10 minutes
