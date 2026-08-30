/**
 * AccountabilityChain — Full investigation chain visualization.
 *
 * Shows the complete lifecycle from observation to future evaluation.
 * Each stage maps to actual Lahore+ functionality.
 *
 * Language is careful:
 *   GOOD: "Verified outcomes retained for future evaluation"
 *   BAD: "The AI learns and improves itself"
 *
 * This is deterministic. No AI claims about automatic improvement.
 */

import { Eye, AlertTriangle, Database, Brain, ClipboardCheck, FileText, TrendingUp, ArrowDown } from 'lucide-react';

const STAGE_ICONS = {
  'ac-observation': Eye,
  'ac-episode': AlertTriangle,
  'ac-evidence': Database,
  'ac-hypothesis': Brain,
  'ac-verification': ClipboardCheck,
  'ac-outcome': FileText,
  'ac-future': TrendingUp,
};

const STAGE_COLORS = {
  'ac-observation': 'var(--lp-brand)',
  'ac-episode': '#dc2626',
  'ac-evidence': '#3b82f6',
  'ac-hypothesis': '#d97706',
  'ac-verification': '#16a34a',
  'ac-outcome': '#16a34a',
  'ac-future': '#2563eb',
};

export default function AccountabilityChain({ chain = [] }) {
  const visibleStages = chain.filter((s) => s.visible);
  if (visibleStages.length === 0) return null;

  return (
    <div className="accountability-chain lp-motion-stagger-lg" role="region" aria-label="Investigation accountability chain">
      {chain.map((stage, i) => {
        const Icon = STAGE_ICONS[stage.id] || Eye;
        const color = STAGE_COLORS[stage.id] || '#64748b';
        const isCurrent = stage.status === 'current';
        const isCompleted = stage.status === 'completed';
        const isLast = i === chain.length - 1;

        if (!stage.visible) return null;

        return (
          <div key={stage.id}>
            <div className={`accountability-chain__stage ${isCurrent ? 'accountability-chain__stage--current' : ''} ${isCompleted ? 'accountability-chain__stage--done' : ''}`}>
              <div
                className="accountability-chain__icon"
                style={{ color, borderColor: isCompleted || isCurrent ? color : undefined }}
              >
                <Icon size={14} aria-hidden="true" />
              </div>
              <div className="accountability-chain__content">
                <span className="accountability-chain__label" style={isCurrent ? { color } : undefined}>
                  {stage.label}
                </span>
                <span className="accountability-chain__detail">{stage.detail}</span>
              </div>
            </div>
            {!isLast && stage.visible && (
              <div className="accountability-chain__connector" aria-hidden="true">
                <ArrowDown size={12} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
