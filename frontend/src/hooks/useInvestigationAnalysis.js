/**
 * useInvestigationAnalysis — Fetches AI investigation reasoning.
 *
 * In demo mode, returns the deterministic DEMO_INVESTIGATION fixture.
 * In live mode, calls GET /api/v1/investigation/analyze.
 *
 * Returns: { analysis, evidence, metadata, loading, error, refresh }
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getInvestigationAnalysis, ApiError, NetworkError, TimeoutError } from '../services/api';
import { useDemoData } from '../demo';

/**
 * Fetch AI investigation analysis with controlled refresh.
 *
 * @param {object} options
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms
 * @returns {object} Investigation analysis state
 */
export function useInvestigationAnalysis({
  autoRefresh = false,
  refreshInterval = 10 * 60 * 1000,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  // In demo mode, immediately return demo data — no API calls
  const [analysisData, setAnalysisData] = useState(() =>
    isDemo ? (demoData.investigationAnalysis || null) : null
  );
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const [lastFetchTime, setLastFetchTime] = useState(isDemo ? new Date() : null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchAnalysis = useCallback(async () => {
    try {
      if (!analysisData) setLoading(true);
      setError(null);

      const data = await getInvestigationAnalysis(
        {},
        { signal: AbortSignal.timeout(45000) }
      );

      if (!mountedRef.current) return;

      setAnalysisData(data);
      setLastFetchTime(new Date());
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
  }, [analysisData]);

  // Initial fetch (live mode only)
  useEffect(() => {
    if (!isDemo) {
      fetchAnalysis();
    }
    return () => { mountedRef.current = false; };
  }, [isDemo]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (isDemo || !autoRefresh) return;

    intervalRef.current = setInterval(fetchAnalysis, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isDemo, autoRefresh, refreshInterval, fetchAnalysis]);

  return {
    analysis: analysisData?.analysis || null,
    evidence: analysisData?.evidence || null,
    metadata: analysisData?.analysis_metadata || null,
    loading,
    error,
    lastFetchTime,
    refresh: fetchAnalysis,
  };
}
