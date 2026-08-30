/**
 * useForecast Hook Tests.
 *
 * Tests the primary data hook for loading, error, success, and refresh states.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useForecast } from '../useForecast';

// Mock the demo module (useDemoData returns null = not in demo mode)
vi.mock('../../demo', () => ({
  useDemoData: vi.fn(() => null),
}));

// Mock the API module
vi.mock('../../services/api', () => ({
  getAllForecasts: vi.fn(),
  getForecastStatus: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(status, code, message) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.code = code;
    }
  },
  NetworkError: class NetworkError extends Error {
    constructor(msg) { super(msg); this.name = 'NetworkError'; }
  },
  TimeoutError: class TimeoutError extends Error {
    constructor(ms) { super(`Timeout ${ms}`); this.name = 'TimeoutError'; }
  },
}));

import { getAllForecasts, getForecastStatus } from '../../services/api';

const mockForecasts = {
  forecasts: {
    '1': { predicted_pm25: 35.2, model: { version: 'v1' } },
    '3': { predicted_pm25: 40.1 },
    '6': { predicted_pm25: 42.0 },
    '12': { predicted_pm25: 45.5 },
    '24': { predicted_pm25: 38.0 },
  },
  errors: [],
  horizon_count: 5,
};

const mockStatus = {
  ready: true,
  supported_horizons: [1, 3, 6, 12, 24],
};

describe('useForecast', () => {
  beforeEach(() => {
    vi.mocked(getAllForecasts).mockReset();
    vi.mocked(getForecastStatus).mockReset();
    // Mock document.visibilityState
    Object.defineProperty(document, 'visibilityState', { value: 'visible', writable: true, configurable: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts in loading state', () => {
    getAllForecasts.mockReturnValue(new Promise(() => {})); // never resolves
    getForecastStatus.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useForecast({ autoRefresh: false }));
    expect(result.current.loading).toBe(true);
    expect(result.current.forecasts).toBeNull();
    expect(result.current.state).toBe('loading');
  });

  it('populates data on successful fetch', async () => {
    getAllForecasts.mockResolvedValue(mockForecasts);
    getForecastStatus.mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useForecast({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.forecasts).toEqual(mockForecasts.forecasts);
    expect(result.current.horizonCount).toBe(5);
    expect(result.current.state).toBe('success');
    expect(result.current.error).toBeNull();
    expect(result.current.lastFetchTime).toBeInstanceOf(Date);
  });

  it('sets error state on API failure', async () => {
    const apiError = new Error('Server error');
    getAllForecasts.mockRejectedValue(apiError);
    getForecastStatus.mockRejectedValue(apiError);

    const { result } = renderHook(() => useForecast({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 5000 });

    expect(result.current.error).toBeTruthy();
    expect(result.current.forecasts).toBeNull();
    expect(result.current.state).toBe('error');
  });

  it('exposes a refresh function', async () => {
    getAllForecasts.mockResolvedValue(mockForecasts);
    getForecastStatus.mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useForecast({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Call refresh
    getAllForecasts.mockResolvedValue({
      ...mockForecasts,
      forecasts: { ...mockForecasts.forecasts, '1': { predicted_pm25: 50.0 } },
    });

    await act(async () => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.forecasts['1'].predicted_pm25).toBe(50.0);
    });
  });

  it('returns errors array from partial failures', async () => {
    getAllForecasts.mockResolvedValue({
      forecasts: { '1': { predicted_pm25: 35.2 } },
      errors: [{ horizon: '6', errors: ['Model not found'] }],
      horizon_count: 1,
    });
    getForecastStatus.mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useForecast({ autoRefresh: false }));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.errors).toHaveLength(1);
    expect(result.current.errors[0].horizon).toBe('6');
    expect(result.current.horizonCount).toBe(1);
  });
});
