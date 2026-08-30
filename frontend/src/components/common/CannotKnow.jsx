/**
 * CannotKnow — Compact "What Lahore+ Cannot Know" section.
 *
 * Strengthens credibility by being transparent about limitations.
 * Each item is based on actual system constraints.
 */

import { AlertTriangle } from 'lucide-react';

const LIMITATIONS = [
  {
    title: 'Directional analysis is not source attribution',
    detail: 'We cannot confirm a specific pollution source from this data alone. The system shows wind direction and sector enrichment, not factory identities.',
  },
  {
    title: 'AI hypotheses are not confirmed facts',
    detail: 'The AI reasoning layer generates constrained investigation hypotheses from available evidence. These require human field verification before being treated as conclusions.',
  },
  {
    title: 'Exposure geometry is approximate',
    detail: 'We cannot guarantee that pollution will follow the exact displayed exposure path. Wind patterns, terrain, and local sources create real-world variation.',
  },
  {
    title: 'Weather and environmental data have spatial limitations',
    detail: 'Environmental data is interpolated from grid models, not measured at every point. Local conditions may differ from regional estimates.',
  },
  {
    title: 'Historical patterns show association, not causation',
    detail: 'The source compass shows which wind sectors correlate with past episodes. Correlation does not prove that pollution came from that direction.',
  },
  {
    title: 'The system does not identify specific polluters',
    detail: 'Lahore+ is an investigation-support tool, not a source-identification system. It helps teams decide where to look, not who to blame.',
  },
  {
    title: 'Human verification is required before conclusions',
    detail: 'No recommendation is treated as validated until a human response officer records a verification outcome.',
  },
];

export default function CannotKnow() {
  return (
    <div className="cannot-know" role="region" aria-label="What Lahore+ cannot know">
      <div className="cannot-know__header">
        <AlertTriangle size={16} className="cannot-know__icon" aria-hidden="true" />
        <div>
          <h3 className="cannot-know__title">What Lahore+ Cannot Know</h3>
          <p className="cannot-know__subtitle">
            Understanding these limits strengthens the system's credibility.
          </p>
        </div>
      </div>
      <div className="cannot-know__list">
        {LIMITATIONS.map((item, i) => (
          <div key={i} className="cannot-know__item">
            <h4 className="cannot-know__item-title">{item.title}</h4>
            <p className="cannot-know__item-detail">{item.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
