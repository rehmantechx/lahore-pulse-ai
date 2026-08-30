/**
 * ProductNarrative — Compact product explanation for the landing page.
 *
 * Clearly communicates: Problem → Decision → Solution
 * with visual separation of OBSERVED / DETERMINISTIC / AI / HUMAN layers.
 */

import { Eye, Cpu, Brain, Users, AlertTriangle } from 'lucide-react';

const LAYERS = [
  {
    icon: Eye,
    label: 'Observed',
    color: 'var(--lp-brand)',
    description: 'Directly measured PM2.5, wind, weather data.',
  },
  {
    icon: Cpu,
    label: 'Deterministic',
    color: '#7c3aed',
    description: 'Episode detection, source compass, exposure geometry.',
  },
  {
    icon: Brain,
    label: 'AI Hypothesis',
    color: '#d97706',
    description: 'Constrained investigation hypotheses from evidence.',
  },
  {
    icon: Users,
    label: 'Human Verification',
    color: '#16a34a',
    description: 'Field officers confirm or reject recommendations.',
  },
];

export default function ProductNarrative() {
  return (
    <section className="lp-narrative">
      <div className="lp-narrative__inner">
        <span className="lp-section-label">How It Works</span>
        <h2 className="lp-narrative__title">
          Not another AQI dashboard.
        </h2>
        <p className="lp-narrative__problem">
          A pollution spike tells authorities that something is happening,
          but not <em>where</em> limited response resources should be deployed first.
        </p>

        <div className="lp-narrative__decision">
          <span className="lp-narrative__decision-label">THE DECISION</span>
          <span className="lp-narrative__decision-text">
            "Where should we investigate first?"
          </span>
        </div>

        <p className="lp-narrative__solution">
          Lahore+ detects abnormal pollution events, assembles environmental evidence,
          uses AI to generate constrained investigation hypotheses,
          predicts approximate exposure direction, recommends investigation priorities,
          and records whether human officers found the recommendations useful.
        </p>

        {/* 4-layer breakdown */}
        <div className="lp-narrative__layers">
          {LAYERS.map((layer) => {
            const Icon = layer.icon;
            return (
              <div key={layer.label} className="lp-narrative__layer">
                <div className="lp-narrative__layer-icon" style={{ color: layer.color }}>
                  <Icon size={18} strokeWidth={1.5} aria-hidden="true" />
                </div>
                <div className="lp-narrative__layer-content">
                  <span className="lp-narrative__layer-label" style={{ color: layer.color }}>
                    {layer.label}
                  </span>
                  <span className="lp-narrative__layer-desc">{layer.description}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="lp-narrative__note">
          <AlertTriangle size={12} aria-hidden="true" />
          <span>
            The AI does not decide what caused pollution.
            It helps humans investigate faster with clearer evidence.
          </span>
        </div>
      </div>
    </section>
  );
}
