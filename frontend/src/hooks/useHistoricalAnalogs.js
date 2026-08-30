/**
 * useHistoricalAnalogs — fetch historical analog episodes.
 *
 * Finds episodes with similar meteorological conditions to current state.
 * Uses deterministic similarity matching (NOT ML).
 */

import { useState, useEffect, useCallback } from 'react';
import { getEpisodeAnalogs } from '../services/api';
import { useDemoData } from '../demo';

/**
 * Fetch historical analogs with controlled refresh.
 *
 * In demo mode, returns demo fixtures without calling the API.
 *
 * @param {object} options
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms
 * @param {number} options.limit - Number of analogs to return (default 3)
 * @returns {object} Analog state
 */
export function useHistoricalAnalogs({
  autoRefresh = true,
  refreshInterval = 10 * 60 * 1000, // 10 minutes (less frequent than episode)
  limit = 3,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const [analogs, setAnalogs] = useState(null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);

  const fetchAnalogs = useCallback(async () => {
    if (isDemo) {
      setAnalogs(demoData.analogs);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await getEpisodeAnalogs({ limit }, { timeout: 30000 });
      setAnalogs(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [isDemo, demoData, limit]);

  // Initial fetch
  useEffect(() => {
    fetchAnalogs();
  }, [fetchAnalogs]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchAnalogs();
      }
    }, refreshInterval);
    return () => clearInterval(id);
  }, [autoRefresh, refreshInterval, fetchAnalogs]);

  const refresh = useCallback(() => {
    fetchAnalogs();
  }, [fetchAnalogs]);

  return { analogs, loading, error, refresh };
}
