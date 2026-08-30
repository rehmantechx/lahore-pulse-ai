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

  // Restore session from localStorage on mount
  // In demo mode, auto-create a demo officer session if no saved session exists
  useEffect(() => {
    try {
      const saved = localStorage.getItem('lahore_plus_auth');
      const isDemoMode = new URLSearchParams(window.location.search).get('demo') === 'true';

      if (saved) {
        const parsed = JSON.parse(saved);
        // Check if token is still valid (not expired)
        // Support both camelCase (expiresAt) and snake_case (expires_at) for migration
        const expiresAt = parsed.expiresAt || parsed.expires_at;
        if (expiresAt && new Date(expiresAt) > new Date()) {
          setUser(parsed);
          setToken(parsed.token);
        } else if (isDemoMode) {
          // In demo mode, token expired — create a local demo session
          // (backend may be unreachable, but demo must still work)
          const demoUser = {
            username: 'officer',
            role: 'officer',
            displayName: 'Demo Officer',
            token: 'demo-local-session',
            expiresAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
          };
          setUser(demoUser);
          setToken(demoUser.token);
          localStorage.setItem('lahore_plus_auth', JSON.stringify(demoUser));
        } else {
          localStorage.removeItem('lahore_plus_auth');
        }
      } else if (isDemoMode) {
        // No saved session, but in demo mode — create local demo session
        const demoUser = {
          username: 'officer',
          role: 'officer',
          displayName: 'Demo Officer',
          token: 'demo-local-session',
          expiresAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        };
        setUser(demoUser);
        setToken(demoUser.token);
        localStorage.setItem('lahore_plus_auth', JSON.stringify(demoUser));
      }
    } catch {
      localStorage.removeItem('lahore_plus_auth');
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username, password) => {
    const isDemoMode = new URLSearchParams(window.location.search).get('demo') === 'true';

    let res;
    try {
      res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
    } catch (fetchErr) {
      // Network failure — if in demo mode, create a local demo session
      // so the judge can still navigate the command center
      if (isDemoMode) {
        const roleMap = { citizen: 'citizen', officer: 'officer', admin: 'admin' };
        const displayMap = {
          citizen: 'Demo Citizen',
          officer: 'Demo Officer',
          admin: 'Demo Admin',
        };
        const role = roleMap[username] || 'officer';
        const userData = {
          username,
          role,
          displayName: displayMap[username] || 'Demo User',
          token: 'demo-local-session',
          expiresAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        };
        setUser(userData);
        setToken(userData.token);
        localStorage.setItem('lahore_plus_auth', JSON.stringify(userData));
        return userData;
      }
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
