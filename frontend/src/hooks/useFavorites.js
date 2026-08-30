/**
 * Lahore Pulse AI — useFavorites hook.
 *
 * Fetches saved locations with live AQ data from the real API.
 * Returns locations with loading/error states and CRUD functions.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useDemoData } from '../demo';
import {
  getFavorites,
  addFavorite,
  updateFavorite,
  deleteFavorite,
} from '../services/api';

/**
 * Fetch and manage saved locations (favorites).
 *
 * @returns {{ locations, loading, error, add, update, remove, refetch }}
 */
export function useFavorites() {
  const demoData = useDemoData();
  const isDemo = Boolean(demoData);

  const [locations, setLocations] = useState(() =>
    isDemo ? (demoData.favorites?.locations || []) : [],
  );
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const fetchFavorites = useCallback(async () => {
    if (isDemo) {
      if (mountedRef.current) {
        setLocations(demoData.favorites?.locations || []);
        setLoading(false);
      }
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await getFavorites();
      if (mountedRef.current) {
        setLocations(
          data && Array.isArray(data.locations) ? data.locations : [],
        );
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        if (err.status === 404) {
          setLocations([]);
          setLoading(false);
        } else {
          setError(err.message);
          setLoading(false);
        }
      }
    }
  }, [isDemo, demoData]);

  useEffect(() => {
    mountedRef.current = true;
    fetchFavorites();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchFavorites]);

  const add = useCallback(
    async (data) => {
      if (isDemo) {
        const newLoc = {
          id: `loc-demo-${Date.now()}`,
          ...data,
          pm25: null,
          pm10: null,
          temperature: null,
          humidity: null,
          aqi: { label: 'No Data', color: '#A09A93', band: 'none' },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setLocations((prev) => [...prev, newLoc]);
        return newLoc;
      }
      const result = await addFavorite(data);
      setLocations((prev) => [...prev, result]);
      return result;
    },
    [isDemo],
  );

  const update = useCallback(
    async (locationId, data) => {
      if (isDemo) {
        setLocations((prev) =>
          prev.map((loc) =>
            loc.id === locationId ? { ...loc, ...data } : loc,
          ),
        );
        return { id: locationId, ...data };
      }
      const result = await updateFavorite(locationId, data);
      setLocations((prev) =>
        prev.map((loc) => (loc.id === locationId ? result : loc)),
      );
      return result;
    },
    [isDemo],
  );

  const remove = useCallback(
    async (locationId) => {
      if (isDemo) {
        setLocations((prev) => prev.filter((loc) => loc.id !== locationId));
        return { status: 'deleted', location_id: locationId };
      }
      await deleteFavorite(locationId);
      setLocations((prev) => prev.filter((loc) => loc.id !== locationId));
      return { status: 'deleted', location_id: locationId };
    },
    [isDemo],
  );

  return {
    locations,
    loading,
    error,
    add,
    update,
    remove,
    refetch: fetchFavorites,
  };
}
