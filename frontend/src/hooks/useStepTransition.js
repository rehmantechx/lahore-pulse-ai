/**
 * useStepTransition — Lightweight hook for demo step transition state.
 *
 * Returns a transition phase ('idle' | 'exiting' | 'entering' | 'active')
 * that components can use to apply appropriate CSS classes.
 *
 * Flow: idle → exiting (150ms) → entering (400ms) → active
 * The hook manages timing and provides phase to consumers.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const PHASE_DURATION = {
  idle: 0,
  exiting: 120,
  entering: 400,
};

/**
 * @param {number} step - Current demo step number
 * @returns {{ phase: string, isTransitioning: boolean, onTransitionEnd: () => void }}
 */
export function useStepTransition(step) {
  const [phase, setPhase] = useState('active');
  const timeoutRef = useRef(null);
  const prevStepRef = useRef(step);

  const clearTimers = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    // Step didn't change — skip
    if (step === prevStepRef.current) return;

    prevStepRef.current = step;
    clearTimers();

    // Start exit phase
    setPhase('exiting');

    // After exit duration, switch to entering
    timeoutRef.current = setTimeout(() => {
      setPhase('entering');

      // After enter duration, settle to active
      timeoutRef.current = setTimeout(() => {
        setPhase('active');
        timeoutRef.current = null;
      }, PHASE_DURATION.entering);
    }, PHASE_DURATION.exiting);

    return () => clearTimers();
  }, [step, clearTimers]);

  const onTransitionEnd = useCallback(() => {
    if (phase === 'entering') {
      setPhase('active');
      clearTimers();
    }
  }, [phase, clearTimers]);

  return {
    phase,
    isTransitioning: phase === 'exiting' || phase === 'entering',
    onTransitionEnd,
  };
}
