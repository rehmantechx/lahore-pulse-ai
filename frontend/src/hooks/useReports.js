/**
 * Lahore Pulse AI — useReports hook.
 *
 * Fetches available reports from the real API or returns demo data.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useDemoData } from '../demo';
import { getReportHistory } from '../services/api';

/**
 * Fetch reports with loading/error states.
 *
 * @returns {object} Reports state
 */
export function useReports() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [reports, setReports] = useState(() => isDemo ? (demoData.reports || []) : []);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const fetchReports = useCallback(async () => {
    if (isDemo) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getReportHistory();
      if (mountedRef.current) {
        setReports(Array.isArray(data) ? data : []);
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        if (err.status === 404) {
          setReports([]);
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
    fetchReports();
    return () => { mountedRef.current = false; };
  }, [fetchReports]);

  return { reports, loading, error, refetch: fetchReports };
}
