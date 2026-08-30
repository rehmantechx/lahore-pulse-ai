/**
 * EvidenceContext — Shared evidence selection state for the Command Center.
 *
 * Allows cross-component evidence linking:
 *   DecisionTrace ↔ ExposureIntelligenceMap ↔ InvestigationVerification
 *   ↔ InvestigationLearning ↔ ExecutiveDecisionSummary
 *
 * Lightweight React-only state — no external state management library.
 *
 * Evidence item structure:
 *   { id: string, layer: 'observed'|'deterministic'|'ai'|'verified'|'accountability',
 *     componentGroup: string, relatedIds: string[] }
 */

import { createContext, useContext, useState, useCallback, useMemo } from 'react';

const EvidenceSelectionContext = createContext(null);

/**
 * Evidence layer definitions — consistent across all components.
 */
export const EVIDENCE_LAYERS = {
  observed: { label: 'OBSERVED', color: 'var(--lp-brand)', desc: 'Directly measured data' },
  deterministic: { label: 'DETERMINISTIC', color: '#3b82f6', desc: 'Rules-based analysis' },
  ai: { label: 'AI HYPOTHESIS', color: '#d97706', desc: 'Hypotheses from evidence' },
  verified: { label: 'HUMAN VERIFIED', color: '#16a34a', desc: 'Field verification' },
  accountability: { label: 'ACCOUNTABILITY', color: '#6b21a8', desc: 'Historical learning' },
};

/**
 * Component group constants for relating evidence across components.
 */
export const COMPONENT_GROUPS = {
  OBSERVATION: 'observation',
  ENVIRONMENTAL_CONTEXT: 'environmental-context',
  SOURCE_COMPASS: 'source-compass',
  EPISODE_DETECTION: 'episode-detection',
  HYPOTHESIS: 'hypothesis',
  INVESTIGATION_PRIORITY: 'investigation-priority',
  RECOMMENDED_ACTION: 'recommended-action',
  EXPOSURE_CORRIDOR: 'exposure-corridor',
  VULNERABLE_SITE: 'vulnerable-site',
  VERIFICATION_OUTCOME: 'verification-outcome',
  HISTORICAL_CASE: 'historical-case',
  ACCOUNTABILITY_STAGE: 'accountability-stage',
};

/**
 * EvidenceProvider — wraps children and provides shared selection state.
 */
export function EvidenceProvider({ children }) {
  const [selectedEvidence, setSelectedEvidence] = useState(null);

  const selectEvidence = useCallback((id, layer, componentGroup, relatedIds = []) => {
    setSelectedEvidence((prev) => {
      // Toggle off if same evidence is clicked again
      if (prev && prev.id === id) return null;
      return { id, layer, componentGroup, relatedIds };
    });
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedEvidence(null);
  }, []);

  const isRelatedTo = useCallback((componentGroup) => {
    if (!selectedEvidence) return false;
    return selectedEvidence.relatedIds.includes(componentGroup);
  }, [selectedEvidence]);

  const isSelected = useCallback((componentGroup) => {
    if (!selectedEvidence) return false;
    return selectedEvidence.componentGroup === componentGroup;
  }, [selectedEvidence]);

  const isHighlighted = useCallback((componentGroup) => {
    if (!selectedEvidence) return true; // nothing selected = everything normal
    if (selectedEvidence.componentGroup === componentGroup) return true;
    if (selectedEvidence.relatedIds.includes(componentGroup)) return true;
    return false;
  }, [selectedEvidence]);

  const value = useMemo(() => ({
    selectedEvidence,
    selectEvidence,
    clearSelection,
    isRelatedTo,
    isSelected,
    isHighlighted,
    hasSelection: Boolean(selectedEvidence),
  }), [selectedEvidence, selectEvidence, clearSelection, isRelatedTo, isSelected, isHighlighted]);

  return (
    <EvidenceSelectionContext.Provider value={value}>
      {children}
    </EvidenceSelectionContext.Provider>
  );
}

/**
 * Hook to access shared evidence selection state.
 */
export function useEvidenceSelection() {
  const ctx = useContext(EvidenceSelectionContext);
  if (!ctx) {
    // Return no-op defaults when used outside EvidenceProvider
    return {
      selectedEvidence: null,
      selectEvidence: () => {},
      clearSelection: () => {},
      isRelatedTo: () => false,
      isSelected: () => false,
      isHighlighted: () => true,
      hasSelection: false,
    };
  }
  return ctx;
}
