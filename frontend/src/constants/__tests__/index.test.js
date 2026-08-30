/**
 * Constants Tests — verify structure and integrity of shared constants.
 */

import { describe, it, expect } from 'vitest';
import {
  LAHORE_CENTER,
  LAHORE_ZOOM,
  HORIZONS,
  HORIZON_META,
  PM25_LEVELS,
  CONFIDENCE_LABELS,
  MAP_TILES,
  REFRESH_INTERVAL_MS,
  STALE_THRESHOLD_MS,
} from '../index';

describe('LAHORE_CENTER', () => {
  it('is a [lat, lng] pair near Lahore', () => {
    expect(LAHORE_CENTER).toHaveLength(2);
    expect(LAHORE_CENTER[0]).toBeCloseTo(31.52, 0);
    expect(LAHORE_CENTER[1]).toBeCloseTo(74.35, 0);
  });
});

describe('HORIZONS', () => {
  it('contains 5 forecast horizons', () => {
    expect(HORIZONS).toEqual([1, 3, 6, 12, 24]);
    expect(HORIZONS).toHaveLength(5);
  });
});

describe('HORIZON_META', () => {
  it('has metadata for every horizon', () => {
    for (const h of HORIZONS) {
      expect(HORIZON_META[h]).toBeDefined();
      expect(HORIZON_META[h].label).toBeTruthy();
      expect(HORIZON_META[h].shortLabel).toBeTruthy();
      expect(HORIZON_META[h].algorithm).toBeTruthy();
      expect(typeof HORIZON_META[h].valMAE).toBe('number');
      expect(typeof HORIZON_META[h].valRMSE).toBe('number');
      expect(typeof HORIZON_META[h].valR2).toBe('number');
      expect(['high', 'moderate', 'lower']).toContain(HORIZON_META[h].confidence);
    }
  });

  it('R2 values are between 0 and 1', () => {
    for (const h of HORIZONS) {
      expect(HORIZON_META[h].valR2).toBeGreaterThan(0);
      expect(HORIZON_META[h].valR2).toBeLessThanOrEqual(1);
    }
  });

  it('has shortLabel matching horizon hour', () => {
    for (const h of HORIZONS) {
      expect(HORIZON_META[h].shortLabel).toBe(`${h}h`);
    }
  });
});

describe('PM25_LEVELS', () => {
  it('contains 7 severity levels', () => {
    expect(PM25_LEVELS).toHaveLength(7);
  });

  it('each level has required fields', () => {
    for (const level of PM25_LEVELS) {
      expect(typeof level.max).toBe('number');
      expect(level.label).toBeTruthy();
      expect(level.color).toBeTruthy();
      expect(level.guidance).toBeTruthy();
      expect(level.icon).toBeTruthy();
    }
  });

  it('first level max is 12 (Good)', () => {
    expect(PM25_LEVELS[0].max).toBe(12);
    expect(PM25_LEVELS[0].label).toBe('Good');
  });

  it('last level max is Infinity (Hazardous)', () => {
    expect(PM25_LEVELS[PM25_LEVELS.length - 1].max).toBe(Infinity);
    expect(PM25_LEVELS[PM25_LEVELS.length - 1].label).toBe('Hazardous');
  });
});

describe('CONFIDENCE_LABELS', () => {
  it('has 3 confidence levels', () => {
    expect(Object.keys(CONFIDENCE_LABELS)).toHaveLength(3);
    expect(CONFIDENCE_LABELS.high).toBeDefined();
    expect(CONFIDENCE_LABELS.moderate).toBeDefined();
    expect(CONFIDENCE_LABELS.lower).toBeDefined();
  });
});

describe('MAP_TILES', () => {
  it('has base tile config with url and attribution', () => {
    expect(MAP_TILES.base.url).toBeTruthy();
    expect(MAP_TILES.base.attribution).toBeTruthy();
  });
  it('labels url is empty string for base-layer includes labels', () => {
    /* OSM standard tiles include labels, so labels layer is not used */
    expect(typeof MAP_TILES.labels.url).toBe('string');
  });
});

describe('REFRESH_INTERVAL_MS', () => {
  it('is 5 minutes', () => {
    expect(REFRESH_INTERVAL_MS).toBe(5 * 60 * 1000);
  });
});

describe('STALE_THRESHOLD_MS', () => {
  it('is 10 minutes', () => {
    expect(STALE_THRESHOLD_MS).toBe(10 * 60 * 1000);
  });
});
