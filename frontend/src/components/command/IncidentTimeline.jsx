/**
 * IncidentTimeline — Persistent incident timeline for the demo.
 *
 * Shows the chronological story of the pollution investigation.
 * Events are driven by demoStep — previously completed events remain visible.
 *
 * Categories: observed, deterministic, ai, verified, accountability
 * States: completed, current, future
 */

import { useState } from 'react';
import { Clock, Eye, Wind, Brain, ClipboardCheck, Shield, Circle, ChevronDown, ChevronRight } from 'lucide-react';

const CATEGORY_CONFIG = {
  observed: { color: 'var(--lp-brand)', icon: Eye },
  deterministic: { color: '#3b82f6', icon: Wind },
  ai: { color: '#d97706', icon: Brain },
  verified: { color: '#16a34a', icon: ClipboardCheck },
  accountability: { color: '#16a34a', icon: Shield },
};

function TimelineEvent({ event, isLast }) {
  const config = CATEGORY_CONFIG[event.category] || CATEGORY_CONFIG.observed;
  const Icon = config.icon;

  if (!event.visible) return null;

  const isCurrent = event.status === 'current';
  const isCompleted = event.status === 'completed';

  return (
    <div className={`incident-timeline__event ${isCurrent ? 'incident-timeline__event--current' : ''} ${isCompleted ? 'incident-timeline__event--completed' : ''}`}>
      {/* Connector line */}
      {!isLast && (
        <div className="incident-timeline__connector" aria-hidden="true">
          <div className={`incident-timeline__connector-line ${isCompleted ? 'incident-timeline__connector-line--done' : ''}`} />
        </div>
      )}

      {/* Event dot */}
      <div
        className={`incident-timeline__dot ${isCurrent ? 'incident-timeline__dot--current' : ''} ${isCompleted ? 'incident-timeline__dot--completed' : ''}`}
        style={isCompleted ? { background: config.color } : undefined}
      >
        {isCompleted ? (
          <span aria-hidden="true">&#10003;</span>
        ) : isCurrent ? (
          <Circle size={10} fill="currentColor" aria-hidden="true" />
        ) : (
          <span aria-hidden="true">{event.time.split(':')[0]}</span>
        )}
      </div>

      {/* Event content */}
      <div className="incident-timeline__content">
        <div className="incident-timeline__time">
          <Clock size={10} aria-hidden="true" />
          <span>{event.time}</span>
        </div>
        <div className="incident-timeline__label">{event.label}</div>
        {isCurrent && (
          <div className="incident-timeline__detail">{event.detail}</div>
        )}
      </div>
    </div>
  );
}

export default function IncidentTimeline({ timeline = [] }) {
  const [collapsed, setCollapsed] = useState(false);
  const visibleEvents = timeline.filter((e) => e.visible);
  if (visibleEvents.length === 0) return null;

  return (
    <div className={`incident-timeline ${collapsed ? 'incident-timeline--collapsed' : ''}`} role="region" aria-label="Incident timeline">
      <button
        className="incident-timeline__header incident-timeline__toggle"
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
        aria-label={collapsed ? 'Expand incident timeline' : 'Collapse incident timeline'}
      >
        <Clock size={14} aria-hidden="true" />
        <span className="incident-timeline__title">Incident Timeline</span>
        <span className="incident-timeline__toggle-icon" aria-hidden="true">
          {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        </span>
      </button>
      {!collapsed && (
        <div className="incident-timeline__events">
          {timeline.map((event, i) => {
            const nextVisible = timeline.slice(i + 1).find((e) => e.visible);
            const isLast = !nextVisible;
            return (
              <TimelineEvent key={event.id} event={event} isLast={isLast} />
            );
          })}
        </div>
      )}
    </div>
  );
}
