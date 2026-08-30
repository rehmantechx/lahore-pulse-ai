/**
 * AIUncertainty — Section 5: Limitations & Uncertainty
 *
 * Shows the AI's own limitations and data gaps.
 * Title: "LIMITATIONS & UNCERTAINTY"
 * This section demonstrates responsible AI by being transparent about what
 * the system does NOT know.
 */

import { AlertCircle, Database } from 'lucide-react';

export default function AIUncertainty({ analysis }) {
  if (!analysis) return null;

  const uncertainties = analysis.uncertainties || [];
  const dataGaps = analysis.data_gaps || [];

  if (uncertainties.length === 0 && dataGaps.length === 0) {
    return null;
  }

  return (
    <div className="ai-uncertainty">
      {uncertainties.length > 0 && (
        <div className="ai-uncertainty__section">
          <div className="ai-uncertainty__header">
            <AlertCircle size={14} className="ai-uncertainty__icon" aria-hidden="true" />
            <span className="ai-uncertainty__label">Limitations</span>
          </div>
          <ul className="ai-uncertainty__list">
            {uncertainties.map((u, i) => (
              <li key={i} className="ai-uncertainty__item">{u}</li>
            ))}
          </ul>
        </div>
      )}

      {dataGaps.length > 0 && (
        <div className="ai-uncertainty__section">
          <div className="ai-uncertainty__header">
            <Database size={14} className="ai-uncertainty__icon" aria-hidden="true" />
            <span className="ai-uncertainty__label">Data Gaps</span>
          </div>
          <ul className="ai-uncertainty__list">
            {dataGaps.map((g, i) => (
              <li key={i} className="ai-uncertainty__item ai-uncertainty__item--gap">{g}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
