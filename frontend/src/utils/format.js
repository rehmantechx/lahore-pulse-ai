/**
 * Lahore Pulse AI — Formatting utilities.
 *
 * All formatters work with actual API response data.
 * No values are computed or invented.
 */

import { PM25_LEVELS } from '../constants';

/**
 * Format a PM2.5 value with units.
 * @param {number|null} value - PM2.5 concentration in μg/m³
 * @returns {string}
 */
export function formatPM25(value) {
  if (value === null || value === undefined || isNaN(value)) return '—';
  return `${value.toFixed(1)} μg/m³`;
}

/**
 * Format a timestamp to a human-readable time string.
 * @param {string} isoString - ISO 8601 timestamp
 * @returns {string}
 */
export function formatTime(isoString) {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Karachi',
    });
  } catch {
    return '—';
  }
}

/**
 * Format a timestamp to a date+time string.
 * @param {string} isoString
 * @returns {string}
 */
export function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Karachi',
    });
  } catch {
    return '—';
  }
}

/**
 * Format a "time ago" string for data freshness.
 * @param {string} isoString - ISO 8601 timestamp
 * @returns {string}
 */
export function formatTimeAgo(isoString) {
  if (!isoString) return 'Unknown';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return 'Unknown';
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHrs = Math.floor(diffMin / 60);

    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
    if (diffHrs < 24) return `${diffHrs} hour${diffHrs !== 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  } catch {
    return 'Unknown';
  }
}

/**
 * Format freshness hours to a human-readable string.
 * @param {number|null} hours
 * @returns {string}
 */
export function formatFreshness(hours) {
  if (hours === null || hours === undefined) return 'Unknown';
  if (hours < 1) return `${Math.round(hours * 60)} minutes`;
  if (hours < 24) return `${hours.toFixed(1)} hours`;
  return `${(hours / 24).toFixed(1)} days`;
}

/**
 * Get the PM2.5 severity level for a given value.
 * @param {number|null} value
 * @returns {object} Severity level object from PM25_LEVELS
 */
export function getPM25Level(value) {
  if (value === null || value === undefined) {
    return { label: 'Unknown', color: '#6b7280', bg: '#f9fafb', textColor: '#374151', icon: '?', guidance: 'No data available.' };
  }
  for (const level of PM25_LEVELS) {
    if (value <= level.max) return level;
  }
  return PM25_LEVELS[PM25_LEVELS.length - 1];
}

/**
 * Format an inference time in milliseconds.
 * @param {number} ms
 * @returns {string}
 */
export function formatInferenceTime(ms) {
  if (!ms) return '—';
  if (ms < 1) return '<1 ms';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}
