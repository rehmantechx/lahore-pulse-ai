/**
 * useVerification — Hook tests.
 *
 * Tests: hook returns correct state, demo mode, submit flow, error handling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useVerification } from '../useVerification';

// ── Mock dependencies ────────────────────────────────────────

const mockSubmitVerification = vi.fn();
const mockUpdateVerification = vi.fn();
const mockGetVerificationStats = vi.fn();
const mockGetVerificationContext = vi.fn();

vi.mock('../../services/api', () => ({
  submitVerification: (...args) => mockSubmitVerification(...args),
  updateVerification: (...args) => mockUpdateVerification(...args),
  getVerificationStats: (...args) => mockGetVerificationStats(...args),
  getVerificationContext: (...args) => mockGetVerificationContext(...args),
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

describe('useVerification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseDemoData.mockReturnValue(null);
    mockGetVerificationStats.mockResolvedValue(null);
    mockGetVerificationContext.mockResolvedValue(null);
  });

  it('returns null context initially in live mode', () => {
    const { result } = renderHook(() => useVerification());
    expect(result.current.context).toBeNull();
    expect(result.current.stats).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('returns demo verification data in demo mode', () => {
    const demoVerification = {
      current_outcome: null,
      stats: { total_verifications: 5, useful_count: 3 },
      has_sufficient_data: true,
    };
    mockUseDemoData.mockReturnValue({ verification: demoVerification, verificationStats: demoVerification.stats });

    const { result } = renderHook(() => useVerification());
    expect(result.current.context).toEqual(demoVerification);
    expect(result.current.stats).toEqual(demoVerification.stats);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('fetches verification data when investigationId provided', async () => {
    const mockContext = {
      current_outcome: null,
      stats: { total_verifications: 2, useful_count: 1 },
      has_sufficient_data: false,
    };
    mockGetVerificationContext.mockResolvedValue(mockContext);
    mockGetVerificationStats.mockResolvedValue({ total_verifications: 10 });

    const { result } = renderHook(() =>
      useVerification({ investigationId: 'inv-001' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockGetVerificationContext).toHaveBeenCalledWith('inv-001', expect.any(Object));
    expect(mockGetVerificationStats).toHaveBeenCalled();
    expect(result.current.context).toEqual(mockContext);
  });

  it('does not fetch when no investigationId', async () => {
    const { result } = renderHook(() => useVerification());
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(mockGetVerificationContext).not.toHaveBeenCalled();
    expect(mockGetVerificationStats).toHaveBeenCalled();
  });

  it('submit calls submitVerification in live mode', async () => {
    const mockResult = { outcome_id: 'vout-123', overall_status: 'USEFUL' };
    mockSubmitVerification.mockResolvedValue(mockResult);
    mockGetVerificationContext.mockResolvedValue({ current_outcome: mockResult });
    mockGetVerificationStats.mockResolvedValue(null);

    const { result } = renderHook(() =>
      useVerification({ investigationId: 'inv-001' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    let submitResult;
    await act(async () => {
      submitResult = await result.current.submit({
        investigation_id: 'inv-001',
        overall_status: 'USEFUL',
      });
    });

    expect(mockSubmitVerification).toHaveBeenCalled();
    expect(submitResult).toEqual(mockResult);
    expect(result.current.submitSuccess).toBe(true);
  });

  it('submit returns success in demo mode', async () => {
    const demoVerification = {
      current_outcome: null,
      stats: { total_verifications: 5 },
    };
    mockUseDemoData.mockReturnValue({ verification: demoVerification });

    const { result } = renderHook(() => useVerification());

    let submitResult;
    await act(async () => {
      submitResult = await result.current.submit({
        investigation_id: 'demo',
        overall_status: 'USEFUL',
      });
    });

    expect(mockSubmitVerification).not.toHaveBeenCalled();
    expect(submitResult).toEqual({ success: true });
    expect(result.current.submitSuccess).toBe(true);
  });

  it('handles API errors gracefully', async () => {
    const apiError = new Error('Request failed');
    apiError.status = 500;
    mockGetVerificationContext.mockRejectedValue(apiError);
    mockGetVerificationStats.mockResolvedValue(null);

    const { result } = renderHook(() =>
      useVerification({ investigationId: 'inv-001' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
  });

  it('update calls updateVerification', async () => {
    const mockResult = { outcome_id: 'vout-123', overall_status: 'PARTIALLY_USEFUL' };
    mockUpdateVerification.mockResolvedValue(mockResult);
    mockGetVerificationContext.mockResolvedValue({ current_outcome: mockResult });
    mockGetVerificationStats.mockResolvedValue(null);

    const { result } = renderHook(() =>
      useVerification({ investigationId: 'inv-001' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.update('vout-123', { overall_status: 'PARTIALLY_USEFUL' });
    });

    expect(mockUpdateVerification).toHaveBeenCalledWith('vout-123', { overall_status: 'PARTIALLY_USEFUL' }, expect.any(Object));
  });
});
