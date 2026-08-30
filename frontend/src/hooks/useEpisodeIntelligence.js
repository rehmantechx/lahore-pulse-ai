/**
 * Lahore Pulse AI - useEpisodeIntelligence hook.
 *
 * Fetches episode intelligence data with loading/error states.
 * Episode intelligence is rule-based detection, NOT machine learning.
 *
 * Data includes: episode state, trajectory, weather context, narrative.
 * Uses ML forecasts as one input signal, but the detection logic is
 * entirely rule-based (Definition 4: PM2.5 > 120 AND rise >= 30 in 6h).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getEpisodeIntelligence, ApiError, NetworkError, TimeoutError } from '../services/api';
import { useDemoData } from '../demo';

/**
 * Fetch episode intelligence with controlled refresh.
 *
 * @param {object} options
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms
 * @returns {object} Episode intelligence state
 */
export function useEpisodeIntelligence({
  autoRefresh = true,
  refreshInterval = 5 * 60 * 1000,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  // In demo mode, immediately return demo data — no API calls
  const [episode, setEpisode] = useState(() => isDemo ? (demoData.episode || null) : null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const [lastFetchTime, setLastFetchTime] = useState(isDemo ? new Date() : null);
  const [isStale, setIsStale] = useState(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);
  const episodeRef = useRef(episode);

  const fetchEpisode = useCallback(async () => {
    try {
      if (!episodeRef.current) setLoading(true);
      setError(null);

      const data = await getEpisodeIntelligence({ timeout: 45000 });

      if (!mountedRef.current) return;

      episodeRef.current = data;
      setEpisode(data);
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

  // Initial fetch
  useEffect(() => {
    if (isDemo) {
      setLoading(false);
      setLastFetchTime(new Date());
      return;
    }
    mountedRef.current = true;
    fetchEpisode();
    return () => { mountedRef.current = false; };
  }, [isDemo]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || isDemo) return;

    intervalRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') {
        setIsStale(true);
        fetchEpisode();
      }
    }, refreshInterval);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, refreshInterval, fetchEpisode]);

  // Visibility-based refresh
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible' && isStale) {
        fetchEpisode();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [isStale, fetchEpisode]);

  const refresh = useCallback(() => {
    fetchEpisode();
  }, [fetchEpisode]);

  const state = loading ? 'loading' : error ? 'error' : episode ? 'success' : 'empty';

  return {
    episode,
    loading,
    error,
    isStale,
    lastFetchTime,
    state,
    refresh,
  };
}
