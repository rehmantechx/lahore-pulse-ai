/**
 * useExposureGeometry — Fetches deterministic exposure geometry.
 *
 * In demo mode, returns the deterministic DEMO_EXPOSURE fixture.
 * In live mode, calls GET /api/v1/investigation/exposure.
 * Falls back to extracting exposure_geometry from the /analyze response.
 *
 * Returns: { exposure, loading, error, refresh }
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getExposureGeometry, ApiError, NetworkError, TimeoutError } from '../services/api';
import { useDemoData } from '../demo';

/**
 * Fetch exposure geometry with controlled refresh.
 *
 * @param {object} options
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms (default 5 min)
 * @returns {object} Exposure geometry state
 */
export function useExposureGeometry({
  autoRefresh = false,
  refreshInterval = 5 * 60 * 1000,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [exposure, setExposure] = useState(() =>
    isDemo ? (demoData.exposureGeometry || null) : null
  );
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchExposure = useCallback(async () => {
    try {
      if (!exposure) setLoading(true);
      setError(null);

      const data = await getExposureGeometry(
        {},
        { signal: AbortSignal.timeout(15000) }
      );

      if (!mountedRef.current) return;
      setExposure(data);
    } catch (err) {
      if (!mountedRef.current) return;

      if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
        setError(err);
      } else {
        setError(new NetworkError(`Unexpected error: ${err.message}`));
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [exposure]);

  // Initial fetch (live mode only)
  useEffect(() => {
    if (!isDemo) {
      fetchExposure();
    }
    return () => { mountedRef.current = false; };
  }, [isDemo]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (isDemo || !autoRefresh) return;
    intervalRef.current = setInterval(fetchExposure, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isDemo, autoRefresh, refreshInterval, fetchExposure]);

  const refresh = useCallback(() => {
    mountedRef.current = true;
    return fetchExposure();
  }, [fetchExposure]);

  return {
    exposure,
    loading,
    error,
    refresh,
  };
}
