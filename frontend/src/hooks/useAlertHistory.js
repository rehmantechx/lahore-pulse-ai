/**
 * Lahore Pulse AI — useAlertHistory hook.
 *
 * Fetches alert history from the real API or returns demo data.
 * Returns a list of past alerts with type, severity, AQI, message, and timestamp.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useDemoData } from '../demo';
import { getAlertHistory } from '../services/api';

/**
 * Fetch alert history with loading/error states.
 *
 * @param {object} options
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms
 * @returns {object} Alert history state
 */
export function useAlertHistory({
  autoRefresh = false,
  refreshInterval = 10 * 60 * 1000,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [alerts, setAlerts] = useState(() => isDemo ? (demoData.alertHistory || []) : []);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchAlerts = useCallback(async () => {
    if (isDemo) return;
    try {
      setLoading((prev) => !intervalRef.current || prev);
      setError(null);
      const data = await getAlertHistory();
      if (mountedRef.current) {
        setAlerts(Array.isArray(data) ? data : []);
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        // 404 means endpoint doesn't exist yet — empty list is valid
        if (err.status === 404) {
          setAlerts([]);
          setLoading(false);
        } else {
          setError(err.message);
          setLoading(false);
        }
      }
    }
  }, [isDemo]);

  useEffect(() => {
    mountedRef.current = true;
    fetchAlerts();

    if (autoRefresh && !isDemo) {
      intervalRef.current = setInterval(fetchAlerts, refreshInterval);
    }

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAlerts, autoRefresh, refreshInterval, isDemo]);

  return { alerts, loading, error, refetch: fetchAlerts };
}
