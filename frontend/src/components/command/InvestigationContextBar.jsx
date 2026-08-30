/**
 * InvestigationContextBar — Persistent compact context for scrolling.
 *
 * Shows essential operational awareness when the officer scrolls past
 * the Executive Decision Summary. Appears sticky at top of viewport.
 *
 * Contains ONLY:
 *   - Incident status (from episode state)
 *   - PM2.5 reading
 *   - Trend
 *   - Investigation stage
 *   - Verification status (when available)
 *
 * Does NOT duplicate ExecutiveDecisionSummary.
 * Does NOT show evidence signals or system assessment.
 * Adapts for desktop/tablet/mobile.
 */

import { useEffect, useState, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus, CheckCircle, Clock, AlertTriangle } from 'lucide-react';

/**
 * Determine investigation stage label from demo step.
 */
function getStageLabel(demoStep) {
  switch (demoStep) {
    case 1: return 'Monitoring';
    case 2: return 'Event Detected';
    case 3: return 'Investigation';
    case 4: return 'Exposure Analysis';
    case 5: return 'Verification';
    case 6: return 'Accountability';
    default: return 'Monitoring';
  }
}

/**
 * Get stage severity for color coding.
 */
function getStageSeverity(demoStep) {
  if (demoStep <= 1) return 'nominal';
  if (demoStep === 2) return 'alert';
  if (demoStep <= 4) return 'active';
  if (demoStep === 5) return 'verified';
  return 'complete';
}

/**
 * Get verification status text and color.
 */
function getVerificationInfo(verificationContext) {
  const outcome = verificationContext?.current_outcome;
  if (!outcome) return null;
  const status = outcome.overall_status;
  switch (status) {
    case 'USEFUL': return { label: 'USEFUL', color: '#16a34a', icon: CheckCircle };
    case 'NOT_SUPPORTED': return { label: 'NOT SUPPORTED', color: '#dc2626', icon: AlertTriangle };
    case 'PARTIALLY_USEFUL': return { label: 'PARTIAL', color: '#ca8a04', icon: AlertTriangle };
    case 'INCONCLUSIVE': return { label: 'INCONCLUSIVE', color: '#6b7280', icon: Clock };
    default: return null;
  }
}

export default function InvestigationContextBar({
  demoStep,
  episode,
  verificationContext,
  isDemo,
}) {
  const [visible, setVisible] = useState(false);
  const sentinelRef = useRef(null);

  // Observe when the EDS scrolls out of view
  useEffect(() => {
    if (!isDemo || !sentinelRef.current) return;
    if (typeof IntersectionObserver === 'undefined') return;
    const el = sentinelRef.current;
    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(!entry.isIntersecting);
      },
      { rootMargin: '-10px 0px 0px 0px', threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [isDemo]);

  const pm25 = episode?.current_pm25;
  const trajectory = episode?.trajectory || 'stable';
  const stageLabel = getStageLabel(demoStep);
  const stageSeverity = getStageSeverity(demoStep);
  const verification = getVerificationInfo(verificationContext);
  const VerificationIcon = verification?.icon;

  return (
    <>
      {/* Sentinel element placed right after the EDS — when it scrolls out, bar appears */}
      <div ref={sentinelRef} className="icb-sentinel" aria-hidden="true" />

      <div
        className={`icb ${visible ? 'icb--visible' : ''}`}
        role="status"
        aria-label="Investigation context"
        data-testid="investigation-context-bar"
      >
        <div className="icb__inner">
          {/* Status */}
          <span className={`icb__chip icb__chip--${stageSeverity}`}>
            {stageLabel}
          </span>

          {/* PM2.5 */}
          <span className="icb__metric">
            <span className="icb__metric-label">PM2.5</span>
            <span className="icb__metric-value">
              {pm25 != null ? `${Math.round(pm25)} μg/m³` : '—'}
            </span>
          </span>

          {/* Trend */}
          <span className="icb__metric">
            <span className="icb__metric-label">Trend</span>
            <span className="icb__metric-value icb__metric-value--trend">
              {trajectory === 'rising' && <TrendingUp size={12} aria-hidden="true" />}
              {trajectory === 'falling' && <TrendingDown size={12} aria-hidden="true" />}
              {trajectory === 'stable' && <Minus size={12} aria-hidden="true" />}
              {trajectory}
            </span>
          </span>

          {/* Verification — only when available */}
          {verification && (
            <span className="icb__verification" style={{ color: verification.color }}>
              {VerificationIcon && <VerificationIcon size={12} aria-hidden="true" />}
              {verification.label}
            </span>
          )}
        </div>
      </div>
    </>
  );
}
