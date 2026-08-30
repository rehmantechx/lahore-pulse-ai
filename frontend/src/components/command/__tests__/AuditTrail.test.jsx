/**
 * AuditTrail — Phase 29 Tests.
 *
 * Compact 8-event timeline showing prediction lifecycle.
 * Renders from demo data (auditTrail array) or explicit events prop.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../demo', () => ({
  useDemoData: vi.fn(),
}));

import AuditTrail from '../AuditTrail';
import { useDemoData } from '../../../demo';

const DEMO_AUDIT_TRAIL = [
  { id: 'audit-001', timestamp: '2026-08-28T13:42:00Z', action: 'Data Ingested', actor: 'System', detail: '47 features collected from monitoring station', icon: 'database' },
  { id: 'audit-002', timestamp: '2026-08-28T13:42:12Z', action: 'Evidence Assembled', actor: 'System', detail: 'Wind pattern, source compass, and historical analogs combined', icon: 'layers' },
  { id: 'audit-003', timestamp: '2026-08-28T13:42:18Z', action: 'Investigation Brief', actor: 'AI', detail: '3 constrained hypotheses generated', icon: 'brain' },
  { id: 'audit-004', timestamp: '2026-08-28T13:42:24Z', action: 'Prediction Made', actor: 'AI', detail: 'PM2.5 forecast: 165 μg/m3 at 6h horizon', icon: 'trending-up' },
  { id: 'audit-005', timestamp: '2026-08-28T13:42:30Z', action: 'Alert Generated', actor: 'System', detail: 'Critical threshold exceeded', icon: 'alert-triangle' },
  { id: 'audit-006', timestamp: '2026-08-28T20:05:00Z', action: 'Observation Verified', actor: 'System', detail: 'Observed PM2.5: 181 μg/m3. Error: 9.7%', icon: 'check-circle' },
  { id: 'audit-007', timestamp: '2026-08-28T20:05:12Z', action: 'Investigation Reviewed', actor: 'Officer', detail: 'Industrial emissions confirmed', icon: 'user-check' },
  { id: 'audit-008', timestamp: '2026-08-28T20:06:00Z', action: 'Receipt Finalized', actor: 'System', detail: 'Prediction receipt LP-000184 generated', icon: 'file-text' },
];

describe('AuditTrail', () => {
  beforeEach(() => vi.clearAllMocks());

  describe('Demo mode with audit trail data', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue({
        auditTrail: DEMO_AUDIT_TRAIL,
        demoStep: 7,
      });
    });

    it('renders the audit trail container', () => {
      render(<AuditTrail />);
      expect(screen.getByTestId('audit-trail')).toBeInTheDocument();
    });

    it('renders audit events', () => {
      render(<AuditTrail />);
      const events = screen.getAllByTestId('audit-event');
      expect(events.length).toBeGreaterThan(0);
    });

    it('displays event actions', () => {
      render(<AuditTrail />);
      expect(screen.getByText('Data Ingested')).toBeInTheDocument();
      expect(screen.getByText('Prediction Made')).toBeInTheDocument();
    });

    it('displays event details', () => {
      render(<AuditTrail />);
      expect(screen.getByText(/47 features collected/)).toBeInTheDocument();
    });

    it('shows the Audit Trail label', () => {
      render(<AuditTrail />);
      expect(screen.getByText('Audit Trail')).toBeInTheDocument();
    });
  });

  describe('Explicit events prop', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('renders events from props when provided', () => {
      render(<AuditTrail events={DEMO_AUDIT_TRAIL} />);
      expect(screen.getByTestId('audit-trail')).toBeInTheDocument();
      expect(screen.getAllByTestId('audit-event')).toHaveLength(8);
    });
  });

  describe('Production mode (no demo, no props)', () => {
    beforeEach(() => {
      useDemoData.mockReturnValue(null);
    });

    it('renders nothing when no events', () => {
      const { container } = render(<AuditTrail />);
      expect(container.innerHTML).toBe('');
    });
  });
});
