/**
 * AuditTrail — Compact 8-event timeline with progressive stagger.
 * Shows the full lifecycle of a prediction: data → evidence → AI → alert → verification → receipt.
 *
 * Phase 29 — Government Trust & Decision Intelligence Layer.
 * Clearly labeled as a decision-support prototype.
 */

import { useState, useEffect } from 'react';
import {
  Database,
  Layers,
  Brain,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  UserCheck,
  FileText,
} from 'lucide-react';
import { useDemoData } from '../../demo/index';

const ICON_MAP = {
  database: Database,
  layers: Layers,
  brain: Brain,
  'trending-up': TrendingUp,
  'alert-triangle': AlertTriangle,
  'check-circle': CheckCircle,
  'user-check': UserCheck,
  'file-text': FileText,
};

function formatTimestamp(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function AuditEvent({ event, index }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (event.status !== 'future') {
      const timer = setTimeout(() => setVisible(true), index * 80);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [event.status, index]);

  const Icon = ICON_MAP[event.icon] || Database;

  return (
    <div
      className={`audit-trail__event audit-trail__event--${event.status}`}
      style={{ animationDelay: `${index * 80}ms` }}
      data-testid="audit-event"
    >
      <div className="audit-trail__dot" aria-hidden="true" />
      <div className="audit-trail__body">
        <div className="audit-trail__action">{event.action}</div>
        <div className="audit-trail__detail">{event.detail}</div>
        <div className="audit-trail__meta">
          <span className="audit-trail__time">{formatTimestamp(event.timestamp)}</span>
          <span
            className={`audit-trail__actor ${
              event.actor === 'AI'
                ? 'audit-trail__actor--ai'
                : event.actor === 'Officer'
                  ? 'audit-trail__actor--officer'
                  : ''
            }`}
          >
            {event.actor}
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * AuditTrail — compact timeline of audit events.
 * Uses demo data when no explicit events prop is provided.
 */
export default function AuditTrail({ events: eventsProp }) {
  const demoData = useDemoData();
  const events = eventsProp || demoData?.auditTrail || [];

  if (!events.length) return null;

  const visibleEvents = events.filter((e) => e.status !== 'future');

  return (
    <div
      style={{
        marginTop: 16,
        padding: 16,
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: 8,
      }}
      role="region"
      aria-label="Audit trail"
      data-testid="audit-trail"
    >
      <div
        style={{
          fontSize: '0.8125rem',
          fontWeight: 600,
          color: '#0f172a',
          marginBottom: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <FileText size={14} color="#64748b" />
        Audit Trail
      </div>
      <div className="audit-trail" role="list">
        <div className="audit-trail__connector" aria-hidden="true" />
        {visibleEvents.map((event, i) => (
          <AuditEvent key={event.id} event={event} index={i} />
        ))}
      </div>
      <div
        style={{
          fontSize: '0.6875rem',
          color: '#94a3b8',
          marginTop: 8,
          fontStyle: 'italic',
        }}
      >
        Every step is timestamped and attributed. Record cannot be edited after finalization.
      </div>
    </div>
  );
}
