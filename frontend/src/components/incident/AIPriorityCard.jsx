/**
 * AIPriorityCard — Section 3: Investigation Priority
 *
 * Visual centerpiece — shows WHERE to investigate first.
 * MUST NOT say "Pollution came from here" — use "Priority investigation area".
 * Shows area, priority level, confidence, rationale.
 */

import { Target, TrendingUp } from 'lucide-react';

const PRIORITY_STYLES = {
  HIGH: {
    color: '#dc2626',
    bg: '#fef2f2',
    border: '#fecaca',
    icon: '#dc2626',
  },
  MEDIUM: {
    color: '#d97706',
    bg: '#fffbeb',
    border: '#fde68a',
    icon: '#d97706',
  },
  LOW: {
    color: '#16a34a',
    bg: '#f0fdf4',
    border: '#bbf7d0',
    icon: '#16a34a',
  },
};

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="ai-priority__confidence-bar">
      <div className="ai-priority__confidence-track">
        <div
          className="ai-priority__confidence-fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="ai-priority__confidence-label">{pct}% confidence</span>
    </div>
  );
}

export default function AIPriorityCard({ priority }) {
  if (!priority) return null;

  const style = PRIORITY_STYLES[priority.priority] || PRIORITY_STYLES.MEDIUM;

  return (
    <div className="ai-priority" style={{ borderColor: style.border }}>
      <div className="ai-priority__header">
        <Target size={18} color={style.icon} className="ai-priority__icon" aria-hidden="true" />
        <span className="ai-priority__label">Priority Investigation Area</span>
        <span
          className="ai-priority__badge"
          style={{ color: style.color, background: style.bg, border: `1px solid ${style.border}` }}
        >
          {priority.priority}
        </span>
      </div>
      <div className="ai-priority__area">{priority.area}</div>
      {priority.rationale && (
        <div className="ai-priority__rationale">{priority.rationale}</div>
      )}
      <ConfidenceBar value={priority.confidence} />
    </div>
  );
}
