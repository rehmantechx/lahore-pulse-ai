/**
 * GovSystemPage — Government system health and configuration.
 *
 * Placeholder for Phase 2.
 */

import { useHealth } from '../hooks/useHealth';

export default function GovSystemPage() {
  const { status, lastFetchTime } = useHealth();

  return (
    <div className="page page--wide">
      <h1 className="page__title">System</h1>
      <p className="page__subtitle">System health and configuration</p>

      <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="surface__header">
          <span className="surface__title">System Status</span>
        </div>
        <div className="surface__body">
          <div style={{ display: 'grid', gap: 'var(--sp-3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-secondary)' }}>API Connection</span>
              <span className={`status-dot status-dot--${status}`} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-secondary)' }}>Last Data Fetch</span>
              <span style={{ fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)', color: 'var(--lp-text-primary)' }}>
                {lastFetchTime ? new Date(lastFetchTime).toLocaleTimeString() : '—'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="surface" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="surface__body" style={{ textAlign: 'center', padding: 'var(--sp-8)' }}>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-tertiary)' }}>
            Detailed system configuration, data source management, and user administration 
            will be available in a future update.
          </p>
        </div>
      </div>
    </div>
  );
}
