/**
 * Lahore Pulse AI — useAlertPreferences hook.
 *
 * Fetches and updates alert preferences from the real API.
 * Returns preferences with loading/error states and an update function.
 */

import { useState, useEffect, useCallback } from 'react';
import { useDemoData } from '../demo';
import { getAlertPreferences, updateAlertPreferences } from '../services/api';

const DEFAULT_PREFS = [
  { id: 'pref-fair', alert_type: 'fair', enabled: false, threshold: 35 },
  { id: 'pref-moderate', alert_type: 'moderate', enabled: false, threshold: 55 },
  { id: 'pref-poor', alert_type: 'poor', enabled: false, threshold: 90 },
  { id: 'pref-dangerous', alert_type: 'dangerous', enabled: false, threshold: 150 },
];

/**
 * Fetch and manage alert preferences.
 *
 * @returns {{ prefs, loading, error, togglePref }}
 */
export function useAlertPreferences() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  // In demo mode, start with all disabled (matching UI default)
  const [prefs, setPrefs] = useState(() => {
    if (isDemo) return DEFAULT_PREFS;
    return DEFAULT_PREFS; // will be replaced by API data
  });
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);

  const fetchPrefs = useCallback(async () => {
    if (isDemo) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getAlertPreferences();
      if (Array.isArray(data) && data.length > 0) {
        setPrefs(data);
      }
      setLoading(false);
    } catch (err) {
      if (err.status === 404) {
        // Endpoint doesn't exist yet — keep defaults
        setPrefs(DEFAULT_PREFS);
        setLoading(false);
      } else {
        setError(err.message);
        setLoading(false);
      }
    }
  }, [isDemo]);

  useEffect(() => {
    fetchPrefs();
  }, [fetchPrefs]);

  /**
   * Toggle a preference and persist to backend.
   * @param {string} alertType - 'fair' | 'moderate' | 'poor' | 'dangerous'
   */
  const togglePref = useCallback(async (alertType) => {
    // Optimistic update
    setPrefs((prev) =>
      prev.map((p) =>
        p.alert_type === alertType ? { ...p, enabled: !p.enabled } : p
      )
    );

    if (isDemo) return; // no backend in demo mode

    try {
      // Get the new enabled state after optimistic update
      const currentPref = prefs.find((p) => p.alert_type === alertType);
      const newEnabled = !currentPref?.enabled;

      await updateAlertPreferences([
        { alert_type: alertType, enabled: newEnabled },
      ]);
    } catch (err) {
      // Revert optimistic update on failure
      setPrefs((prev) =>
        prev.map((p) =>
          p.alert_type === alertType ? { ...p, enabled: !p.enabled } : p
        )
      );
      setError(err.message);
    }
  }, [prefs, isDemo]);

  return { prefs, loading, error, togglePref };
}
