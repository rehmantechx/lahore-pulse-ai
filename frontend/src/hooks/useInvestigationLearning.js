/**
 * useInvestigationLearning — Fetches investigation learning context.
 *
 * In demo mode, returns the deterministic DEMO_INVESTIGATION_LEARNING fixture.
 * In live mode, calls GET /api/v1/investigation/learning.
 *
 * Deterministic: NO machine learning — purely rule-based similarity matching
 * against previously verified investigation outcomes.
 *
 * Returns: { learning, loading, error, refresh }
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getInvestigationLearning,
  ApiError,
  NetworkError,
  TimeoutError,
} from '../services/api';
import { useDemoData } from '../demo';

/**
 * Fetch investigation learning context.
 *
 * @param {object} options
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms (default 15 min)
 * @returns {object} Learning state and actions
 */
export function useInvestigationLearning({
  autoRefresh = false,
  refreshInterval = 15 * 60 * 1000,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  // Demo mode: return demo learning data
  const demoLearning = isDemo ? (demoData.investigationLearning || null) : null;

  const [learning, setLearning] = useState(demoLearning);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      if (!learning) setLoading(true);
      setError(null);

      const data = await getInvestigationLearning(
        {},
        { signal: AbortSignal.timeout(15000) }
      );

      if (!mountedRef.current) return;

      setLearning(data);
    } catch (err) {
      if (!mountedRef.current) return;

      if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
        setError(err);
      } else {
        setError(new NetworkError(`Investigation learning fetch error: ${err.message}`));
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [learning]);

  // Initial fetch (live mode only)
  useEffect(() => {
    if (!isDemo) {
      fetchData();
    }
    return () => { mountedRef.current = false; };
  }, [isDemo]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (isDemo || !autoRefresh) return;

    intervalRef.current = setInterval(fetchData, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isDemo, autoRefresh, refreshInterval, fetchData]);

  const refresh = useCallback(() => {
    if (!isDemo) fetchData();
  }, [isDemo, fetchData]);

  return {
    learning,
    loading,
    error,
    refresh,
  };
}
