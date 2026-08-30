/**
 * TechnicalDetail — Expandable technical model evaluation metrics.
 *
 * Clearly labeled as "historical model evaluation",
 * NOT current prediction certainty.
 */

import { useState } from 'react';
import { HORIZON_META } from '../../constants';
import { HORIZONS } from '../../constants';

export default function TechnicalDetail({ forecastStatus }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="expandable">
      <button
        className="expandable__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls="technical-detail-content"
      >
        <span>Technical model details</span>
        <span className={`expandable__arrow ${isOpen ? 'expandable__arrow--open' : ''}`} aria-hidden="true">
          ▶
        </span>
      </button>

      {isOpen && (
        <div className="expandable__content" id="technical-detail-content">
          <div className="info-box info-box--info" style={{ marginBottom: 'var(--sp-4)' }}>
            These metrics are from historical model evaluation on held-out test data.
            They describe model quality, not certainty about any individual prediction.
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>Horizon</th>
                <th>Algorithm</th>
                <th>Val MAE</th>
                <th>Val RMSE</th>
                <th>Val R²</th>
                <th>Reliability</th>
              </tr>
            </thead>
            <tbody>
              {HORIZONS.map(h => {
                const meta = HORIZON_META[h];
                return (
                  <tr key={h}>
                    <td style={{ fontWeight: 600 }}>{meta.label}</td>
                    <td className="text-mono text-xs">{meta.algorithm}</td>
                    <td className="text-mono">{meta.valMAE.toFixed(2)} μg/m³</td>
                    <td className="text-mono">{meta.valRMSE.toFixed(2)} μg/m³</td>
                    <td className="text-mono">{meta.valR2.toFixed(3)}</td>
                    <td>{meta.confidence}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Model store status */}
          {forecastStatus?.model_store?.horizons && (
            <div style={{ marginTop: 'var(--sp-4)' }}>
              <h4 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--slate-600)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--sp-2)' }}>
                Model store status
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 'var(--sp-2)' }}>
                {Object.entries(forecastStatus.model_store.horizons).map(([h, info]) => (
                  <div key={h} style={{ padding: 'var(--sp-2)', background: 'var(--surface-raised)', border: 'var(--border-subtle)', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)' }}>
                    <div style={{ fontWeight: 600, color: 'var(--slate-700)' }}>{h}h</div>
                    <div className="text-mono" style={{ color: 'var(--slate-500)' }}>{info.status}</div>
                    {info.algorithm && <div className="text-mono" style={{ color: 'var(--slate-400)' }}>{info.algorithm}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
