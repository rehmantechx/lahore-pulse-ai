/**
 * useVerification — Fetches and manages investigation verification data.
 *
 * In demo mode, returns the deterministic DEMO_VERIFICATION fixture.
 * In live mode, calls verification API endpoints.
 *
 * Returns: { outcome, stats, context, loading, error, refresh, submit, update }
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  submitVerification,
  updateVerification,
  getVerificationStats,
  getVerificationContext,
  ApiError,
  NetworkError,
  TimeoutError,
} from '../services/api';
import { useDemoData } from '../demo';

/**
 * Fetch verification data for an investigation.
 *
 * @param {object} options
 * @param {string} options.investigationId - Investigation to get context for
 * @param {boolean} options.autoRefresh - Auto-refresh on interval
 * @param {number} options.refreshInterval - Refresh interval in ms (default 5 min)
 * @returns {object} Verification state and actions
 */
export function useVerification({
  investigationId = null,
  autoRefresh = false,
  refreshInterval = 5 * 60 * 1000,
} = {}) {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  // Demo mode: return demo verification data
  const demoVerification = isDemo ? (demoData.verification || null) : null;

  const [stats, setStats] = useState(() =>
    isDemo ? (demoVerification?.stats || demoData.verificationStats || null) : null
  );
  const [context, setContext] = useState(() =>
    isDemo ? demoVerification : null
  );
  const [outcome, setOutcome] = useState(() =>
    isDemo ? (demoVerification?.current_outcome || null) : null
  );
  const [loading, setLoading] = useState(!isDemo && Boolean(investigationId));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchContext = useCallback(async () => {
    if (!investigationId) return;

    try {
      if (!context) setLoading(true);
      setError(null);

      const data = await getVerificationContext(
        investigationId,
        { signal: AbortSignal.timeout(15000) }
      );

      if (!mountedRef.current) return;

      setContext(data);
      setOutcome(data.current_outcome || null);
      setStats(data.stats || null);
    } catch (err) {
      if (!mountedRef.current) return;

      if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
        setError(err);
      } else {
        setError(new NetworkError(`Verification fetch error: ${err.message}`));
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [investigationId, context]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await getVerificationStats({ signal: AbortSignal.timeout(10000) });
      if (!mountedRef.current) return;
      setStats(data);
    } catch (err) {
      // Stats failure is non-critical
    }
  }, []);

  // Initial fetch (live mode only)
  useEffect(() => {
    if (!isDemo) {
      if (investigationId) fetchContext();
      fetchStats();
    }
    return () => { mountedRef.current = false; };
  }, [isDemo, investigationId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh
  useEffect(() => {
    if (isDemo || !autoRefresh) return;

    intervalRef.current = setInterval(() => {
      if (investigationId) fetchContext();
      fetchStats();
    }, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isDemo, autoRefresh, refreshInterval, investigationId, fetchContext, fetchStats]);

  const submit = useCallback(async (verificationData) => {
    if (isDemo) {
      // In demo mode, simulate success
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);
      return { success: true };
    }

    setSubmitting(true);
    setError(null);
    setSubmitSuccess(false);

    try {
      const result = await submitVerification(verificationData, {
        signal: AbortSignal.timeout(15000),
      });

      if (!mountedRef.current) return result;

      setOutcome(result);
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);

      // Refresh context and stats
      await fetchContext();
      await fetchStats();

      return result;
    } catch (err) {
      if (!mountedRef.current) return null;

      if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
        setError(err);
      } else {
        setError(new NetworkError(`Submit error: ${err.message}`));
      }
      return null;
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  }, [isDemo, fetchContext, fetchStats]);

  const update = useCallback(async (outcomeId, updateData) => {
    if (isDemo) {
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);
      return { success: true };
    }

    setSubmitting(true);
    setError(null);

    try {
      const result = await updateVerification(outcomeId, updateData, {
        signal: AbortSignal.timeout(15000),
      });

      if (!mountedRef.current) return result;

      setOutcome(result);
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);

      await fetchContext();
      await fetchStats();

      return result;
    } catch (err) {
      if (!mountedRef.current) return null;

      if (err instanceof ApiError || err instanceof NetworkError || err instanceof TimeoutError) {
        setError(err);
      } else {
        setError(new NetworkError(`Update error: ${err.message}`));
      }
      return null;
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  }, [isDemo, fetchContext, fetchStats]);

  return {
    outcome,
    stats,
    context,
    loading,
    submitting,
    error,
    submitSuccess,
    refresh: useCallback(() => {
      if (investigationId) fetchContext();
      fetchStats();
    }, [investigationId, fetchContext, fetchStats]),
    submit,
    update,
  };
}
