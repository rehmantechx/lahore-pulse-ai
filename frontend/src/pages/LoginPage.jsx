/**
 * Login page for Lahore+ Command Center.
 *
 * Role-based login for hackathon demo.
 * Credentials are validated server-side via bcrypt.
 *
 * Design matches Lahore+ premium civic-tech brand.
 */

import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/government';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const userData = await login(username, password);
      // Redirect based on role
      if (userData.role === 'citizen') {
        navigate('/citizen', { replace: true });
      } else {
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="app app--public">
      <main
        className="app-content"
        role="main"
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: 'calc(100vh - 64px)',
          padding: 'var(--sp-6)',
          background: 'var(--lp-bg-secondary)',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: '420px',
            background: 'var(--lp-bg-primary)',
            border: '1px solid var(--lp-border-subtle)',
            borderRadius: 'var(--lp-radius-lg)',
            padding: 'var(--sp-8)',
            boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
          }}
        >
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 'var(--sp-6)' }}>
            <h1
              style={{
                fontSize: 'var(--text-2xl)',
                fontWeight: 700,
                color: 'var(--lp-text-primary)',
                marginBottom: 'var(--sp-2)',
              }}
            >
              Command Center
            </h1>
            <p
              style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--lp-text-tertiary)',
              }}
            >
              Punjab Pollution Response Intelligence
            </p>
            <div style={{
              marginTop: 'var(--sp-3)',
              padding: '6px 12px',
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: 'var(--lp-radius-sm)',
              fontSize: 'var(--text-xs)',
              color: '#1E40AF',
              display: 'inline-block',
            }}>
              Authorized Access Only — Demo Mode
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit}>
            {error && (
              <div
                role="alert"
                style={{
                  padding: 'var(--sp-3)',
                  marginBottom: 'var(--sp-4)',
                  background: '#FEF2F2',
                  border: '1px solid #FECACA',
                  borderRadius: 'var(--lp-radius-sm)',
                  color: '#991B1B',
                  fontSize: 'var(--text-sm)',
                }}
              >
                {error}
              </div>
            )}

            <div style={{ marginBottom: 'var(--sp-4)' }}>
              <label
                htmlFor="username"
                style={{
                  display: 'block',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 500,
                  color: 'var(--lp-text-secondary)',
                  marginBottom: 'var(--sp-2)',
                }}
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
                style={{
                  width: '100%',
                  padding: 'var(--sp-3)',
                  border: '1px solid var(--lp-border-subtle)',
                  borderRadius: 'var(--lp-radius-sm)',
                  fontSize: 'var(--text-md)',
                  color: 'var(--lp-text-primary)',
                  background: 'var(--lp-bg-primary)',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ marginBottom: 'var(--sp-6)' }}>
              <label
                htmlFor="password"
                style={{
                  display: 'block',
                  fontSize: 'var(--text-sm)',
                  fontWeight: 500,
                  color: 'var(--lp-text-secondary)',
                  marginBottom: 'var(--sp-2)',
                }}
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                style={{
                  width: '100%',
                  padding: 'var(--sp-3)',
                  border: '1px solid var(--lp-border-subtle)',
                  borderRadius: 'var(--lp-radius-sm)',
                  fontSize: 'var(--text-md)',
                  color: 'var(--lp-text-primary)',
                  background: 'var(--lp-bg-primary)',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              style={{
                width: '100%',
                padding: 'var(--sp-3)',
                background: 'var(--lp-brand-600)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--lp-radius-sm)',
                fontSize: 'var(--text-md)',
                fontWeight: 600,
                cursor: submitting ? 'not-allowed' : 'pointer',
                opacity: submitting ? 0.7 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              {submitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Demo hint — role names only, no passwords exposed in source */}
          <div style={{ marginTop: 'var(--sp-6)' }}>
            <p
              style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--lp-text-tertiary)',
                textAlign: 'center',
                marginBottom: 'var(--sp-3)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Available Roles
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
              {[
                { role: 'Citizen', desc: 'Public access — view air quality data' },
                { role: 'Officer', desc: 'Command center — monitor and respond' },
                { role: 'Admin', desc: 'Full access — system administration' },
              ].map((item) => (
                <div
                  key={item.role}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: 'var(--sp-3)',
                    background: 'var(--lp-bg-secondary)',
                    border: '1px solid var(--lp-border-subtle)',
                    borderRadius: 'var(--lp-radius-sm)',
                    textAlign: 'left',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 'var(--text-sm)',
                        fontWeight: 600,
                        color: 'var(--lp-text-primary)',
                      }}
                    >
                      {item.role}
                    </div>
                    <div
                      style={{
                        fontSize: 'var(--text-xs)',
                        color: 'var(--lp-text-tertiary)',
                      }}
                    >
                      {item.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Back to public */}
          <div style={{ marginTop: 'var(--sp-4)', textAlign: 'center' }}>
            <Link
              to="/"
              style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--lp-brand-600)',
                textDecoration: 'none',
              }}
            >
              ← Back to Lahore+
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
