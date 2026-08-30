/**
 * Lahore Pulse AI — useHealth hook.
 *
 * Monitors backend health and readiness with low-frequency polling.
 * Used by the StatusBar component.
 */

import { useState, useEffect, useCallback } from 'react';
import { getReadiness, NetworkError, TimeoutError } from '../services/api';
import { useDemoData } from '../demo';

const HEALTH_POLL_MS = 30000; // 30 seconds

export function useHealth() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);
  const [status, setStatus] = useState(isDemo ? { status: 'demo' } : null);
  const [loading, setLoading] = useState(!isDemo);
  const [online, setOnline] = useState(isDemo);

  const checkHealth = useCallback(async () => {
    if (isDemo) return;
    try {
      const data = await getReadiness({ timeout: 20000 });
      setStatus(data);
      setOnline(data.status === 'ready' || data.status === 'healthy');
      setLoading(false);
    } catch {
      // Retry once after a short delay to handle startup race conditions
      try {
        await new Promise(r => setTimeout(r, 2000));
        const data = await getReadiness({ timeout: 20000 });
        setStatus(data);
        setOnline(data.status === 'ready' || data.status === 'healthy');
      } catch {
        setStatus(null);
        setOnline(false);
      } finally {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (isDemo) return;
    checkHealth();
    const interval = setInterval(checkHealth, HEALTH_POLL_MS);
    return () => clearInterval(interval);
  }, [checkHealth, isDemo]);

  return { status, loading, online, refresh: checkHealth };
}
