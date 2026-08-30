/**
 * useHealth Hook Tests.
 *
 * Tests backend health monitoring polling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useHealth } from '../useHealth';

vi.mock('../../services/api', () => ({
  getReadiness: vi.fn(),
  NetworkError: class extends Error { constructor(m) { super(m); this.name = 'NetworkError'; } },
  TimeoutError: class extends Error { constructor(m) { super(m); this.name = 'TimeoutError'; } },
}));

import { getReadiness } from '../../services/api';

describe('useHealth', () => {
  beforeEach(() => {
    vi.mocked(getReadiness).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts in loading state', () => {
    getReadiness.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useHealth());
    expect(result.current.loading).toBe(true);
    expect(result.current.online).toBe(false);
  });

  it('reports online when backend is ready', async () => {
    getReadiness.mockResolvedValue({ status: 'ready', components: {} });
    const { result } = renderHook(() => useHealth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.online).toBe(true);
    expect(result.current.status).toBeTruthy();
  });

  it('reports offline on error', async () => {
    getReadiness.mockRejectedValue(new Error('Network error'));
    const { result } = renderHook(() => useHealth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    }, { timeout: 5000 });

    expect(result.current.online).toBe(false);
    expect(result.current.status).toBeNull();
  });

  it('reports online when backend says "healthy"', async () => {
    getReadiness.mockResolvedValue({ status: 'healthy' });
    const { result } = renderHook(() => useHealth());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.online).toBe(true);
  });
});
