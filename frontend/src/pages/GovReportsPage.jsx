/**
 * GovReportsPage — Government report generation.
 *
 * Placeholder for Phase 2.
 */

export default function GovReportsPage() {
  return (
    <div className="page page--wide">
      <h1 className="page__title">Reports</h1>
      <p className="page__subtitle">Generate and export government reports</p>

      <div className="surface" style={{ marginTop: 'var(--sp-6)' }}>
        <div className="surface__body" style={{ textAlign: 'center', padding: 'var(--sp-10)' }}>
          <div style={{ marginBottom: 'var(--sp-3)' }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--lp-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, color: 'var(--lp-text-primary)', marginBottom: 'var(--sp-2)' }}>
            Report Generator
          </h2>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--lp-text-tertiary)', maxWidth: 400, margin: '0 auto' }}>
            Generate official air quality reports for policy review and public communication.
            This feature will be available in a future update.
          </p>
        </div>
      </div>
    </div>
  );
}
