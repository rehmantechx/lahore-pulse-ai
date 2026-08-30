/**
 * DecisionEvidenceChain — 5-step evidence chain answering
 * "Why do we trust this alert?"
 *
 * Each step has a title, icon, data label, source, and detail.
 * Steps animate in with 120ms stagger when the chain opens.
 *
 * Phase 29 — Government Trust & Decision Intelligence Layer.
 * Clearly labeled as a decision-support prototype.
 */

import { useState, useEffect, useRef } from 'react';
import {
  Database,
  Brain,
  Search,
  CheckCircle,
  Shield,
} from 'lucide-react';
import { useDemoData } from '../../demo/index';

const ICON_MAP = {
  database: Database,
  brain: Brain,
  search: Search,
  'check-circle': CheckCircle,
  shield: Shield,
};

/**
 * Single evidence step with icon, title, data fields, and detail.
 * Stagger is controlled via CSS animation-delay set as inline style.
 */
function EvidenceStep({ step, index, isVisible }) {
  const Icon = ICON_MAP[step.icon] || Database;

  return (
    <div
      className={`evidence-step evidence-step--${step.status}`}
      style={{ animationDelay: `${index * 120}ms` }}
      data-testid="evidence-step"
    >
      <div className="evidence-step__icon">
        <Icon size={18} color="#10b981" />
      </div>
      <div className="evidence-step__content">
        <div className="evidence-step__title">{step.title}</div>
        <div className="evidence-step__label">{step.data.label}</div>
        {step.data.detail && (
          <div className="evidence-step__detail">{step.data.detail}</div>
        )}
        <div className="evidence-step__meta">
          {step.data.source && (
            <span className="evidence-step__meta-tag">{step.data.source}</span>
          )}
          {step.data.confidence && (
            <span className="evidence-step__meta-tag">
              Confidence: {step.data.confidence}
            </span>
          )}
          {step.data.calibration && (
            <span className="evidence-step__meta-tag">{step.data.calibration}</span>
          )}
          {step.data.freshness && (
            <span className="evidence-step__meta-tag">{step.data.freshness}</span>
          )}
          {step.data.permanent && (
            <span className="evidence-step__meta-tag">{step.data.permanent}</span>
          )}
          {step.data.bestMatch && (
            <span className="evidence-step__meta-tag">{step.data.bestMatch}</span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * DecisionEvidenceChain — renders when `open` is true.
 * Uses demo data when no explicit props are provided.
 */
export default function DecisionEvidenceChain({
  open = false,
  steps: stepsProp,
}) {
  const demoData = useDemoData();
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef(null);

  // Steps from props or demo data
  const steps = stepsProp || demoData?.evidenceChain || [];

  useEffect(() => {
    if (open) {
      // Small delay so CSS transition starts from collapsed state
      const timer = setTimeout(() => setIsVisible(true), 50);
      return () => clearTimeout(timer);
    }
    setIsVisible(false);
    return undefined;
  }, [open]);

  if (!steps.length) return null;

  const filledCount = steps.filter((s) => s.status === 'complete').length;

  return (
    <div
      ref={containerRef}
      className={`why-trust__evidence-container ${isVisible ? 'why-trust__evidence-container--open' : ''}`}
      role="region"
      aria-label="Decision evidence chain"
      data-testid="evidence-chain"
    >
      <div className="evidence-chain" role="list">
        <div
          className={`evidence-chain__connector ${filledCount > 0 ? 'evidence-chain__connector--filled' : ''}`}
          aria-hidden="true"
        />
        {steps.map((step, i) => (
          <EvidenceStep
            key={step.id}
            step={step}
            index={i}
            isVisible={isVisible}
          />
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
        Decision-support prototype — not a government approval workflow.
      </div>
    </div>
  );
}
