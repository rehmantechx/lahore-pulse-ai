/**
 * API Client Tests — Services layer.
 *
 * Tests: error classes, apiFetch wrapper, all API methods.
 * Uses vi.fn() to mock global.fetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ApiError,
  NetworkError,
  TimeoutError,
  getHealth,
  getReadiness,
  getForecast,
  getAllForecasts,
  getForecastStatus,
  getPredictionHistory,
  getDataSources,
  getObservationStats,
} from '../api';

// ── Error Classes ──────────────────────────────────────────────

describe('ApiError', () => {
  it('should store status, code, message, and details', () => {
    const err = new ApiError(404, 'NOT_FOUND', 'Resource not found', { field: 'id' });
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('ApiError');
    expect(err.status).toBe(404);
    expect(err.code).toBe('NOT_FOUND');
    expect(err.message).toBe('Resource not found');
    expect(err.details).toEqual({ field: 'id' });
  });
});

describe('NetworkError', () => {
  it('should store message and originalError', () => {
    const orig = new TypeError('Failed to fetch');
    const err = new NetworkError('Cannot connect', orig);
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('NetworkError');
    expect(err.message).toBe('Cannot connect');
    expect(err.originalError).toBe(orig);
  });
});

describe('TimeoutError', () => {
  it('should store timeoutMs in message', () => {
    const err = new TimeoutError(5000);
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('TimeoutError');
    expect(err.timeoutMs).toBe(5000);
    expect(err.message).toContain('5000');
  });
});

// ── API Fetch Mocks ────────────────────────────────────────────

describe('API methods', () => {
  beforeEach(() => {
    vi.spyOn(global, 'fetch');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetchJson(data, ok = true, status = 200) {
    global.fetch.mockResolvedValue({
      ok,
      status,
      json: async () => data,
      statusText: ok ? 'OK' : 'Error',
    });
  }

  function mockFetchError(status, body) {
    global.fetch.mockResolvedValue({
      ok: false,
      status,
      statusText: 'Error',
      json: async () => body,
    });
  }

  function mockFetchNetworkError() {
    global.fetch.mockRejectedValue(new TypeError('Failed to fetch'));
  }

  function mockFetchAbort() {
    const abortErr = new DOMException('The operation was aborted.', 'AbortError');
    global.fetch.mockRejectedValue(abortErr);
  }

  // ── getHealth ──

  it('getHealth returns status data', async () => {
    const data = { status: 'healthy', service: 'lahore-pulse-ai', version: '1.0.0' };
    mockFetchJson(data);
    const result = await getHealth();
    expect(result).toEqual(data);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/health',
      expect.objectContaining({ headers: expect.objectContaining({ 'Accept': 'application/json' }) })
    );
  });

  // ── getReadiness ──

  it('getReadiness returns component status', async () => {
    const data = { status: 'ready', components: { database: { status: 'ok' } } };
    mockFetchJson(data);
    const result = await getReadiness();
    expect(result).toEqual(data);
  });

  // ── getForecast ──

  it('getForecast passes horizon query parameter', async () => {
    const data = { forecast: { predicted_pm25: 35.2 } };
    mockFetchJson(data);
    const result = await getForecast(6);
    expect(result).toEqual(data);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/forecast?horizon=6',
      expect.anything()
    );
  });

  // ── getAllForecasts ──

  it('getAllForecasts returns multi-horizon data', async () => {
    const data = {
      forecasts: { '1': { predicted_pm25: 30 }, '3': { predicted_pm25: 35 } },
      errors: [],
      horizon_count: 2,
    };
    mockFetchJson(data);
    const result = await getAllForecasts();
    expect(result.forecasts).toHaveProperty('1');
    expect(result.forecasts).toHaveProperty('3');
    expect(result.horizon_count).toBe(2);
  });

  // ── getForecastStatus ──

  it('getForecastStatus returns ready state', async () => {
    const data = { ready: true, supported_horizons: [1, 3, 6, 12, 24] };
    mockFetchJson(data);
    const result = await getForecastStatus();
    expect(result.ready).toBe(true);
  });

  // ── Error handling ──

  it('throws ApiError on non-OK response', async () => {
    mockFetchError(404, { error: { code: 'NOT_FOUND', message: 'Not found' } });
    await expect(getHealth()).rejects.toThrow(ApiError);
    try {
      await getHealth();
    } catch (e) {
      expect(e.status).toBe(404);
      expect(e.code).toBe('NOT_FOUND');
    }
  });

  it('throws NetworkError on fetch TypeError', async () => {
    mockFetchNetworkError();
    await expect(getHealth()).rejects.toThrow(NetworkError);
  });

  it('throws on abort (timeout or abort error)', async () => {
    mockFetchAbort();
    await expect(getHealth({ timeout: 100 })).rejects.toThrow();
  });
});
