/**
 * AccessDenied — 403 authorization state component.
 *
 * Shown when an authenticated user attempts to access a route
 * they don't have permission for. Replaces silent redirects
 * with clear authorization feedback.
 */

import { ShieldOff, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function AccessDenied({ requiredRole = 'officer', currentRole, message }) {
  const navigate = useNavigate();

  return (
    <div className="app app--public">
      <main
        className="app-content"
        role="main"
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '70vh',
          padding: 'var(--sp-6)',
        }}
      >
        <div
          style={{
            maxWidth: 480,
            textAlign: 'center',
          }}
        >
          {/* Icon */}
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: '50%',
              background: 'var(--lp-surface-alt, #1e293b)',
              border: '2px solid var(--lp-error, #ef4444)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto var(--sp-5)',
            }}
          >
            <ShieldOff size={32} color="var(--lp-error, #ef4444)" />
          </div>

          {/* Error Code */}
          <div
            style={{
              fontSize: 'var(--text-3xl, 2rem)',
              fontWeight: 800,
              color: 'var(--lp-error, #ef4444)',
              letterSpacing: '0.05em',
              marginBottom: 'var(--sp-2)',
            }}
          >
            403
          </div>

          {/* Title */}
          <h1
            style={{
              fontSize: 'var(--text-xl, 1.25rem)',
              fontWeight: 700,
              color: 'var(--lp-text-primary, #f1f5f9)',
              marginBottom: 'var(--sp-3)',
            }}
          >
            ACCESS RESTRICTED
          </h1>

          {/* Explanation */}
          <p
            style={{
              fontSize: 'var(--text-sm, 0.875rem)',
              color: 'var(--lp-text-tertiary, #94a3b8)',
              lineHeight: 1.6,
              marginBottom: 'var(--sp-4)',
            }}
          >
            {message || `Government authorization is required to access this command surface.`}
          </p>

          {/* Current Role */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--sp-2)',
              padding: 'var(--sp-2) var(--sp-4)',
              background: 'var(--lp-surface, #0f172a)',
              border: '1px solid var(--lp-border, #334155)',
              borderRadius: 8,
              marginBottom: 'var(--sp-5)',
              fontSize: 'var(--text-xs, 0.75rem)',
              color: 'var(--lp-text-secondary, #cbd5e1)',
            }}
          >
            Current role:
            <span
              style={{
                fontWeight: 700,
                color: currentRole === 'admin'
                  ? 'var(--lp-error, #ef4444)'
                  : currentRole === 'officer'
                    ? 'var(--lp-accent, #facc15)'
                    : 'var(--lp-text-primary, #f1f5f9)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              {currentRole || 'unauthenticated'}
            </span>
          </div>

          {/* Required Role */}
          {requiredRole && requiredRole !== currentRole && (
            <div
              style={{
                fontSize: 'var(--text-xs, 0.75rem)',
                color: 'var(--lp-text-muted, #64748b)',
                marginBottom: 'var(--sp-5)',
              }}
            >
              Required role: <strong style={{ color: 'var(--lp-text-secondary, #cbd5e1)' }}>{requiredRole}</strong>
            </div>
          )}

          {/* Return Button */}
          <button
            onClick={() => navigate('/')}
            className="btn btn--primary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--sp-2)',
            }}
          >
            <ArrowLeft size={16} />
            Return to Lahore+
          </button>
        </div>
      </main>
    </div>
  );
}
