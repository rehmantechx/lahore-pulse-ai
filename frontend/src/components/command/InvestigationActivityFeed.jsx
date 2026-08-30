/**
 * InvestigationActivityFeed — Simulated processing activity for the demo.
 *
 * Shows what the system is doing during the investigation.
 * Progressive, deterministic, driven by demoStep.
 *
 * Categories: OBSERVED, DETERMINISTIC, DATA RETRIEVAL, AI ANALYSIS, AI OUTPUT, HUMAN, ACCOUNTABILITY
 * Each entry has an icon state: check (completed) or dot (in progress)
 */

import { Check, Circle, Activity } from 'lucide-react';

const CATEGORY_COLORS = {
  OBSERVED: 'var(--lp-brand)',
  DETERMINISTIC: '#7c3aed',
  'DATA RETRIEVAL': '#7c3aed',
  'AI ANALYSIS': '#d97706',
  'AI OUTPUT': '#d97706',
  HUMAN: '#16a34a',
  ACCOUNTABILITY: '#16a34a',
};

function FeedEntry({ entry }) {
  if (!entry.visible) return null;

  const isLatest = entry.isLatest;
  const isCompleted = entry.status === 'completed';
  const color = CATEGORY_COLORS[entry.category] || '#64748b';

  return (
    <div className={`activity-feed__entry ${isLatest ? 'activity-feed__entry--current' : ''} ${isCompleted ? 'activity-feed__entry--done' : ''}`}>
      {/* Status icon */}
      <div
        className={`activity-feed__icon ${isLatest ? 'activity-feed__icon--active' : ''}`}
        style={isCompleted ? { color } : isLatest ? { color } : undefined}
      >
        {isCompleted ? (
          <Check size={12} strokeWidth={2.5} aria-hidden="true" />
        ) : isLatest ? (
          <Circle size={12} fill="currentColor" aria-hidden="true" />
        ) : (
          <Circle size={12} aria-hidden="true" />
        )}
      </div>

      {/* Category + label */}
      <span className="activity-feed__category" style={isLatest || isCompleted ? { color } : undefined}>
        {entry.category}
      </span>
      <span className="activity-feed__label">
        {entry.label}
      </span>
    </div>
  );
}

export default function InvestigationActivityFeed({ activityFeed = [] }) {
  const visibleEntries = activityFeed.filter((e) => e.visible);
  if (visibleEntries.length === 0) return null;

  return (
    <div className="activity-feed" role="region" aria-label="Investigation activity feed">
      <div className="activity-feed__header">
        <Activity size={14} aria-hidden="true" />
        <span className="activity-feed__title">Processing Activity</span>
      </div>
      <div className="activity-feed__list lp-motion-stagger-lg">
        {activityFeed.map((entry) => (
          <FeedEntry key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  );
}
