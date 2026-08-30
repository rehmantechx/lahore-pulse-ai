/**
 * AISummary — Section 2: "What Happened"
 *
 * Displays the AI event summary and severity assessment.
 * Must be readable in <10 seconds. No jargon, no source attribution.
 */

import { AlertTriangle } from 'lucide-react';

export default function AISummary({ analysis }) {
  if (!analysis) return null;

  const summary = analysis.event_summary;
  const severity = analysis.severity_assessment;

  return (
    <div className="ai-summary">
      {summary && (
        <p className="ai-summary__text">{summary}</p>
      )}
      {severity && (
        <div className="ai-summary__severity">
          <AlertTriangle size={14} className="ai-summary__severity-icon" aria-hidden="true" />
          <span className="ai-summary__severity-label">Severity Assessment</span>
          <span className="ai-summary__severity-text">{severity}</span>
        </div>
      )}
    </div>
  );
}
