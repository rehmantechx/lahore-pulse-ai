/**
 * ModelTransparency — "How this forecast works" section.
 *
 * Explains the forecasting methodology in accessible terms.
 * No marketing language. No "AI analyzed millions" claims.
 */

import { useState } from 'react';
import { HORIZON_META } from '../../constants';

export default function ModelTransparency() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="expandable">
      <button
        className="expandable__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="model-transparency-content"
      >
        <span>How this forecast works</span>
        <span className={`expandable__arrow ${isOpen ? 'expandable__arrow--open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>

      {isOpen && (
        <div className="expandable__content" id="model-transparency-content">
          <div style={{ display: 'grid', gap: 'var(--sp-4)' }}>
            {/* Simple explanation */}
            <div>
              <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
                What this system does
              </h4>
              <p style={{ color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
                Lahore Pulse AI forecasts PM2.5 air-quality levels 1 to 24 hours into the future using
                historical air-quality observations, weather data, and time-based patterns from Lahore.
              </p>
            </div>

            {/* Input sources */}
            <div>
              <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
                Data inputs
              </h4>
              <ul style={{ color: 'var(--slate-600)', paddingLeft: 'var(--sp-5)', lineHeight: 'var(--leading-relaxed)' }}>
                <li>Recent PM2.5 history (up to 96 hours of observations)</li>
                <li>Weather conditions: temperature, humidity, wind speed, pressure</li>
                <li>Air-quality measurements: PM10, NO₂, SO₂, O₃, CO</li>
                <li>Time-of-day and day-of-week patterns</li>
                <li>Historical training data from Lahore (2023–2025)</li>
              </ul>
            </div>

            {/* Method */}
            <div>
              <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
                Forecasting method
              </h4>
              <p style={{ color: 'var(--slate-600)', lineHeight: 'var(--leading-relaxed)' }}>
                Two validated statistical models — <strong>Ridge Regression</strong> for short-term and
                long-term horizons, and <strong>Histogram Gradient Boosting</strong> for 3, 6, and 12-hour
                horizons — were selected through systematic evaluation on held-out data.
              </p>
            </div>

            {/* Confidence by horizon */}
            <div>
              <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
                Reliability by forecast horizon
              </h4>
              <div style={{ display: 'grid', gap: 'var(--sp-2)' }}>
                {Object.entries(HORIZON_META).map(([h, meta]) => (
                  <div key={h} style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-3)' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--slate-500)', width: 36 }}>
                      {meta.shortLabel}
                    </span>
                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--slate-600)' }}>
                      {meta.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Limitations */}
            <div>
              <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--slate-700)' }}>
                Limitations
              </h4>
              <ul style={{ color: 'var(--slate-600)', paddingLeft: 'var(--sp-5)', lineHeight: 'var(--leading-relaxed)' }}>
                <li>Data resolution is limited to 45 km (CAMS grid) — local variations within Lahore are not captured.</li>
                <li>Predictions reflect statistical patterns, not real-time causal understanding.</li>
                <li>Unusual events (fires, construction, policy changes) may not be captured by historical training data.</li>
                <li>Longer-horizon forecasts (12h, 24h) have greater uncertainty than shorter ones.</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
