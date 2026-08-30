/**
 * IncidentTimeline — Visual timeline of incident lifecycle events.
 *
 * Shows chronological events with stage transitions, notes, and actions.
 * Uses the same timeline CSS classes established for PollutionStory.
 */

import {
  Circle,
  Play,
  CheckCircle,
  CircleDot,
  Square,
  FileText,
  Activity,
  Clock,
} from 'lucide-react';
import { INCIDENT_STAGES } from '../../lib/incidentStore';

const EVENT_ICONS = {
  detected: Circle,
  investigating: Play,
  responding: Activity,
  monitoring: CircleDot,
  resolved: CheckCircle,
  note: FileText,
  action: Square,
  data_update: Activity,
};

const EVENT_COLORS = {
  detected: '#dc2626',
  investigating: '#ea580c',
  responding: '#a16207',
  monitoring: '#2563eb',
  resolved: '#16a34a',
  note: '#64748b',
  action: '#7c3aed',
  data_update: '#0891b2',
};

function formatTimestamp(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/**
 * @param {object} props
 * @param {Array} props.events - Array of timeline events
 * @param {string} props.currentStage - Current incident stage
 */
export default function IncidentTimeline({ events = [], currentStage }) {
  if (!events.length) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--sp-6)', color: 'var(--lp-text-muted)' }}>
        <Clock size={20} style={{ marginBottom: 'var(--sp-2)', opacity: 0.5 }} />
        <div style={{ fontSize: 'var(--text-sm)' }}>No events recorded yet.</div>
      </div>
    );
  }

  // Sort events chronologically (newest first)
  const sorted = [...events].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  return (
    <div className="story-timeline" style={{ maxWidth: '100%' }}>
      {sorted.map((event, i) => {
        const Icon = EVENT_ICONS[event.event] || Circle;
        const color = EVENT_COLORS[event.event] || '#64748b';
        const isLatest = i === 0;
        const stageConfig = INCIDENT_STAGES.find(s => s.id === event.event);
        const isStageTransition = Boolean(stageConfig);

        return (
          <div
            key={`${event.event}-${event.timestamp}-${i}`}
            className={`story-timeline__item ${isLatest ? 'story-timeline__item--now' : ''}`}
          >
            <div className="story-timeline__connector">
              <div
                className="story-timeline__dot"
                style={{
                  backgroundColor: color,
                  width: isStageTransition ? 14 : 10,
                  height: isStageTransition ? 14 : 10,
                  boxShadow: isLatest ? `0 0 0 3px ${color}20` : 'none',
                }}
              >
                <Icon size={isStageTransition ? 8 : 6} color="white" style={{ display: 'block', margin: 'auto' }} />
              </div>
              {i < sorted.length - 1 && <div className="story-timeline__line" />}
            </div>
            <div className="story-timeline__content">
              <div className="story-timeline__header">
                <span
                  className="story-timeline__label"
                  style={{ color, fontWeight: isStageTransition ? 600 : 500 }}
                >
                  {stageConfig ? stageConfig.label : event.event.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </span>
                <span className="story-timeline__detail" style={{ fontSize: '0.6875rem' }}>
                  {event.actor} · {formatTimestamp(event.timestamp)}
                </span>
              </div>
              {event.detail && (
                <div className="story-timeline__detail">
                  {event.detail}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
