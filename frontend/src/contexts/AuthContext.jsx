/**
 * Authentication context and provider for Lahore+ frontend.
 *
 * Provides:
 *   - AuthProvider: Context provider managing auth state
 *   - useAuth: Hook to access auth state and actions
 *   - login/logout functions
 *   - Token persistence in localStorage
 *   - Centralized RBAC permissions model
 *
 * Roles:
 *   citizen  → VIEW_PUBLIC
 *   officer  → VIEW_PUBLIC + VIEW_GOVERNMENT + VIEW_ANALYTICS + VIEW_REPLAY + VERIFY_PREDICTIONS
 *   admin    → all of above + VIEW_SYSTEM + ADMIN_SYSTEM
 *
 * Backend authorization is authoritative. Frontend permissions are
 * for UI gating only — never trust them for data access decisions.
 */

import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

const AuthContext = createContext(null);

const API_BASE = '/api/v1';

/* ── Centralized Permissions Model ─────────────────────────── */

/** All known permission strings. */
export const PERMISSIONS = Object.freeze({
  VIEW_PUBLIC: 'VIEW_PUBLIC',
  VIEW_GOVERNMENT: 'VIEW_GOVERNMENT',
  VIEW_ANALYTICS: 'VIEW_ANALYTICS',
  VIEW_REPLAY: 'VIEW_REPLAY',
  VERIFY_PREDICTIONS: 'VERIFY_PREDICTIONS',
  VIEW_SYSTEM: 'VIEW_SYSTEM',
  ADMIN_SYSTEM: 'ADMIN_SYSTEM',
});

/** Role → permissions mapping. Frontend-only — backend is authoritative. */
const ROLE_PERMISSIONS = Object.freeze({
  citizen: Object.freeze([
    PERMISSIONS.VIEW_PUBLIC,
  ]),
  officer: Object.freeze([
    PERMISSIONS.VIEW_PUBLIC,
    PERMISSIONS.VIEW_GOVERNMENT,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.VIEW_REPLAY,
    PERMISSIONS.VERIFY_PREDICTIONS,
  ]),
  admin: Object.freeze([
    PERMISSIONS.VIEW_PUBLIC,
    PERMISSIONS.VIEW_GOVERNMENT,
    PERMISSIONS.VIEW_ANALYTICS,
    PERMISSIONS.VIEW_REPLAY,
    PERMISSIONS.VERIFY_PREDICTIONS,
    PERMISSIONS.VIEW_SYSTEM,
    PERMISSIONS.ADMIN_SYSTEM,
  ]),
});

/**
 * Derive a frozen Set of permissions for a given role string.
 * Unknown roles get an empty set (fail-closed).
 */
function permissionsForRole(role) {
  return new Set(ROLE_PERMISSIONS[role] || []);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session from localStorage on mount and validate with backend
  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      try {
        const saved = localStorage.getItem('lahore_plus_auth');
        if (!saved) return;

        const parsed = JSON.parse(saved);
        const expiresAt = parsed.expiresAt || parsed.expires_at;

        // Quick local expiry check first
        if (!expiresAt || new Date(expiresAt) <= new Date()) {
          localStorage.removeItem('lahore_plus_auth');
          return;
        }

        // Validate token with backend /auth/me
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${parsed.token}` },
        });

        if (!res.ok) {
          // Token invalid or expired server-side — clear session
          localStorage.removeItem('lahore_plus_auth');
          return;
        }

        const me = await res.json();
        if (!cancelled) {
          setUser({
            username: me.username,
            role: me.role,
            displayName: me.username,
            token: parsed.token,
            expiresAt: me.expires_at,
          });
          setToken(parsed.token);
        }
      } catch {
        // Network error on restore — clear stale session
        localStorage.removeItem('lahore_plus_auth');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    restoreSession();
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (username, password) => {
    let res;
    try {
      res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
    } catch {
      throw new Error('Cannot reach server. Please check your connection.');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }

    const data = await res.json();
    const userData = {
      username: data.role === 'citizen' ? username : data.display_name,
      role: data.role,
      displayName: data.display_name,
      token: data.token,
      expiresAt: data.expires_at,
    };

    setUser(userData);
    setToken(data.token);
    localStorage.setItem('lahore_plus_auth', JSON.stringify(userData));
    return userData;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('lahore_plus_auth');
  }, []);

  /* ── Derived state ──────────────────────────────────────── */
  const isGovernment = user?.role === 'officer' || user?.role === 'admin';
  const isAdmin = user?.role === 'admin';

  /** Centralized permissions Set for the current user. */
  const permissions = useMemo(
    () => permissionsForRole(user?.role),
    [user?.role],
  );

  /** Check if the current user has a specific permission. */
  const hasPermission = useCallback(
    (perm) => permissions.has(perm),
    [permissions],
  );

  const value = useMemo(() => ({
    user,
    token,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isGovernment,
    isAdmin,
    permissions,
    hasPermission,
  }), [user, token, loading, login, logout, isGovernment, isAdmin, permissions, hasPermission]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

/**
 * Hook for checking a single permission.
 * Convenience wrapper around useAuth().hasPermission.
 */
export function usePermission(permission) {
  const { hasPermission } = useAuth();
  return hasPermission(permission);
}
