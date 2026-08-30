/**
 * Format Utilities Tests.
 *
 * Tests: formatPM25, formatTime, formatDateTime, formatTimeAgo,
 * formatFreshness, getPM25Level, formatInferenceTime.
 */

import { describe, it, expect } from 'vitest';
import {
  formatPM25,
  formatTime,
  formatDateTime,
  formatTimeAgo,
  formatFreshness,
  getPM25Level,
  formatInferenceTime,
} from '../format';

describe('formatPM25', () => {
  it('formats a numeric value with 1 decimal and units', () => {
    const result = formatPM25(35.678);
    expect(result).toContain('35.7');
    expect(result).toContain('g/m');
  });

  it('formats zero correctly', () => {
    const result = formatPM25(0);
    expect(result).toContain('0.0');
    expect(result).toContain('g/m');
  });

  it('returns dash for null', () => {
    expect(formatPM25(null)).toBe('—');
  });

  it('returns dash for undefined', () => {
    expect(formatPM25(undefined)).toBe('—');
  });

  it('returns dash for NaN', () => {
    expect(formatPM25(NaN)).toBe('—');
  });
});

describe('formatTime', () => {
  it('formats an ISO timestamp to 12-hour time', () => {
    const result = formatTime('2025-01-15T14:30:00Z');
    // Result depends on timezone conversion; just verify it's not a dash
    expect(result).not.toBe('—');
    expect(result).toMatch(/AM|PM/);
  });

  it('returns dash for null', () => {
    expect(formatTime(null)).toBe('—');
  });

  it('returns dash for empty string', () => {
    expect(formatTime('')).toBe('—');
  });
});

describe('formatDateTime', () => {
  it('formats an ISO timestamp to date + time', () => {
    const result = formatDateTime('2025-01-15T14:30:00Z');
    expect(result).not.toBe('—');
    expect(result).toMatch(/AM|PM/);
  });

  it('returns dash for null', () => {
    expect(formatDateTime(null)).toBe('—');
  });
});

describe('formatTimeAgo', () => {
  it('returns "Just now" for times less than 1 minute ago', () => {
    const now = new Date();
    expect(formatTimeAgo(now.toISOString())).toBe('Just now');
  });

  it('returns minutes ago for recent times', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000);
    expect(formatTimeAgo(fiveMinAgo.toISOString())).toBe('5 minutes ago');
  });

  it('returns hours ago', () => {
    const twoHrsAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
    expect(formatTimeAgo(twoHrsAgo.toISOString())).toBe('2 hours ago');
  });

  it('returns "Unknown" for null', () => {
    expect(formatTimeAgo(null)).toBe('Unknown');
  });

  it('returns "Unknown" for invalid input', () => {
    expect(formatTimeAgo('not-a-date')).toBe('Unknown');
  });
});

describe('formatFreshness', () => {
  it('formats minutes for sub-hour values', () => {
    expect(formatFreshness(0.5)).toBe('30 minutes');
  });

  it('formats hours for sub-day values', () => {
    expect(formatFreshness(3.5)).toBe('3.5 hours');
  });

  it('formats days for multi-day values', () => {
    expect(formatFreshness(48)).toBe('2.0 days');
  });

  it('returns "Unknown" for null', () => {
    expect(formatFreshness(null)).toBe('Unknown');
  });

  it('returns "Unknown" for undefined', () => {
    expect(formatFreshness(undefined)).toBe('Unknown');
  });
});

describe('getPM25Level', () => {
  it('returns "Good" for low PM2.5', () => {
    const level = getPM25Level(8);
    expect(level.label).toBe('Good');
    expect(level.color).toBeTruthy();
  });

  it('returns "Moderate" for mid-range PM2.5', () => {
    const level = getPM25Level(30);
    expect(level.label).toBe('Moderate');
  });

  it('returns "Unhealthy" for high PM2.5', () => {
    const level = getPM25Level(75);
    expect(level.label).toBe('Unhealthy');
  });

  it('returns "Hazardous" for extreme PM2.5', () => {
    const level = getPM25Level(200);
    expect(level.label).toBe('Hazardous');
  });

  it('returns Unknown-level for null', () => {
    const level = getPM25Level(null);
    expect(level.label).toBe('Unknown');
  });

  it('returns Unknown-level for undefined', () => {
    const level = getPM25Level(undefined);
    expect(level.label).toBe('Unknown');
  });

  it('returns guidance text for each level', () => {
    expect(getPM25Level(5).guidance).toBeTruthy();
    expect(getPM25Level(100).guidance).toBeTruthy();
    expect(getPM25Level(200).guidance).toBeTruthy();
  });
});

describe('formatInferenceTime', () => {
  it('formats sub-millisecond values', () => {
    expect(formatInferenceTime(0.5)).toBe('<1 ms');
  });

  it('formats millisecond values', () => {
    expect(formatInferenceTime(42)).toBe('42 ms');
  });

  it('formats second values', () => {
    expect(formatInferenceTime(1500)).toBe('1.50 s');
  });

  it('returns dash for null', () => {
    expect(formatInferenceTime(null)).toBe('—');
  });

  it('returns dash for 0', () => {
    expect(formatInferenceTime(0)).toBe('—');
  });
});
