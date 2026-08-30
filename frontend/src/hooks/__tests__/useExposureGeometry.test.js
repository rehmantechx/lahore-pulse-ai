/**
 * useExposureGeometry — Hook tests.
 *
 * Tests: hook returns correct state, demo mode, error handling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useExposureGeometry } from '../useExposureGeometry';

// ── Mock dependencies ────────────────────────────────────────

const mockGetExposureGeometry = vi.fn();

vi.mock('../../services/api', () => ({
  getExposureGeometry: (...args) => mockGetExposureGeometry(...args),
  ApiError: class ApiError extends Error {
    constructor(msg, status) { super(msg); this.status = status; }
  },
  NetworkError: class NetworkError extends Error {
    constructor(msg) { super(msg); }
  },
  TimeoutError: class TimeoutError extends Error {
    constructor(msg) { super(msg); }
  },
}));

const mockUseDemoData = vi.fn(() => null);

vi.mock('../../demo', () => ({
  useDemoData: (...args) => mockUseDemoData(...args),
}));

// ── Tests ────────────────────────────────────────────────────

describe('useExposureGeometry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDemoData.mockReturnValue(null);
  });

  it('returns null exposure initially in live mode', () => {
    mockGetExposureGeometry.mockResolvedValue(null);
    const { result } = renderHook(() => useExposureGeometry());
    expect(result.current.exposure).toBeNull();
  });

  it('returns demo data immediately in demo mode', () => {
    const demoExposure = {
      event_location: { lat: 31.5204, lng: 74.3587 },
      investigation_area: {},
      exposure_path: {},
      vulnerable_locations: { schools: [], hospitals: [], summary: {} },
      metadata: {},
    };
    mockUseDemoData.mockReturnValue({ exposureGeometry: demoExposure });

    const { result } = renderHook(() => useExposureGeometry());
    expect(result.current.exposure).toEqual(demoExposure);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('fetches exposure data on mount in live mode', async () => {
    const mockData = {
      event_location: { lat: 31.52, lng: 74.35 },
      investigation_area: {},
      exposure_path: {},
      vulnerable_locations: { schools: [], hospitals: [], summary: {} },
      metadata: {},
    };
    mockGetExposureGeometry.mockResolvedValue(mockData);

    const { result } = renderHook(() => useExposureGeometry());

    await waitFor(() => {
      expect(result.current.exposure).toEqual(mockData);
      expect(result.current.loading).toBe(false);
    });

    expect(mockGetExposureGeometry).toHaveBeenCalledWith(
      {},
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
  });

  it('sets error when API call fails', async () => {
    mockGetExposureGeometry.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useExposureGeometry());

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
      expect(result.current.loading).toBe(false);
    });
  });

  it('does not fetch in demo mode', () => {
    mockUseDemoData.mockReturnValue({ exposureGeometry: { event_location: {} } });

    renderHook(() => useExposureGeometry());
    expect(mockGetExposureGeometry).not.toHaveBeenCalled();
  });
});
