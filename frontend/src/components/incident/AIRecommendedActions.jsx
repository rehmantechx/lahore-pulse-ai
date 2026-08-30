/**
 * AIRecommendedActions — Section 6: Recommended Investigation Actions
 *
 * Shows top 3 recommended actions with priority, rationale, and verification goal.
 * Priority 1 is immediately obvious.
 */

import { ArrowRight, CheckCircle } from 'lucide-react';

const PRIORITY_COLORS = {
  1: { color: '#dc2626', bg: '#fef2f2', border: '#fecaca', num: '#dc2626' },
  2: { color: '#d97706', bg: '#fffbeb', border: '#fde68a', num: '#d97706' },
  3: { color: '#0d9488', bg: '#f0fdf4', border: '#ccfbf1', num: '#0d9488' },
};

function ActionCard({ action, isFirst }) {
  const style = PRIORITY_COLORS[action.priority] || PRIORITY_COLORS[3];

  return (
    <div
      className={`ai-actions__card ${isFirst ? 'ai-actions__card--first' : ''}`}
      style={isFirst ? { borderColor: style.border, background: style.bg } : undefined}
    >
      <div className="ai-actions__card-header">
        <span
          className="ai-actions__priority-num"
          style={{ color: style.num }}
        >
          {action.priority}
        </span>
        <span className="ai-actions__action-text">{action.action}</span>
      </div>
      {action.rationale && (
        <div className="ai-actions__rationale">
          <ArrowRight size={12} color="var(--lp-text-tertiary)" aria-hidden="true" />
          <span>{action.rationale}</span>
        </div>
      )}
      {action.verification_goal && (
        <div className="ai-actions__verification">
          <CheckCircle size={12} color="#0d9488" aria-hidden="true" />
          <span className="ai-actions__verification-label">Verification goal:</span>{' '}
          {action.verification_goal}
        </div>
      )}
    </div>
  );
}

export default function AIRecommendedActions({ actions }) {
  if (!actions || actions.length === 0) return null;

  const sorted = [...actions].sort((a, b) => a.priority - b.priority);

  return (
    <div className="ai-actions">
      {sorted.map((action, i) => (
        <ActionCard key={action.priority || i} action={action} isFirst={i === 0} />
      ))}
    </div>
  );
}
