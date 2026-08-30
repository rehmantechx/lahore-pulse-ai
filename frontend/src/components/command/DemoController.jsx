/**
 * DemoController — Guided demonstration controller for competition judges.
 *
 * Appears ONLY when ?demo=true is in the URL.
 * Provides step-by-step walkthrough of the full investigation story.
 *
 * 6 steps tell ONE coherent story:
 *   Normal Conditions → Abnormal Event → Investigation →
 *   Exposure → Verification → Accountability
 */

import { useEffect, useRef, useState } from 'react';
import { RotateCcw, ChevronRight, ChevronLeft } from 'lucide-react';
import { DEMO_STEPS, TOTAL_STEPS, nextStep, prevStep, FINAL_MESSAGE } from '../../demo/stateMachine';
import { useDemoData } from '../../demo';
import DemoLegend from './DemoLegend';
import { useStepTransition } from '../../hooks/useStepTransition';
import { getSimulationState } from '../../demo/simulationState';
import IncidentTimeline from './IncidentTimeline';
import InvestigationActivityFeed from './InvestigationActivityFeed';

export default function DemoController() {
  const { demoStep, setDemoStep, resetDemo } = useDemoData();
  const current = DEMO_STEPS.find((s) => s.id === demoStep) || DEMO_STEPS[0];
  const stepRef = useRef(demoStep);
  const { phase, isTransitioning } = useStepTransition(demoStep);
  const [infoKey, setInfoKey] = useState(demoStep);

  /* ── Scroll to relevant section on step change ─────────── */
  useEffect(() => {
    if (demoStep === stepRef.current) return;
    stepRef.current = demoStep;

    const { sectionId } = current;
    if (!sectionId) return;

    const timer = setTimeout(() => {
      const el = document.querySelector(`[data-demo-section="${sectionId}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 150);
    return () => clearTimeout(timer);
  }, [demoStep, current]);

  /* Update infoKey when entering new step for animation restart */
  useEffect(() => {
    if (phase === 'entering') {
      setInfoKey(demoStep);
    }
  }, [phase, demoStep]);

  const simulation = getSimulationState(demoStep);

  const isAtStart = demoStep === 1;
  const isAtEnd = demoStep === TOTAL_STEPS;
  const infoPhaseClass = phase === 'exiting' ? 'lp-transition-content--exiting'
    : phase === 'entering' ? 'lp-transition-content--entering' : '';

  return (
    <div className="demo-controller" role="complementary" aria-label="Demo walkthrough">
      {/* Header */}
      <div className="demo-controller__header">
        <span className="demo-controller__logo">LAHORE+</span>
        <span className="demo-controller__subtitle">DEMONSTRATION</span>
      </div>

      {/* Step progress */}
      <div className="demo-controller__steps">
        {DEMO_STEPS.map((step) => {
          const isCurrent = step.id === demoStep;
          const isPast = step.id < demoStep;
          return (
            <div
              key={step.id}
              className={`demo-step ${isCurrent ? 'demo-step--active' : ''} ${isPast ? 'demo-step--done' : ''}`}
              data-testid="demo-step-indicator"
              aria-current={isCurrent ? 'step' : undefined}
            >
              <div
                className={`demo-step__dot ${isCurrent ? 'demo-step__dot--active' : ''} ${isPast ? 'demo-step__dot--done' : ''}`}
                style={isCurrent ? { transform: 'scale(1.1)' } : undefined}
              >
                {isPast ? <span aria-hidden="true">{'\u2713'}</span> : step.id}
              </div>
              <span className="demo-step__label">
                {current.id === step.id ? current.question : '\u00a0'}
              </span>
            </div>
          );
        })}
      </div>

      {/* Current step info */}
      <div
        className={`demo-controller__info lp-transition-content ${infoPhaseClass}`}
        data-testid="demo-step-info"
        key={infoKey}
      >
        <div className="demo-controller__step-title lp-motion-fade-up">
          Step {demoStep}: {current.label}
        </div>
        <p className="demo-controller__description lp-motion-fade-up" style={{ animationDelay: '60ms' }}>{current.description}</p>
        <p className="demo-controller__narration lp-motion-fade-up" style={{ animationDelay: '120ms' }}>{current.narration}</p>
        {current.caveat && (
          <p className="demo-controller__caveat lp-motion-fade-up" style={{ animationDelay: '180ms' }}>{current.caveat}</p>
        )}
        {current.emphasis && (
          <div className="demo-controller__emphasis lp-motion-scale-in" role="alert">
            {current.emphasis}
          </div>
        )}
        {isAtEnd && (
          <p className="demo-controller__final-message lp-motion-fade-in" style={{ animationDelay: '200ms' }}>{FINAL_MESSAGE}</p>
        )}
      </div>

      {/* Incident Timeline */}
      <IncidentTimeline timeline={simulation.timeline} />

      {/* Activity Feed */}
      <InvestigationActivityFeed activityFeed={simulation.activityFeed} />

      {/* Progressive Layer Legend */}
      <DemoLegend activeLayers={current.layers || []} transitionKey={demoStep} />

      {/* Controls */}
      <div className="demo-controller__controls">
        <button
          className="demo-btn demo-btn--secondary lp-btn-premium"
          onClick={() => setDemoStep(prevStep(demoStep))}
          disabled={isAtStart}
          aria-label="Previous step"
          data-testid="demo-prev"
        >
          <ChevronLeft size={14} aria-hidden="true" /> Prev
        </button>
        <button
          className="demo-btn demo-btn--primary lp-btn-premium"
          onClick={() => setDemoStep(nextStep(demoStep))}
          disabled={isAtEnd}
          aria-label="Next step"
          data-testid="demo-next"
        >
          Next <ChevronRight size={14} aria-hidden="true" />
        </button>
        <button
          className="demo-btn demo-btn--reset lp-btn-premium"
          onClick={resetDemo}
          aria-label="Reset demo"
          data-testid="demo-reset"
        >
          <RotateCcw size={12} aria-hidden="true" /> Reset
        </button>
      </div>
    </div>
  );
}
