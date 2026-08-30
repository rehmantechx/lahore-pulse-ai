/**
 * ExecutiveDecisionSummary — Phase 12: Decision-Maker Interface.
 *
 * Compact card at top of Command Center answering 5 questions in <10 seconds:
 *   1. What happened?
 *   2. What does the system think?
 *   3. What should a human do next?
 *   4. What evidence supports that?
 *   5. What is the human verification status?
 *
 * Adapts to all 6 demo steps:
 *   Step 1 → Normal monitoring (green, calm)
 *   Step 2 → Anomaly detected (red, no AI analysis yet)
 *   Step 3 → Investigation active (amber, hypothesis shown)
 *   Step 4 → Exposure analysis added (amber, corridor signal)
 *   Step 5 → Verification complete (green/red based on outcome)
 *   Step 6 → Accountability visible (green, historical reliability)
 *
 * Design rules:
 * - Does NOT duplicate detailed sections below
 * - Uses only existing data — no new data models
 * - Compact: fits in one viewport-height card
 * - Follows --lp-* design tokens
 */

import {
  CheckCircle,
  AlertTriangle,
  Clock,
  Shield,
  ChevronRight,
  Brain,
  MapPin,
  User,
  Info,
} from 'lucide-react';

/* ── Helpers ────────────────────────────────────────────── */

function formatPM25(pm25) {
  if (pm25 == null) return '—';
  return `${Math.round(pm25)} μg/m³`;
}

function formatVerificationStatus(outcome) {
  if (!outcome) return null;
  const map = {
    USEFUL: { label: 'Recommendation useful', color: '#16a34a', icon: CheckCircle },
    PARTIALLY_USEFUL: { label: 'Partially useful', color: '#ca8a04', icon: AlertTriangle },
    NOT_SUPPORTED: { label: 'Not supported by field findings', color: '#dc2626', icon: AlertTriangle },
    INCONCLUSIVE: { label: 'Inconclusive', color: '#6b7280', icon: Info },
  };
  return map[outcome] || null;
}

/* ── Component ──────────────────────────────────────────── */

export default function ExecutiveDecisionSummary({
  demoStep,
  episode,
  investigationAnalysis,
  verificationContext,
  exposureGeometry,
}) {
  if (!demoStep || demoStep < 1) return null;

  const pm25 = episode?.current_pm25;
  const trajectory = episode?.trajectory || 'stable';
  const episodeState = (episode?.state || 'normal').toLowerCase();

  const hasAnalysis = Boolean(investigationAnalysis?.analysis_status === 'complete');
  const topHypothesis = investigationAnalysis?.investigation_hypotheses?.[0];
  const topAction = investigationAnalysis?.recommended_actions?.[0];
  const outcome = verificationContext?.current_outcome;
  const verification = outcome ? formatVerificationStatus(outcome.overall_status) : null;

  const corridorLabel = investigationAnalysis?.investigation_priority?.area;
  const vulnerableCount = (exposureGeometry?.vulnerable_locations?.schools?.length || 0)
    + (exposureGeometry?.vulnerable_locations?.hospitals?.length || 0);

  /* ── Status configuration per step ─────────────────── */
  function getStatus() {
    if (demoStep === 1) {
      return { label: 'NOMINAL', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' };
    }
    if (demoStep === 5 && outcome) {
      if (outcome.overall_status === 'USEFUL') {
        return { label: 'VERIFIED', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' };
      }
      if (outcome.overall_status === 'NOT_SUPPORTED') {
        return { label: 'CONCERN', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' };
      }
      return { label: 'VERIFIED', color: '#ca8a04', bg: '#fffbeb', border: '#fde68a' };
    }
    if (demoStep >= 6) {
      return { label: 'ACCOUNTABILITY', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' };
    }
    if (demoStep >= 3) {
      return { label: 'INVESTIGATION', color: '#d97706', bg: '#fffbeb', border: '#fde68a' };
    }
    return { label: 'EPISODE ACTIVE', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' };
  }

  /* ── What happened text ────────────────────────────── */
  function getWhatHappened() {
    if (demoStep === 1) {
      return 'No abnormal pollution event detected. PM2.5 within seasonal norms.';
    }
    if (demoStep === 2) {
      return `PM2.5 rising sharply to ${formatPM25(pm25)}. Abnormal episode detected.`;
    }
    // Steps 3-6
    const windDir = episode?.source_compass?.current_wind?.sector;
    return `Active pollution episode. ${formatPM25(pm25)} from ${windDir || 'unknown'} sector.`;
  }

  /* ── System assessment ─────────────────────────────── */
  function getSystemAssessment() {
    if (demoStep === 1) {
      return { text: 'No investigation active', verified: false, icon: Info };
    }
    if (demoStep === 2) {
      return { text: 'Evidence assembly in progress', verified: false, icon: Clock };
    }
    if (demoStep >= 5 && outcome) {
      return {
        text: `Human verification: ${outcome.overall_status?.replace(/_/g, ' ')}`,
        verified: true,
        icon: CheckCircle,
      };
    }
    if (demoStep >= 6) {
      const score = investigationAnalysis ? '79%' : '—';
      return { text: `Historical reliability: ${score} for similar conditions`, verified: false, icon: Shield };
    }
    if (hasAnalysis && topHypothesis) {
      return { text: topHypothesis.factor, verified: false, icon: Brain };
    }
    return { text: 'Analysis in progress…', verified: false, icon: Clock };
  }

  /* ── Recommended human action ──────────────────────── */
  function getRecommendedAction() {
    if (demoStep === 1) return 'Continue monitoring current conditions.';
    if (demoStep === 2) return 'Awaiting AI investigation to complete.';
    // Step 6+: Accountability language
    if (demoStep >= 6) {
      return 'Outcome recorded. Available for evaluating future recommendations.';
    }
    // Step 5: Verification outcome
    if (demoStep === 5 && outcome) {
      if (outcome.overall_status === 'USEFUL') {
        return 'Investigation outcome useful. Review and preserve for future reference.';
      }
      return `Verification recorded as ${outcome.overall_status?.replace(/_/g, ' ').toLowerCase()}. Review findings.`;
    }
    // Steps 3-4: AI recommended action
    if (topAction) return topAction.action;
    return 'Awaiting recommended actions.';
  }

  /* ── Supporting evidence signals ───────────────────── */
  function getEvidenceSignals() {
    const signals = [];
    // Step 6+: Historical accountability signal first
    if (demoStep >= 6) {
      signals.push({ label: 'Historical Cases', value: '12 evaluated', color: '#0d9488' });
    }
    // Step 4+: Exposure signals next
    if (demoStep >= 4 && vulnerableCount > 0) {
      signals.push({ label: 'Vulnerable Sites', value: String(vulnerableCount), color: '#0d9488' });
    }
    if (demoStep >= 4 && exposureGeometry?.investigation_area?.priority) {
      signals.push({ label: 'Area Priority', value: exposureGeometry.investigation_area.priority, color: '#d97706' });
    }
    // Steps 3+: AI confidence
    if (hasAnalysis && topHypothesis?.confidence) {
      signals.push({ label: 'Confidence', value: `${Math.round(topHypothesis.confidence * 100)}%`, color: '#d97706' });
    }
    // Core signals: PM2.5 and trajectory
    if (pm25 != null) {
      signals.push({ label: 'PM2.5', value: formatPM25(pm25), color: episodeState === 'episode' ? '#dc2626' : '#16a34a' });
    }
    if (trajectory) {
      const trajColor = trajectory === 'rising' ? '#dc2626' : trajectory === 'falling' ? '#16a34a' : '#6b7280';
      signals.push({ label: 'Trend', value: trajectory, color: trajColor });
    }
    return signals;
  }

  const status = getStatus();
  const whatHappened = getWhatHappened();
  const assessment = getSystemAssessment();
  const action = getRecommendedAction();
  const evidence = getEvidenceSignals();
  const AssessmentIcon = assessment.icon;

  return (
    <div
      className="eds"
      role="region"
      aria-label="Executive decision summary"
      data-testid="executive-decision-summary"
      data-demo-step={demoStep}
    >
      {/* ── Status Badge ─────────────────────────────── */}
      <div className="eds__header">
        <span
          className="eds__status-badge lp-motion-scale-in"
          data-testid="eds-status-badge"
          style={{
            color: status.color,
            backgroundColor: status.bg,
            borderColor: status.border,
          }}
        >
          <span className="eds__status-dot" style={{ backgroundColor: status.color }} aria-hidden="true" />
          {status.label}
        </span>
        <span className="eds__header-label">Executive Summary</span>
      </div>

      {/* ── 1. What Happened ─────────────────────────── */}
      <div className="eds__row lp-motion-fade-up" style={{ animationDelay: '60ms' }} data-testid="eds-what-happened">
        <div className="eds__row-label">What happened</div>
        <div className="eds__row-text">{whatHappened}</div>
      </div>

      {/* ── 2. System Assessment ─────────────────────── */}
      <div className="eds__row lp-motion-fade-up" style={{ animationDelay: '120ms' }} data-testid="eds-system-assessment">
        <div className="eds__row-label">
          {assessment.verified ? 'Verified outcome' : 'System assessment'}
        </div>
        <div className="eds__row-text eds__row-text--assessment">
          <AssessmentIcon size={14} color={assessment.color || 'var(--lp-text-secondary)'} aria-hidden="true" />
          <span>{assessment.text}</span>
        </div>
        {demoStep >= 3 && !assessment.verified && hasAnalysis && (
          <span className="eds__not-verified" data-testid="eds-not-verified">NOT VERIFIED</span>
        )}
      </div>

      {/* ── 3. Recommended Human Action ──────────────── */}
      <div className="eds__row lp-motion-fade-up" style={{ animationDelay: '180ms' }} data-testid="eds-recommended-action">
        <div className="eds__row-label">What should a human do</div>
        <div className="eds__row-text eds__row-text--action">{action}</div>
      </div>

      {/* ── 4. Supporting Evidence ────────────────────── */}
      <div className="eds__row lp-motion-fade-up" style={{ animationDelay: '240ms' }} data-testid="eds-evidence">
        <div className="eds__row-label">Supporting evidence</div>
        <div className="eds__signals">
          {evidence.slice(0, 3).map((sig) => (
            <span key={sig.label} className="eds__signal" data-testid="eds-signal">
              <span className="eds__signal-label">{sig.label}</span>
              <span className="eds__signal-value" style={{ color: sig.color }}>{sig.value}</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── 5. Verification Status ───────────────────── */}
      <div className="eds__row lp-motion-fade-up" style={{ animationDelay: '300ms' }} data-testid="eds-verification-status">
        <div className="eds__row-label">Verification status</div>
        <div className="eds__row-text">
          {verification ? (
            <span className="eds__verification" style={{ color: verification.color }}>
              <verification.icon size={13} aria-hidden="true" />
              {verification.label}
            </span>
          ) : demoStep >= 3 ? (
            <span className="eds__pending">
              <Clock size={13} aria-hidden="true" />
              Awaiting human verification
            </span>
          ) : (
            <span className="eds__pending">
              <Clock size={13} aria-hidden="true" />
              N/A
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
