/**
 * Protected route wrapper for government/admin pages.
 *
 * Shows AccessDenied (403) if user lacks required role/permission.
 * Shows loading state while auth state is being restored from localStorage.
 *
 * Uses centralized RBAC from AuthContext. Backend authorization is
 * authoritative — this component only gates UI visibility.
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth, PERMISSIONS } from '../../contexts/AuthContext.jsx';
import AccessDenied from './AccessDenied.jsx';

export default function ProtectedRoute({ children, requiredRole = 'officer', requiredPermission }) {
  const { isAuthenticated, loading, user, hasPermission } = useAuth();
  const location = useLocation();

  // Show loading while restoring session
  if (loading) {
    return (
      <div className="app app--public">
        <main
          className="app-content"
          role="main"
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '60vh',
            color: 'var(--lp-text-tertiary)',
          }}
        >
          <p>Loading...</p>
        </main>
      </div>
    );
  }

  // Not authenticated — redirect to login with return URL
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    );
  }

  // Permission-based guard (if a specific permission is required)
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <AccessDenied
        requiredRole={requiredRole}
        currentRole={user?.role}
        message={`You need the "${requiredPermission}" permission to access this page.`}
      />
    );
  }

  // Check role requirements — show 403 instead of silent redirect
  if (requiredRole === 'admin' && user?.role !== 'admin') {
    return (
      <AccessDenied
        requiredRole="admin"
        currentRole={user?.role}
        message="This page requires administrator authorization. Government administrators can manage system configuration and verification controls."
      />
    );
  }

  if (requiredRole === 'officer' && user?.role === 'citizen') {
    return (
      <AccessDenied
        requiredRole="officer"
        currentRole={user?.role}
        message="Government authorization is required to access this command surface."
      />
    );
  }

  return children;
}
