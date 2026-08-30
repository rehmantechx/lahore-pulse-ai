/**
 * WhyDifferent — Judge-facing "How Our Solution Is Different" panel.
 *
 * Compact, defensible, based on actual implementation.
 * No marketing exaggeration, no unsupported uniqueness claims.
 */

import {
  Eye, Brain, Shield, ArrowRight, CheckCircle2,
  AlertTriangle, Users, TrendingUp
} from 'lucide-react';

const DIFFERENTIATORS = [
  {
    icon: Eye,
    color: 'var(--lp-brand)',
    title: 'Beyond AQI Dashboards',
    description:
      'Lahore+ does not stop at displaying a pollution value. It detects abnormal events and turns them into structured investigations.',
  },
  {
    icon: Brain,
    color: '#d97706',
    title: 'AI Receives Evidence, Not Raw Context',
    description:
      'The AI reasoning layer receives a structured evidence package with constraints. It cannot fabricate data it was not given.',
  },
  {
    icon: Shield,
    color: '#7c3aed',
    title: 'Facts, Inference, and Hypotheses Are Separated',
    description:
      'Every piece of information is labeled as observed data, deterministic inference, or AI hypothesis — never presented as equal.',
  },
  {
    icon: TrendingUp,
    color: '#0d9488',
    title: 'Predicts Approximate Exposure Direction',
    description:
      'Wind-driven geometry estimates where pollution may travel, highlighting vulnerable locations in the approximate path.',
  },
  {
    icon: Users,
    color: '#16a34a',
    title: 'Human Decision-Maker Stays in Control',
    description:
      'The system recommends investigation priorities. A human officer decides what to do and records whether the recommendation was useful.',
  },
  {
    icon: CheckCircle2,
    color: '#dc2626',
    title: 'Recommendations Are Verified and Evaluated Over Time',
    description:
      'Human verification outcomes become part of the investigation history. The system shows accountability instead of pretending it was always correct.',
  },
];

export default function WhyDifferent() {
  return (
    <div className="why-different" role="region" aria-label="How our solution is different">
      <div className="why-different__header">
        <span className="why-different__label">Submission</span>
        <h3 className="why-different__title">How Our Solution Is Different</h3>
        <p className="why-different__subtitle">
          Based on the actual implementation — not marketing claims.
        </p>
      </div>

      {/* WHO / PROBLEM / DECISION */}
      <div className="why-different__context">
        <div className="why-different__context-item">
          <span className="why-different__context-label">WHO</span>
          <span className="why-different__context-value">
            Environmental response teams and city decision-makers in Lahore, Punjab.
          </span>
        </div>
        <div className="why-different__context-item">
          <span className="why-different__context-label">PROBLEM</span>
          <span className="why-different__context-value">
            During a sudden pollution episode, teams have limited time and resources.
            They may not know where to investigate first.
          </span>
        </div>
        <div className="why-different__context-item">
          <span className="why-different__context-label">DECISION</span>
          <span className="why-different__context-value why-different__context-value--bold">
            "Where should we investigate first right now?"
          </span>
        </div>
      </div>

      {/* Differentiators */}
      <div className="why-different__grid">
        {DIFFERENTIATORS.map((item, i) => {
          const Icon = item.icon;
          return (
            <div key={i} className="why-different__card">
              <div className="why-different__card-icon" style={{ color: item.color }}>
                <Icon size={18} strokeWidth={1.5} aria-hidden="true" />
              </div>
              <div className="why-different__card-content">
                <h4 className="why-different__card-title">{item.title}</h4>
                <p className="why-different__card-desc">{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="why-different__footer">
        <AlertTriangle size={12} aria-hidden="true" />
        <span>
          Lahore+ does not claim source attribution, real-time government integration,
          or 100% accuracy. It claims to help humans investigate faster with clearer evidence.
        </span>
      </div>
    </div>
  );
}
