/**
 * InvestigationLearning — Historical investigation accountability context.
 *
 * Shows how useful past similar verified investigations were.
 * Deterministic comparison — NO machine learning.
 *
 * Design Rules:
 * - Minimum 3 verified cases before showing percentage statistics
 * - Language: "Similar previously verified investigations showed..."
 *   NOT: "The AI learned that..."
 * - Every response contains limitations
 * - Historical verification is context only, not a guarantee
 * - Never fabricates historical cases
 */

import { useState } from 'react';
import {
  BookOpen,
  Shield,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  Info,
  Clock,
} from 'lucide-react';

const EVIDENCE_COLORS = {
  INSUFFICIENT: { bg: '#fef2f2', text: '#991b1b', border: '#fecaca' },
  LIMITED: { bg: '#fffbeb', text: '#92400e', border: '#fde68a' },
  MODERATE: { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe' },
  STRONG: { bg: '#f0fdf4', text: '#166534', border: '#bbf7d0' },
};

const STATUS_ICONS = {
  USEFUL: CheckCircle,
  PARTIALLY_USEFUL: HelpCircle,
  NOT_SUPPORTED: XCircle,
  INCONCLUSIVE: HelpCircle,
};

const STATUS_COLORS = {
  USEFUL: '#16a34a',
  PARTIALLY_USEFUL: '#ca8a04',
  NOT_SUPPORTED: '#dc2626',
  INCONCLUSIVE: '#6b7280',
};

function formatStatus(status) {
  return (status || '').replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

function SimilarCaseCard({ caseData }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = STATUS_ICONS[caseData.overall_status] || HelpCircle;
  const color = STATUS_COLORS[caseData.overall_status] || '#6b7280';

  return (
    <div style={styles.caseCard} data-testid="similar-case">
      <div style={styles.caseHeader}>
        <div style={styles.caseHeaderLeft}>
          <Icon size={14} color={color} />
          <span style={styles.caseStatus} data-testid="case-status">
            {formatStatus(caseData.overall_status)}
          </span>
          <span style={styles.caseId}>{caseData.investigation_id}</span>
        </div>
        <div style={styles.caseHeaderRight}>
          <span style={styles.similarityBadge} data-testid="similarity-score">
            {(caseData.similarity_score * 100).toFixed(0)}% match
          </span>
          <span style={styles.caseDate}>{caseData.date}</span>
        </div>
      </div>

      <p style={styles.caseSummary}>{caseData.summary}</p>

      {/* Matching / Differing Dimensions */}
      <div style={styles.dimensionsRow}>
        {caseData.matching_dimensions?.length > 0 && (
          <div style={styles.dimensionGroup}>
            <span style={styles.dimensionLabel}>Matching:</span>
            {caseData.matching_dimensions.map((dim) => (
              <span key={dim} style={styles.dimensionTag}>
                {dim.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>

      {caseData.differing_dimensions?.length > 0 && (
        <div style={styles.dimensionsRow}>
          <div style={styles.dimensionGroup}>
            <span style={{ ...styles.dimensionLabel, color: '#92400e' }}>Differing:</span>
            {caseData.differing_dimensions.map((dim) => (
              <span key={dim} style={{ ...styles.dimensionTag, backgroundColor: '#fef3c7', color: '#92400e' }}>
                {dim.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Expand details */}
      <button
        style={styles.expandButton}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {expanded ? 'Less detail' : 'More detail'}
      </button>

      {expanded && (
        <div style={styles.expandedContent}>
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>Recommendation verification:</span>
            <span style={{ ...styles.detailValue, color: STATUS_COLORS[caseData.recommendation_verification] || '#6b7280' }}>
              {formatStatus(caseData.recommendation_verification)}
            </span>
          </div>
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>Outcome ID:</span>
            <span style={styles.detailValue}>{caseData.outcome_id}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function InvestigationLearning({ learning, loading, error }) {
  if (loading) {
    return (
      <div style={styles.card}>
        <div style={styles.header}>
          <BookOpen size={16} color="#475569" />
          <h4 style={styles.title}>Investigation Accountability</h4>
        </div>
        <div style={styles.loading}>Loading historical context…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.card}>
        <div style={styles.header}>
          <BookOpen size={16} color="#475569" />
          <h4 style={styles.title}>Investigation Accountability</h4>
        </div>
        <p style={styles.errorText}>
          Historical context is temporarily unavailable.
        </p>
      </div>
    );
  }

  if (!learning) {
    return (
      <div style={styles.card}>
        <div style={styles.header}>
          <BookOpen size={16} color="#475569" />
          <h4 style={styles.title}>Investigation Accountability</h4>
        </div>
        <p style={styles.noData}>No historical investigation data available yet.</p>
      </div>
    );
  }

  const {
    historical_investigations_found = 0,
    verified_outcomes = {},
    recommendation_reliability = {},
    similar_cases = [],
    limitations = [],
    evidence_status = 'INSUFFICIENT',
    historical_context_message = '',
    disclaimer = '',
  } = learning;

  const evidenceStyle = EVIDENCE_COLORS[evidence_status] || EVIDENCE_COLORS.INSUFFICIENT;
  const hasEnoughData = historical_investigations_found >= 3;
  const reliabilityScore = recommendation_reliability.score;

  return (
    <div style={styles.card} className="accountability-reveal" data-testid="investigation-learning">
      {/* Header */}
      <div style={styles.header}>
        <BookOpen size={16} color="#475569" />
        <h4 style={styles.title}>Investigation Accountability</h4>
        <span
          style={{
            ...styles.evidenceBadge,
            backgroundColor: evidenceStyle.bg,
            color: evidenceStyle.text,
            borderColor: evidenceStyle.border,
          }}
          data-testid="evidence-status"
        >
          {evidence_status}
        </span>
        <span style={styles.caseCount} data-testid="case-count">
          {historical_investigations_found} historical cases
        </span>
      </div>

      {/* Historical Context Message */}
      {historical_context_message && (
        <div style={styles.contextMessage} data-testid="context-message">
          <p style={styles.contextText}>{historical_context_message}</p>
        </div>
      )}

      {/* Reliability Score */}
      {hasEnoughData && reliabilityScore != null && (
        <div style={styles.reliabilitySection} data-testid="reliability-section">
          <div style={styles.reliabilityHeader}>
            <Shield size={14} color="#475569" />
            <span style={styles.reliabilityLabel}>Recommendation Reliability</span>
            <span
              style={{
                ...styles.reliabilityBadge,
                color: getReliabilityColor(recommendation_reliability.classification),
              }}
              data-testid="reliability-classification"
            >
              {recommendation_reliability.classification}
            </span>
          </div>

          {/* Score Bar */}
          <div style={styles.scoreBarContainer}>
            <div style={styles.scoreBarTrack}>
              <div
                style={{
                  ...styles.scoreBarFill,
                  width: `${(reliabilityScore * 100).toFixed(0)}%`,
                  backgroundColor: getReliabilityColor(recommendation_reliability.classification),
                }}
              />
            </div>
            <span style={styles.scoreText} data-testid="reliability-score">
              {(reliabilityScore * 100).toFixed(0)}%
            </span>
          </div>

          <p style={styles.reliabilityDescription}>{recommendation_reliability.description}</p>

          {/* Breakdown */}
          <div style={styles.breakdown}>
            <div style={styles.breakdownItem}>
              <CheckCircle size={12} color="#16a34a" />
              <span style={styles.breakdownLabel}>Useful</span>
              <span style={{ ...styles.breakdownCount, color: '#16a34a' }}>
                {recommendation_reliability.useful_count}
              </span>
            </div>
            <div style={styles.breakdownItem}>
              <HelpCircle size={12} color="#ca8a04" />
              <span style={styles.breakdownLabel}>Partially</span>
              <span style={{ ...styles.breakdownCount, color: '#ca8a04' }}>
                {recommendation_reliability.partially_useful_count}
              </span>
            </div>
            <div style={styles.breakdownItem}>
              <XCircle size={12} color="#dc2626" />
              <span style={styles.breakdownLabel}>Not Supported</span>
              <span style={{ ...styles.breakdownCount, color: '#dc2626' }}>
                {recommendation_reliability.not_supported_count}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Insufficient Data Warning */}
      {!hasEnoughData && historical_investigations_found > 0 && (
        <div style={styles.insufficientData}>
          <AlertTriangle size={14} color="#92400e" />
          <span>
            At least 3 verified investigations needed for reliability statistics.
            Currently {historical_investigations_found} found.
          </span>
        </div>
      )}

      {/* Similar Cases */}
      {similar_cases.length > 0 && (
        <div style={styles.casesSection}>
          <h5 style={styles.casesTitle}>Similar Verified Investigations</h5>
          {similar_cases.map((c) => (
            <SimilarCaseCard key={c.investigation_id} caseData={c} />
          ))}
        </div>
      )}

      {/* Limitations */}
      {limitations.length > 0 && (
        <div style={styles.limitationsSection} data-testid="limitations">
          <div style={styles.limitationsHeader}>
            <AlertTriangle size={13} color="#92400e" />
            <span style={styles.limitationsTitle}>Limitations</span>
          </div>
          <ul style={styles.limitationsList}>
            {limitations.map((lim, i) => (
              <li key={i} style={styles.limitationItem}>
                {lim}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div style={styles.disclaimer} data-testid="disclaimer">
        <Info size={12} color="#94a3b8" />
        <span>{disclaimer}</span>
      </div>
    </div>
  );
}

function getReliabilityColor(classification) {
  switch (classification) {
    case 'STRONG': return '#16a34a';
    case 'MODERATE': return '#2563eb';
    case 'LIMITED': return '#ca8a04';
    case 'INSUFFICIENT': return '#dc2626';
    default: return '#6b7280';
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
    flexWrap: 'wrap',
  },
  title: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#1e293b',
    margin: 0,
    flex: 1,
  },
  evidenceBadge: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 10px',
    borderRadius: '10px',
    border: '1.5px solid',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  caseCount: {
    fontSize: '11px',
    color: '#64748b',
    background: '#f1f5f9',
    padding: '2px 8px',
    borderRadius: '10px',
  },
  loading: {
    fontSize: '13px',
    color: '#94a3b8',
    textAlign: 'center',
    padding: '12px 0',
  },
  errorText: {
    fontSize: '13px',
    color: '#dc2626',
    textAlign: 'center',
    padding: '12px 0',
  },
  noData: {
    fontSize: '13px',
    color: '#94a3b8',
    textAlign: 'center',
    padding: '12px 0',
  },
  contextMessage: {
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    padding: '12px 14px',
    marginBottom: '16px',
    border: '1px solid #e2e8f0',
  },
  contextText: {
    fontSize: '13px',
    color: '#334155',
    lineHeight: '1.5',
    margin: 0,
  },
  reliabilitySection: {
    marginBottom: '16px',
  },
  reliabilityHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '8px',
  },
  reliabilityLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#475569',
    flex: 1,
  },
  reliabilityBadge: {
    fontSize: '11px',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  scoreBarContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '8px',
  },
  scoreBarTrack: {
    flex: 1,
    height: '8px',
    backgroundColor: '#f1f5f9',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.3s ease',
  },
  scoreText: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#1e293b',
    minWidth: '40px',
    textAlign: 'right',
  },
  reliabilityDescription: {
    fontSize: '12px',
    color: '#64748b',
    lineHeight: '1.5',
    margin: '0 0 10px 0',
  },
  breakdown: {
    display: 'flex',
    gap: '16px',
  },
  breakdownItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  breakdownLabel: {
    fontSize: '11px',
    color: '#64748b',
  },
  breakdownCount: {
    fontSize: '13px',
    fontWeight: '700',
  },
  insufficientData: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 12px',
    backgroundColor: '#fffbeb',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#92400e',
    marginBottom: '16px',
  },
  casesSection: {
    marginBottom: '16px',
  },
  casesTitle: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: '10px',
  },
  caseCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '8px',
    backgroundColor: '#fafafa',
  },
  caseHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
    flexWrap: 'wrap',
    gap: '4px',
  },
  caseHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  caseHeaderRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  caseStatus: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#475569',
  },
  caseId: {
    fontSize: '11px',
    color: '#94a3b8',
  },
  similarityBadge: {
    fontSize: '10px',
    fontWeight: '600',
    color: '#2563eb',
    backgroundColor: '#eff6ff',
    padding: '1px 6px',
    borderRadius: '8px',
  },
  caseDate: {
    fontSize: '10px',
    color: '#94a3b8',
  },
  caseSummary: {
    fontSize: '12px',
    color: '#475569',
    lineHeight: '1.4',
    margin: '0 0 8px 0',
  },
  dimensionsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginBottom: '4px',
  },
  dimensionGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    flexWrap: 'wrap',
  },
  dimensionLabel: {
    fontSize: '10px',
    fontWeight: '600',
    color: '#16a34a',
  },
  dimensionTag: {
    fontSize: '10px',
    backgroundColor: '#dcfce7',
    color: '#166534',
    padding: '1px 6px',
    borderRadius: '6px',
    textTransform: 'capitalize',
  },
  expandButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    color: '#64748b',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '4px 0',
    marginTop: '4px',
  },
  expandedContent: {
    marginTop: '8px',
    paddingTop: '8px',
    borderTop: '1px solid #e2e8f0',
  },
  detailRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '4px',
  },
  detailLabel: {
    fontSize: '11px',
    color: '#64748b',
  },
  detailValue: {
    fontSize: '11px',
    fontWeight: '500',
    color: '#1e293b',
    textTransform: 'capitalize',
  },
  limitationsSection: {
    backgroundColor: '#fffbeb',
    borderRadius: '8px',
    padding: '12px 14px',
    marginBottom: '12px',
    border: '1px solid #fde68a',
  },
  limitationsHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '8px',
  },
  limitationsTitle: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#92400e',
  },
  limitationsList: {
    margin: 0,
    paddingLeft: '16px',
    listStyle: 'disc',
  },
  limitationItem: {
    fontSize: '11px',
    color: '#78716c',
    lineHeight: '1.4',
    marginBottom: '4px',
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
