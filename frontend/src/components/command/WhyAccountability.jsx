/**
 * WhyAccountability — "Why This Matters" moment for the judge.
 *
 * One concise explanation of why accountability matters.
 * Should appear near the Accountability Loop, above the fold.
 */

export default function WhyAccountability() {
  return (
    <div className="cc-section cc-section--compact" data-testid="why-accountability">
      <div className="surface surface--tinted" style={{
        padding: 'var(--sp-3) var(--sp-5)',
        borderLeft: '3px solid var(--brand-600, #0d9488)',
        background: 'linear-gradient(135deg, #f0fdfa 0%, var(--lp-bg-surface, #fff) 100%)',
      }}>
        <div style={{ display: 'flex', gap: 'var(--sp-4)', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <p style={{
              fontSize: 13,
              lineHeight: 1.6,
              color: 'var(--lp-text-secondary, #475569)',
              margin: 0,
            }}>
              Most air-quality systems answer: <strong style={{ color: 'var(--lp-text-primary, #0f172a)' }}>"What is the air quality?"</strong>
              {' '}Lahore+ also asks: <strong style={{ color: 'var(--brand-600, #0d9488)' }}>"Was our prediction correct?"</strong>
              {' '}Every forecast becomes a measurable record once reality arrives.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
