/**
 * GovInvestigationsPage — Government investigation management.
 *
 * Placeholder for Phase 2.
 */

export default function GovInvestigationsPage() {
  return (
    <div className="page page--wide">
      <h1 className="page__title">Investigations</h1>
      <p className="page__subtitle">Source investigation and evidence tracking</p>

      <div className="surface" style={{ marginTop: 'var(--sp-6)' }}>
        <div className="surface__body" style={{ textAlign: 'center', padding: 'var(--sp-10)' }}>
          <div style={{ marginBottom: 'var(--sp-3)' }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--lp-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, color: 'var(--lp-text-primary)', marginBottom: 'var(--sp-2)' }}>
            Investigation Tracker
          </h2>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-tertiary)', maxWidth: 400, margin: '0 auto' }}>
            Track investigation workflows, evidence chains, and source attribution.
            This feature will be available in a future update.
          </p>
        </div>
      </div>
    </div>
  );
}
