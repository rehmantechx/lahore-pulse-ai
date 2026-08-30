/**
 * IncidentCard — Individual incident display with lifecycle progress.
 *
 * Shows severity badge, PM2.5 reading, area, stage progress bar,
 * and quick actions (advance stage, add note).
 */

import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Clock,
  MapPin,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
  MessageSquare,
} from 'lucide-react';
import { INCIDENT_STAGES, SEVERITY_CONFIG, advanceStage, addIncidentNote } from '../../lib/incidentStore';
import IncidentTimeline from './IncidentTimeline';

const TRAJECTORY_ICONS = {
  worsening: { Icon: TrendingUp, color: '#dc2626', label: 'Rising' },
  improving: { Icon: TrendingDown, color: '#16a34a', label: 'Falling' },
  stable:    { Icon: Minus, color: '#64748b', label: 'Stable' },
};

function formatTimeAgo(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${diffDay}d ago`;
}

/**
 * @param {object} props
 * @param {object} props.incident - Incident data object
 * @param {Function} props.onUpdate - Called after incident is updated
 * @param {boolean} props.expanded - Whether detail panel is open
 */
export default function IncidentCard({ incident, onUpdate, expanded = false }) {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const [noteText, setNoteText] = useState('');
  const [showNoteInput, setShowNoteInput] = useState(false);

  const severityCfg = SEVERITY_CONFIG[incident.severity] || SEVERITY_CONFIG.unknown;
  const currentStageIdx = INCIDENT_STAGES.findIndex(s => s.id === incident.stage);
  const currentStage = INCIDENT_STAGES[currentStageIdx];
  const isResolved = incident.stage === 'resolved';
  const canAdvance = currentStageIdx < INCIDENT_STAGES.length - 1;
  const nextStage = canAdvance ? INCIDENT_STAGES[currentStageIdx + 1] : null;

  const trajectory = TRAJECTORY_ICONS[incident.trajectory] || TRAJECTORY_ICONS.stable;
  const TrajectoryIcon = trajectory.Icon;

  const handleAdvance = () => {
    if (!canAdvance) return;
    const updated = advanceStage(incident.id, {
      note: `Stage advanced to ${nextStage.label} by officer.`,
    });
    if (updated && onUpdate) onUpdate();
  };

  const handleAddNote = () => {
    if (!noteText.trim()) return;
    addIncidentNote(incident.id, { note: noteText.trim() });
    setNoteText('');
    setShowNoteInput(false);
    if (onUpdate) onUpdate();
  };

  // Stage progress bar width
  const progressPct = ((currentStageIdx + 1) / INCIDENT_STAGES.length) * 100;

  return (
    <div
      className="card card--elevated"
      style={{
        border: `1px solid ${isResolved ? 'var(--lp-border-subtle)' : severityCfg.border}`,
        transition: 'border-color 150ms, box-shadow 150ms',
        opacity: isResolved ? 0.75 : 1,
      }}
    >
      {/* Card header — always visible */}
      <div
        style={{
          padding: 'var(--sp-4)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--sp-3)',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        aria-expanded={isExpanded}
        tabIndex={0}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsExpanded(!isExpanded); } }}
      >
        {/* Severity indicator dot */}
        <div style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          backgroundColor: severityCfg.color,
          flexShrink: 0,
          marginTop: 5,
        }} />

        {/* Main info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--lp-text-primary)' }}>
              {incident.title}
            </span>
            <span style={{
              fontSize: '0.625rem',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 'var(--lp-radius-sm)',
              background: severityCfg.bg,
              color: severityCfg.color,
              border: `1px solid ${severityCfg.border}`,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              {severityCfg.label}
            </span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-3)',
            marginTop: 'var(--sp-1)',
            fontSize: '0.75rem',
            color: 'var(--lp-text-muted)',
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <MapPin size={11} />
              {incident.area}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <Clock size={11} />
              {formatTimeAgo(incident.createdAt)}
            </span>
            {incident.pm25 != null && (
              <span style={{ fontWeight: 600, color: severityCfg.color }}>
                {incident.pm25.toFixed(1)} μg/m³
              </span>
            )}
            <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: trajectory.color }}>
              <TrajectoryIcon size={11} />
              {trajectory.label}
            </span>
          </div>

          {/* Stage progress bar */}
          <div style={{
            marginTop: 'var(--sp-2)',
            height: 4,
            background: 'var(--slate-100)',
            borderRadius: 2,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${progressPct}%`,
              background: currentStage?.color || '#64748b',
              borderRadius: 2,
              transition: 'width 300ms ease',
            }} />
          </div>

          {/* Stage labels */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: 3,
            fontSize: '0.5625rem',
            color: 'var(--lp-text-muted)',
          }}>
            {INCIDENT_STAGES.map((s, i) => (
              <span
                key={s.id}
                style={{
                  color: i <= currentStageIdx ? s.color : undefined,
                  fontWeight: i === currentStageIdx ? 600 : 400,
                }}
              >
                {s.label}
              </span>
            ))}
          </div>
        </div>

        {/* Expand arrow */}
        <div style={{ flexShrink: 0, marginTop: 4, color: 'var(--lp-text-muted)' }}>
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </div>

      {/* Expanded detail panel */}
      {isExpanded && (
        <div style={{
          padding: '0 var(--sp-4) var(--sp-4)',
          borderTop: '1px solid var(--lp-border-subtle)',
        }}>
          {/* Narrative */}
          {incident.narrative && (
            <div style={{
              marginTop: 'var(--sp-3)',
              padding: 'var(--sp-3)',
              background: 'var(--slate-50)',
              borderRadius: 'var(--lp-radius-md)',
              fontSize: 'var(--text-sm)',
              color: 'var(--lp-text-secondary)',
              lineHeight: 1.6,
            }}>
              {incident.narrative}
            </div>
          )}

          {/* Timeline */}
          <div style={{ marginTop: 'var(--sp-4)' }}>
            <h4 style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: 'var(--lp-text-primary)',
              marginBottom: 'var(--sp-3)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              Timeline
            </h4>
            <IncidentTimeline events={incident.timeline} currentStage={incident.stage} />
          </div>

          {/* Actions and notes */}
          <div style={{ marginTop: 'var(--sp-4)', display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
            {canAdvance && (
              <button
                className="btn btn--primary btn--sm"
                onClick={handleAdvance}
                style={{ display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <ArrowRight size={14} />
                Advance to {nextStage.label}
              </button>
            )}
            <button
              className="btn btn--outline btn--sm"
              onClick={() => setShowNoteInput(!showNoteInput)}
              style={{ display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <MessageSquare size={14} />
              Add Note
            </button>
          </div>

          {/* Note input */}
          {showNoteInput && (
            <div style={{ marginTop: 'var(--sp-3)', display: 'flex', gap: 'var(--sp-2)' }}>
              <input
                type="text"
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                placeholder="Enter observation or note..."
                className="input"
                style={{ flex: 1 }}
                onKeyDown={e => { if (e.key === 'Enter') handleAddNote(); }}
                autoFocus
              />
              <button className="btn btn--primary btn--sm" onClick={handleAddNote} disabled={!noteText.trim()}>
                Save
              </button>
            </div>
          )}

          {/* Existing notes */}
          {incident.notes?.length > 0 && (
            <div style={{ marginTop: 'var(--sp-3)' }}>
              <h5 style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--lp-text-muted)', marginBottom: 'var(--sp-2)' }}>
                Notes ({incident.notes.length})
              </h5>
              {incident.notes.map((n, i) => (
                <div
                  key={i}
                  style={{
                    padding: 'var(--sp-2)',
                    background: 'var(--slate-50)',
                    borderRadius: 'var(--lp-radius-sm)',
                    fontSize: '0.75rem',
                    color: 'var(--lp-text-secondary)',
                    marginBottom: 'var(--sp-1)',
                    borderLeft: '2px solid var(--lp-border-subtle)',
                  }}
                >
                  <span>{n.text}</span>
                  <span style={{ marginLeft: 'var(--sp-2)', color: 'var(--lp-text-muted)', fontSize: '0.625rem' }}>
                    {formatTimeAgo(n.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
