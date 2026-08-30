/**
 * HistoricalVerificationContext — Displays verification statistics as context.
 *
 * Shows aggregated verification data from past investigations.
 * Only shows percentages when minimum sample threshold (3) is met.
 *
 * Design Rules:
 * - Minimum 3 verified cases before showing percentage statistics
 * - Historical verification is context only, not a guarantee
 * - Use language: "Recommendation supported" NOT "AI was correct"
 */

import { BarChart3, Shield, Target, Lightbulb, Info } from 'lucide-react';

function StatBar({ label, value, color = '#2563eb' }) {
  return (
    <div style={styles.statBar}>
      <div style={styles.statBarHeader}>
        <span style={styles.statLabel}>{label}</span>
        <span style={{ ...styles.statValue, color }}>{value != null ? `${value}%` : '—'}</span>
      </div>
      <div style={styles.barTrack}>
        <div
          style={{
            ...styles.barFill,
            width: value != null ? `${Math.min(value, 100)}%` : '0%',
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

export default function HistoricalVerificationContext({
  stats = null,
  currentOutcome = null,
  disclaimer = '',
}) {
  if (!stats) {
    return (
      <div style={styles.card}>
        <div style={styles.header}>
          <BarChart3 size={16} color="#475569" />
          <h4 style={styles.title}>Verification Context</h4>
        </div>
        <p style={styles.noData}>No verification data available yet.</p>
      </div>
    );
  }

  const hasEnoughData = stats.total_verifications >= 3;

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <BarChart3 size={16} color="#475569" />
        <h4 style={styles.title}>Verification Context</h4>
        <span style={styles.badge}>{stats.total_verifications} verified</span>
      </div>

      {/* Status Distribution */}
      <div style={styles.distribution}>
        <div style={styles.distItem}>
          <span style={{ ...styles.distCount, color: '#16a34a' }}>{stats.useful_count}</span>
          <span style={styles.distLabel}>Useful</span>
        </div>
        <div style={styles.distItem}>
          <span style={{ ...styles.distCount, color: '#ca8a04' }}>{stats.partially_useful_count}</span>
          <span style={styles.distLabel}>Partially</span>
        </div>
        <div style={styles.distItem}>
          <span style={{ ...styles.distCount, color: '#dc2626' }}>{stats.not_supported_count}</span>
          <span style={styles.distLabel}>Not Supported</span>
        </div>
        <div style={styles.distItem}>
          <span style={{ ...styles.distCount, color: '#6b7280' }}>{stats.inconclusive_count}</span>
          <span style={styles.distLabel}>Inconclusive</span>
        </div>
      </div>

      {/* Percentage Stats (only when sufficient data) */}
      {hasEnoughData ? (
        <div style={styles.statsSection}>
          <StatBar
            label="Corridor recommendations supported"
            value={stats.recommendation_supported_pct}
            color="#2563eb"
          />
          <StatBar
            label="Investigation areas verified"
            value={stats.area_supported_pct}
            color="#059669"
          />
          <StatBar
            label="Hypotheses verified"
            value={stats.hypothesis_hit_rate}
            color="#7c3aed"
          />
        </div>
      ) : (
        <div style={styles.insufficientData}>
          <Info size={14} color="#94a3b8" />
          <span>
            At least 3 verified investigations needed for percentage statistics.
            Currently {stats.total_verifications} verified.
          </span>
        </div>
      )}

      {/* Current Outcome (if exists) */}
      {currentOutcome && (
        <div style={styles.currentOutcome}>
          <div style={styles.outcomeHeader}>
            <Shield size={14} color="#475569" />
            <span style={styles.outcomeTitle}>Current Investigation Status</span>
          </div>
          <span
            style={{
              ...styles.outcomeStatus,
              color: getStatusColor(currentOutcome.overall_status),
              borderColor: getStatusColor(currentOutcome.overall_status),
            }}
          >
            {formatStatus(currentOutcome.overall_status)}
          </span>
          {currentOutcome.field_notes && (
            <p style={styles.fieldNotes}>{currentOutcome.field_notes}</p>
          )}
        </div>
      )}

      {/* Disclaimer */}
      <div style={styles.disclaimer}>
        <Info size={12} color="#94a3b8" />
        <span>
          {disclaimer || 'Historical verification data provides context for ongoing investigations. It does not guarantee the accuracy of current AI analysis.'}
        </span>
      </div>
    </div>
  );
}

function formatStatus(status) {
  return status?.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) || '';
}

function getStatusColor(status) {
  switch (status) {
    case 'USEFUL': return '#16a34a';
    case 'PARTIALLY_USEFUL': return '#ca8a04';
    case 'NOT_SUPPORTED': return '#dc2626';
    case 'INCONCLUSIVE': return '#6b7280';
    default: return '#94a3b8';
  }
}

const styles = {
  card: {
    background: 'white',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    padding: '20px',
    marginBottom: '16px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '16px',
  },
  title: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#1e293b',
    margin: 0,
    flex: 1,
  },
  badge: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#64748b',
    background: '#f1f5f9',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  noData: {
    fontSize: '13px',
    color: '#94a3b8',
    textAlign: 'center',
    padding: '12px 0',
  },
  distribution: {
    display: 'flex',
    gap: '12px',
    marginBottom: '16px',
    paddingBottom: '16px',
    borderBottom: '1px solid #f1f5f9',
  },
  distItem: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '2px',
  },
  distCount: {
    fontSize: '20px',
    fontWeight: '700',
  },
  distLabel: {
    fontSize: '10px',
    color: '#94a3b8',
    textAlign: 'center',
    lineHeight: '1.2',
  },
  statsSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginBottom: '16px',
  },
  statBar: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  statBarHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statLabel: {
    fontSize: '12px',
    color: '#64748b',
  },
  statValue: {
    fontSize: '13px',
    fontWeight: '700',
  },
  barTrack: {
    height: '6px',
    backgroundColor: '#f1f5f9',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  },
  insufficientData: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 12px',
    backgroundColor: '#fafafa',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#64748b',
    marginBottom: '16px',
  },
  currentOutcome: {
    padding: '12px',
    backgroundColor: '#fafafa',
    borderRadius: '8px',
    marginBottom: '12px',
  },
  outcomeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '8px',
  },
  outcomeTitle: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#475569',
  },
  outcomeStatus: {
    display: 'inline-block',
    fontSize: '12px',
    fontWeight: '600',
    padding: '2px 10px',
    borderRadius: '12px',
    border: '1.5px solid',
    marginBottom: '6px',
  },
  fieldNotes: {
    fontSize: '12px',
    color: '#64748b',
    margin: '6px 0 0',
    fontStyle: 'italic',
  },
  disclaimer: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '6px',
    fontSize: '11px',
    color: '#94a3b8',
    lineHeight: '1.4',
    paddingTop: '12px',
    borderTop: '1px solid #f1f5f9',
  },
};
