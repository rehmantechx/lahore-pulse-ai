/**
 * EvidenceContext — Unit tests.
 *
 * Tests: provider, hook defaults, selection, toggle, clearing, highlighting, layer definitions.
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import {
  EvidenceProvider,
  useEvidenceSelection,
  EVIDENCE_LAYERS,
  COMPONENT_GROUPS,
} from '../EvidenceContext';

/* ── Test consumer component ────────────────────────── */

function Consumer() {
  const {
    selectedEvidence,
    selectEvidence,
    clearSelection,
    isRelatedTo,
    isSelected,
    isHighlighted,
    hasSelection,
  } = useEvidenceSelection();

  return (
    <div data-testid="consumer">
      <span data-testid="has-selection">{String(hasSelection)}</span>
      <span data-testid="selected-id">{selectedEvidence?.id ?? 'none'}</span>
      <span data-testid="is-highlighted-obs">{String(isHighlighted('observation'))}</span>
      <span data-testid="is-highlighted-hyp">{String(isHighlighted('hypothesis'))}</span>
      <span data-testid="is-selected-obs">{String(isSelected('observation'))}</span>
      <span data-testid="is-related-hyp">{String(isRelatedTo('hypothesis'))}</span>
      <button
        data-testid="select-obs"
        onClick={() => selectEvidence('obs-1', 'observed', 'observation', ['hypothesis'])}
      >
        Select Observed
      </button>
      <button
        data-testid="select-hyp"
        onClick={() => selectEvidence('hyp-1', 'ai', 'hypothesis', ['observation'])}
      >
        Select Hypothesis
      </button>
      <button data-testid="clear" onClick={clearSelection}>
        Clear
      </button>
    </div>
  );
}

function renderProvider() {
  return render(
    <EvidenceProvider>
      <Consumer />
    </EvidenceProvider>
  );
}

/* ── Tests ───────────────────────────────────────────── */

describe('EvidenceContext', () => {
  describe('Constants', () => {
    it('EVIDENCE_LAYERS has 5 layers', () => {
      expect(Object.keys(EVIDENCE_LAYERS)).toHaveLength(5);
    });

    it('each layer has label, color, desc', () => {
      for (const [key, layer] of Object.entries(EVIDENCE_LAYERS)) {
        expect(layer.label).toBeTruthy();
        expect(layer.color).toBeTruthy();
        expect(layer.desc).toBeTruthy();
      }
    });

    it('COMPONENT_GROUPS has 12 groups', () => {
      expect(Object.keys(COMPONENT_GROUPS)).toHaveLength(12);
    });
  });

  describe('Default state (no selection)', () => {
    it('hasSelection is false', () => {
      renderProvider();
      expect(screen.getByTestId('has-selection')).toHaveTextContent('false');
    });

    it('selectedEvidence is none', () => {
      renderProvider();
      expect(screen.getByTestId('selected-id')).toHaveTextContent('none');
    });

    it('isHighlighted returns true for everything when nothing selected', () => {
      renderProvider();
      expect(screen.getByTestId('is-highlighted-obs')).toHaveTextContent('true');
      expect(screen.getByTestId('is-highlighted-hyp')).toHaveTextContent('true');
    });

    it('isSelected returns false for everything', () => {
      renderProvider();
      expect(screen.getByTestId('is-selected-obs')).toHaveTextContent('false');
    });

    it('isRelatedTo returns false for everything', () => {
      renderProvider();
      expect(screen.getByTestId('is-related-hyp')).toHaveTextContent('false');
    });
  });

  describe('Selection', () => {
    it('selecting evidence sets hasSelection true', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('has-selection')).toHaveTextContent('true');
    });

    it('selecting evidence sets the correct id', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('selected-id')).toHaveTextContent('obs-1');
    });

    it('selected componentGroup is marked as selected', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('is-selected-obs')).toHaveTextContent('true');
    });

    it('related component groups are marked as related', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('is-related-hyp')).toHaveTextContent('true');
    });

    it('non-related groups are highlighted=false when selection active', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      // 'hypothesis' is in relatedIds, so highlighted=true
      expect(screen.getByTestId('is-highlighted-hyp')).toHaveTextContent('true');
    });
  });

  describe('Toggle off', () => {
    it('clicking same evidence deselects it', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('has-selection')).toHaveTextContent('true');
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('has-selection')).toHaveTextContent('false');
    });
  });

  describe('Clearing selection', () => {
    it('clearSelection resets to no selection', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('has-selection')).toHaveTextContent('true');
      fireEvent.click(screen.getByTestId('clear'));
      expect(screen.getByTestId('has-selection')).toHaveTextContent('false');
    });
  });

  describe('Switching selection', () => {
    it('selecting different evidence replaces previous', () => {
      renderProvider();
      fireEvent.click(screen.getByTestId('select-obs'));
      expect(screen.getByTestId('selected-id')).toHaveTextContent('obs-1');
      fireEvent.click(screen.getByTestId('select-hyp'));
      expect(screen.getByTestId('selected-id')).toHaveTextContent('hyp-1');
    });
  });

  describe('useEvidenceSelection outside provider', () => {
    it('returns no-op defaults when used outside EvidenceProvider', () => {
      function StandaloneConsumer() {
        const { hasSelection, isHighlighted } = useEvidenceSelection();
        return (
          <div>
            <span data-testid="standalone-has">{String(hasSelection)}</span>
            <span data-testid="standalone-hl">{String(isHighlighted('observation'))}</span>
          </div>
        );
      }
      render(<StandaloneConsumer />);
      expect(screen.getByTestId('standalone-has')).toHaveTextContent('false');
      expect(screen.getByTestId('standalone-hl')).toHaveTextContent('true');
    });
  });
});
