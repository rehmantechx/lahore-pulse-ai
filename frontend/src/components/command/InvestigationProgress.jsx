/**
 * InvestigationProgress — Step 3 evidence-processing sequence.
 *
 * Shows the deterministic investigation pipeline:
 *   anomaly confirmed → boundaries calculated → meteorological context →
 *   historical comparison → evidence ranked → hypotheses generated
 *
 * Each step appears as completed when visible, or shows as current.
 * After all steps complete, the existing investigation content is shown.
 */

import { Check, ArrowRight } from 'lucide-react';

export default function InvestigationProgress({ progress = [], isComplete = false }) {
  const visibleSteps = progress.filter((s) => s.visible);
  if (visibleSteps.length === 0) return null;

  return (
    <div className="investigation-progress" role="region" aria-label="Investigation evidence processing">
      <div className="investigation-progress__steps lp-motion-stagger">
        {visibleSteps.map((step, i) => {
          const isCurrent = step.status === 'current';
          const isCompleted = step.status === 'completed';
          const isLast = i === visibleSteps.length - 1;

          return (
            <div
              key={step.id}
              className={`investigation-progress__step ${isCurrent ? 'investigation-progress__step--current' : ''} ${isCompleted ? 'investigation-progress__step--done' : ''}`}
            >
              <div className={`investigation-progress__check ${isCompleted ? 'investigation-progress__check--done' : ''} ${isCurrent ? 'investigation-progress__check--active' : ''}`}>
                {isCompleted ? (
                  <Check size={12} strokeWidth={3} aria-hidden="true" />
                ) : (
                  <ArrowRight size={12} aria-hidden="true" />
                )}
              </div>
              <span className="investigation-progress__label">{step.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
