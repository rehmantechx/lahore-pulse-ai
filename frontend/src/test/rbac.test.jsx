/**
 * AuthContext — RBAC Tests (Phase 27).
 *
 * Verifies:
 * - PERMISSIONS constants defined
 * - hasPermission works for each role via login
 * - Citizen role gets only VIEW_PUBLIC
 * - Officer role gets citizen + government permissions
 * - Admin role gets all permissions
 * - permissions is a Set
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../demo', () => ({
  useDemoData: vi.fn(() => null),
}));

vi.mock('../services/api', () => ({
  login: vi.fn(),
  getStations: vi.fn(),
}));

import { AuthProvider, useAuth, PERMISSIONS } from '../contexts/AuthContext';

function TestComponent({ onRender }) {
  const auth = useAuth();
  onRender(auth);
  return <div>test</div>;
}

async function getAuthValue(sessionData) {
  if (sessionData) {
    localStorage.setItem('lahore_plus_auth', JSON.stringify(sessionData));
  }
  let authValue;
  await act(async () => {
    render(
      <AuthProvider>
        <TestComponent onRender={(v) => { authValue = v; }} />
      </AuthProvider>
    );
  });
  // If session was provided, wait for user to be set
  if (sessionData) {
    await waitFor(() => {
      expect(authValue.user).not.toBeNull();
    }, { timeout: 5000 });
  }
  return authValue;
}

function makeSession(role) {
  return {
    username: role === 'citizen' ? 'testuser' : role,
    role,
    displayName: `Test ${role}`,
    token: 'test-token',
    expires_at: new Date(Date.now() + 3600000).toISOString(),
  };
}

describe('AuthContext RBAC', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('exports PERMISSIONS constants', () => {
    expect(PERMISSIONS).toBeDefined();
    expect(PERMISSIONS.VIEW_PUBLIC).toBe('VIEW_PUBLIC');
    expect(PERMISSIONS.VIEW_GOVERNMENT).toBe('VIEW_GOVERNMENT');
    expect(PERMISSIONS.VIEW_ANALYTICS).toBe('VIEW_ANALYTICS');
    expect(PERMISSIONS.VIEW_REPLAY).toBe('VIEW_REPLAY');
    expect(PERMISSIONS.VERIFY_PREDICTIONS).toBe('VERIFY_PREDICTIONS');
    expect(PERMISSIONS.VIEW_SYSTEM).toBe('VIEW_SYSTEM');
    expect(PERMISSIONS.ADMIN_SYSTEM).toBe('ADMIN_SYSTEM');
  });

  it('provides hasPermission function', () => {
    let authValue;
    render(
      <AuthProvider>
        <TestComponent onRender={(v) => { authValue = v; }} />
      </AuthProvider>
    );
    expect(typeof authValue.hasPermission).toBe('function');
  });

  it('provides permissions as a Set', () => {
    let authValue;
    render(
      <AuthProvider>
        <TestComponent onRender={(v) => { authValue = v; }} />
      </AuthProvider>
    );
    expect(authValue.permissions).toBeInstanceOf(Set);
  });

  it('no permissions when logged out', () => {
    let authValue;
    render(
      <AuthProvider>
        <TestComponent onRender={(v) => { authValue = v; }} />
      </AuthProvider>
    );
    expect(authValue.user).toBeNull();
    expect(authValue.hasPermission(PERMISSIONS.VIEW_PUBLIC)).toBe(false);
  });

  it('citizen has VIEW_PUBLIC but not VIEW_GOVERNMENT', async () => {
    const authValue = await getAuthValue(makeSession('citizen'));
    expect(authValue.user.role).toBe('citizen');
    expect(authValue.hasPermission(PERMISSIONS.VIEW_PUBLIC)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_GOVERNMENT)).toBe(false);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_ANALYTICS)).toBe(false);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_REPLAY)).toBe(false);
    expect(authValue.hasPermission(PERMISSIONS.VERIFY_PREDICTIONS)).toBe(false);
  });

  it('officer has government + analytics + replay + verify but not admin', async () => {
    const authValue = await getAuthValue(makeSession('officer'));
    expect(authValue.user.role).toBe('officer');
    expect(authValue.hasPermission(PERMISSIONS.VIEW_PUBLIC)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_GOVERNMENT)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_ANALYTICS)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_REPLAY)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VERIFY_PREDICTIONS)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.ADMIN_SYSTEM)).toBe(false);
  });

  it('admin has all permissions', async () => {
    const authValue = await getAuthValue(makeSession('admin'));
    expect(authValue.user.role).toBe('admin');
    expect(authValue.hasPermission(PERMISSIONS.VIEW_PUBLIC)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_GOVERNMENT)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_ANALYTICS)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_REPLAY)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VERIFY_PREDICTIONS)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.VIEW_SYSTEM)).toBe(true);
    expect(authValue.hasPermission(PERMISSIONS.ADMIN_SYSTEM)).toBe(true);
  });
});
