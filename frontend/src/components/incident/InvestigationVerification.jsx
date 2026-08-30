/**
 * InvestigationVerification — Human verification form for AI investigation results.
 *
 * Allows response officers to submit feedback on AI investigation quality.
 * Part of the transparent feedback loop (Phase 5 — Learning Loop).
 *
 * Design Rules:
 * - NEVER modify original AI analysis when storing verification
 * - Use language: "Recommendation supported" NOT "AI was correct"
 * - Historical verification is context only, not a guarantee
 */

import { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Send,
  FileText,
  Users,
  MapPin,
  Lightbulb,
} from 'lucide-react';

const STATUS_OPTIONS = [
  { value: 'USEFUL', label: 'Useful', icon: CheckCircle2, color: '#16a34a', description: 'Investigation provided actionable intelligence' },
  { value: 'PARTIALLY_USEFUL', label: 'Partially Useful', icon: AlertTriangle, color: '#ca8a04', description: 'Some recommendations were useful, others not' },
  { value: 'NOT_SUPPORTED', label: 'Not Supported', icon: XCircle, color: '#dc2626', description: 'Field findings did not support the analysis' },
  { value: 'INCONCLUSIVE', label: 'Inconclusive', icon: HelpCircle, color: '#6b7280', description: 'Unable to determine usefulness' },
];

const AREA_VERIFICATION_OPTIONS = [
  { value: 'SUPPORTED', label: 'Supported', color: '#16a34a' },
  { value: 'PARTIALLY_SUPPORTED', label: 'Partially Supported', color: '#ca8a04' },
  { value: 'NOT_SUPPORTED', label: 'Not Supported', color: '#dc2626' },
  { value: 'UNKNOWN', label: 'Unknown', color: '#6b7280' },
];

export default function InvestigationVerification({
  investigationId = 'current-investigation',
  hypotheses = [],
  onSubmit,
  onUpdate,
  existingOutcome = null,
  loading = false,
  submitting = false,
}) {
  const [overallStatus, setOverallStatus] = useState(existingOutcome?.overall_status || '');
  const [areaVerification, setAreaVerification] = useState(existingOutcome?.investigation_area_verification || 'UNKNOWN');
  const [recommendationVerification, setRecommendationVerification] = useState(existingOutcome?.recommendation_verification || 'UNKNOWN');
  const [hypothesisResults, setHypothesisResults] = useState(() => {
    if (existingOutcome?.hypothesis_verifications?.length) {
      return existingOutcome.hypothesis_verifications;
    }
    return hypotheses.map(h => ({ factor: h.factor, verified: false, notes: '' }));
  });
  const [fieldNotes, setFieldNotes] = useState(existingOutcome?.field_notes || '');
  const [verifiedBy, setVerifiedBy] = useState(existingOutcome?.verified_by || '');
  const [showSuccess, setShowSuccess] = useState(false);

  const handleHypothesisToggle = (index) => {
    setHypothesisResults(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], verified: !updated[index].verified };
      return updated;
    });
  };

  const handleHypothesisNotes = (index, notes) => {
    setHypothesisResults(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], notes };
      return updated;
    });
  };

  const handleSubmit = async () => {
    if (!overallStatus) return;

    const data = {
      investigation_id: investigationId,
      overall_status: overallStatus,
      recommendation_verification: recommendationVerification,
      investigation_area_verification: areaVerification,
      hypothesis_verifications: hypothesisResults,
      field_notes: fieldNotes,
      verified_by: verifiedBy,
    };

    let result;
    if (existingOutcome?.outcome_id) {
      result = await onUpdate?.(existingOutcome.outcome_id, data);
    } else {
      result = await onSubmit?.(data);
    }

    if (result) {
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 4000);
    }
  };

  if (loading) {
    return (
      <div style={styles.card}>
        <div style={styles.loading}>Loading verification data…</div>
      </div>
    );
  }

  if (showSuccess) {
    return (
      <div style={{ ...styles.card, ...styles.successCard }} className="lp-motion-scale-in">
        <CheckCircle2 size={24} color="#16a34a" />
        <div style={styles.successText}>
          <strong>Verification submitted</strong>
          <span style={styles.successSub}>Your feedback helps improve future investigations.</span>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <FileText size={18} color="#475569" />
        <h3 style={styles.title}>Investigation Verification</h3>
      </div>

      <p style={styles.description}>
        Your verification provides transparent feedback on the investigation quality.
        This does <em>not</em> modify the original AI analysis — it is stored separately.
      </p>

      {/* Overall Status */}
      <div style={styles.section}>
        <label style={styles.sectionLabel}>Overall Assessment</label>
        <div style={styles.statusGrid}>
          {STATUS_OPTIONS.map(opt => {
            const Icon = opt.icon;
            const isSelected = overallStatus === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => setOverallStatus(opt.value)}
                style={{
                  ...styles.statusBtn,
                  borderColor: isSelected ? opt.color : '#e2e8f0',
                  backgroundColor: isSelected ? `${opt.color}11` : 'white',
                  color: isSelected ? opt.color : '#475569',
                }}
              >
                <Icon size={16} />
                <span style={styles.statusLabel}>{opt.label}</span>
                <span style={styles.statusDesc}>{opt.description}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Recommendation Verification */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <MapPin size={16} color="#475569" />
          <label style={styles.sectionLabel}>Investigation Corridor Verification</label>
        </div>
        <p style={styles.sectionHint}>Was the recommended investigation corridor supported by field findings?</p>
        <div style={styles.optionRow}>
          {AREA_VERIFICATION_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setRecommendationVerification(opt.value)}
              style={{
                ...styles.optionBtn,
                borderColor: recommendationVerification === opt.value ? opt.color : '#e2e8f0',
                backgroundColor: recommendationVerification === opt.value ? `${opt.color}11` : 'white',
                color: recommendationVerification === opt.value ? opt.color : '#475569',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Investigation Area Verification */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <MapPin size={16} color="#475569" />
          <label style={styles.sectionLabel}>Investigation Area Verification</label>
        </div>
        <p style={styles.sectionHint}>Was the upwind investigation area verified in the field?</p>
        <div style={styles.optionRow}>
          {AREA_VERIFICATION_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setAreaVerification(opt.value)}
              style={{
                ...styles.optionBtn,
                borderColor: areaVerification === opt.value ? opt.color : '#e2e8f0',
                backgroundColor: areaVerification === opt.value ? `${opt.color}11` : 'white',
                color: areaVerification === opt.value ? opt.color : '#475569',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Hypothesis Verifications */}
      {hypothesisResults.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <Lightbulb size={16} color="#475569" />
            <label style={styles.sectionLabel}>Hypothesis Verification</label>
          </div>
          {hypothesisResults.map((hyp, idx) => (
            <div key={idx} style={styles.hypothesisCard}>
              <div style={styles.hypothesisHeader}>
                <button
                  onClick={() => handleHypothesisToggle(idx)}
                  style={{
                    ...styles.verifyBtn,
                    backgroundColor: hyp.verified ? '#dcfce7' : '#f1f5f9',
                    borderColor: hyp.verified ? '#16a34a' : '#e2e8f0',
                  }}
                >
                  {hyp.verified ? '✓ Verified' : 'Verify'}
                </button>
                <span style={styles.hypothesisFactor}>{hyp.factor}</span>
              </div>
              <textarea
                value={hyp.notes}
                onChange={(e) => handleHypothesisNotes(idx, e.target.value)}
                placeholder="Optional notes for this hypothesis…"
                style={styles.textarea}
                rows={2}
              />
            </div>
          ))}
        </div>
      )}

      {/* Field Notes */}
      <div style={styles.section}>
        <label style={styles.sectionLabel}>Field Notes</label>
        <textarea
          value={fieldNotes}
          onChange={(e) => setFieldNotes(e.target.value)}
          placeholder="Describe what was found during the field investigation…"
          style={styles.textarea}
          rows={4}
        />
      </div>

      {/* Verified By */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <Users size={16} color="#475569" />
          <label style={styles.sectionLabel}>Verified By</label>
        </div>
        <input
          value={verifiedBy}
          onChange={(e) => setVerifiedBy(e.target.value)}
          placeholder="Name or role of verifier"
          style={styles.input}
        />
      </div>

      {/* Submit */}
      <div style={styles.footer}>
        <button
          onClick={handleSubmit}
          disabled={!overallStatus || submitting}
          style={{
            ...styles.submitBtn,
            opacity: (!overallStatus || submitting) ? 0.5 : 1,
          }}
        >
          <Send size={16} />
          {submitting ? 'Submitting…' : existingOutcome ? 'Update Verification' : 'Submit Verification'}
        </button>
      </div>
    </div>
  );
}

const styles = {
  card: {
    background: 'white',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    padding: '24px',
    marginBottom: '16px',
  },
  successCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    background: '#f0fdf4',
    borderColor: '#bbf7d0',
  },
  successText: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  successSub: {
    fontSize: '13px',
    color: '#166534',
  },
  loading: {
    color: '#94a3b8',
    textAlign: 'center',
    padding: '20px',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
  },
  title: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1e293b',
    margin: 0,
  },
  description: {
    fontSize: '13px',
    color: '#64748b',
    marginBottom: '20px',
    lineHeight: '1.5',
  },
  section: {
    marginBottom: '20px',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '6px',
  },
  sectionLabel: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#334155',
    display: 'block',
    marginBottom: '4px',
  },
  sectionHint: {
    fontSize: '12px',
    color: '#94a3b8',
    marginBottom: '8px',
  },
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
  },
  statusBtn: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '4px',
    padding: '12px',
    borderRadius: '8px',
    border: '2px solid #e2e8f0',
    background: 'white',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    textAlign: 'left',
  },
  statusLabel: {
    fontSize: '13px',
    fontWeight: '600',
  },
  statusDesc: {
    fontSize: '11px',
    opacity: 0.7,
  },
  optionRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  optionBtn: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1.5px solid #e2e8f0',
    background: 'white',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '500',
    transition: 'all 0.15s ease',
  },
  hypothesisCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '8px',
    background: '#fafafa',
  },
  hypothesisHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
  },
  verifyBtn: {
    padding: '4px 10px',
    borderRadius: '6px',
    border: '1.5px solid',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '500',
    whiteSpace: 'nowrap',
  },
  hypothesisFactor: {
    fontSize: '13px',
    color: '#334155',
    fontWeight: '500',
  },
  textarea: {
    width: '100%',
    padding: '8px 10px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    fontSize: '13px',
    fontFamily: 'inherit',
    resize: 'vertical',
    color: '#334155',
    lineHeight: '1.4',
  },
  input: {
    width: '100%',
    padding: '8px 10px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    fontSize: '13px',
    fontFamily: 'inherit',
    color: '#334155',
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    paddingTop: '12px',
    borderTop: '1px solid #f1f5f9',
  },
  submitBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: '#2563eb',
    color: 'white',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
};
