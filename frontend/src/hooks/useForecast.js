/**
 * Lahore Pulse AI — useForecast hook.
 *
 * Fetches all-horizon forecast data with loading/error/stale states
 * and controlled refresh. This is the primary data hook for the
 * forecast UI.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getAllForecasts, getForecastStatus, ApiError, NetworkError, TimeoutError } from '../services/api';
import { REFRESH_INTERVAL_MS } from '../constants';
import { useDemoData } from '../demo';

/**
 * State machine for forecast data.
 *
 * States:
 * - loading: Initial fetch in progress
 * - success: Data loaded and fresh
 * - stale: Data loaded but refresh interval has elapsed
 * - error: Last fetch failed (may have stale data)
 * - empty: No forecast data available
 */

export function useForecast({ autoRefresh = true, refreshInterval = REFRESH_INTERVAL_MS, skip: skipProp = false } = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const skip = skipProp || isDemo;

  // In demo mode, immediately return demo data — no API calls
  const [forecasts, setForecasts] = useState(() => isDemo ? (demoData.forecasts || {}) : null);
  const [errors, setErrors] = useState(() => isDemo ? [] : []);
  const [horizonCount, setHorizonCount] = useState(() => isDemo ? Object.keys(demoData.forecasts || {}).length : 0);
  const [forecastStatus, setForecastStatus] = useState(() => isDemo ? (demoData.forecastStatus || null) : null);
  const [loading, setLoading] = useState(!skip);
  const [error, setError] = useState(null);
  const [lastFetchTime, setLastFetchTime] = useState(isDemo ? new Date() : null);
  const [isStale, setIsStale] = useState(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);
  const retryTimerRef = useRef(null);
  const forecastsRef = useRef(forecasts);

  const fetchForecasts = useCallback(async () => {
    try {
      // Only show loading spinner on first load
      if (!forecastsRef.current) setLoading(true);
      setError(null);

      const [forecastResult, statusResult] = await Promise.allSettled([
        getAllForecasts({ timeout: 20000 }),
        getForecastStatus({ timeout: 35000 }),
      ]);

      if (!mountedRef.current) return;

      // Forecast data is required; if it failed, throw
      if (forecastResult.status === 'rejected') {
        throw forecastResult.reason;
      }

      const forecastData = forecastResult.value;
      forecastsRef.current = forecastData.forecasts || {};
      setForecasts(forecastData.forecasts || {});
      setErrors(forecastData.errors || []);
      setHorizonCount(forecastData.horizon_count || 0);

      // Status is optional; use whatever we got
      if (statusResult.status === 'fulfilled') {
        setForecastStatus(statusResult.value);
      }
      setLastFetchTime(new Date());
      setIsStale(false);
      setLoading(false);
    } catch (err) {
      if (!mountedRef.current) return;

      if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
        setError(err);
      } else {
        setError(new Error(err.message || 'Unexpected error'));
      }
      setLoading(false);
      setIsStale(false);
    }
  }, []);

  // Initial fetch with auto-retry on failure
  useEffect(() => {
    if (skip) {
      setLoading(false);
      setLastFetchTime(new Date());
      return;
    }
    mountedRef.current = true;

    async function doFetch(attempt) {
      try {
        if (attempt === 0) setLoading(true);
        setError(null);

        const [forecastResult, statusResult] = await Promise.allSettled([
          getAllForecasts({ timeout: 20000 }),
          getForecastStatus({ timeout: 35000 }),
        ]);

        if (!mountedRef.current) return;

        if (forecastResult.status === 'rejected') {
          throw forecastResult.reason;
        }

        const forecastData = forecastResult.value;
        forecastsRef.current = forecastData.forecasts || {};
        setForecasts(forecastData.forecasts || {});
        setErrors(forecastData.errors || []);
        setHorizonCount(forecastData.horizon_count || 0);

        if (statusResult.status === 'fulfilled') {
          setForecastStatus(statusResult.value);
        }
        setLastFetchTime(new Date());
        setIsStale(false);
        setLoading(false);
      } catch (err) {
        if (!mountedRef.current) return;

        if (attempt === 0) {
          // Retry once after 2 seconds on first failure
          await new Promise(r => { retryTimerRef.current = setTimeout(r, 2000); });
          if (!mountedRef.current) return;
          return doFetch(1);
        }

        // Final failure
        if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
          setError(err);
        } else {
          setError(new Error(err.message || 'Unexpected error'));
        }
        setLoading(false);
        setIsStale(false);
      }
    }

    doFetch(0);

    return () => {
      mountedRef.current = false;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || skip) return;

    intervalRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') {
        setIsStale(true);
        fetchForecasts();
      }
    }, refreshInterval);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, refreshInterval, fetchForecasts]);

  // Visibility-based refresh
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible' && isStale) {
        fetchForecasts();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [isStale, fetchForecasts]);

  const refresh = useCallback(() => {
    fetchForecasts();
  }, [fetchForecasts]);

  const state = loading ? 'loading' : error ? 'error' : forecasts && horizonCount > 0 ? 'success' : 'empty';

  return {
    forecasts,
    errors,
    horizonCount,
    forecastStatus,
    loading,
    error,
    isStale,
    lastFetchTime,
    state,
    refresh,
  };
}
