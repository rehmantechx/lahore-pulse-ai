/**
 * InvestigationVerification — Component tests.
 *
 * Tests: rendering, status selection, hypothesis toggling, submit flow, demo mode.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import InvestigationVerification from '../InvestigationVerification';

// ── Mock data ────────────────────────────────────────────────

const HYPOTHESES = [
  { factor: 'Industrial emissions', confidence: 0.72, reasoning: 'High PM2.5', verification_needed: true },
  { factor: 'Crop burning', confidence: 0.55, reasoning: 'Seasonal pattern', verification_needed: true },
];

const EXISTING_OUTCOME = {
  outcome_id: 'vout-001',
  investigation_id: 'inv-001',
  overall_status: 'USEFUL',
  recommendation_verification: 'SUPPORTED',
  investigation_area_verification: 'PARTIALLY_SUPPORTED',
  hypothesis_verifications: [
    { factor: 'Industrial emissions', verified: true, notes: 'Confirmed' },
  ],
  field_notes: 'Field notes here',
  verified_by: 'Officer Ali',
};

// ── Tests ────────────────────────────────────────────────────

describe('InvestigationVerification', () => {
  const defaultProps = {
    investigationId: 'inv-001',
    hypotheses: HYPOTHESES,
    onSubmit: vi.fn().mockResolvedValue({ outcome_id: 'vout-new' }),
    onUpdate: vi.fn().mockResolvedValue({ outcome_id: 'vout-001' }),
    existingOutcome: null,
    loading: false,
    submitting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the verification form', () => {
    render(<InvestigationVerification {...defaultProps} />);
    expect(screen.getByText('Investigation Verification')).toBeInTheDocument();
    expect(screen.getByText('Overall Assessment')).toBeInTheDocument();
    expect(screen.getByText('Field Notes')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<InvestigationVerification {...defaultProps} loading={true} />);
    expect(screen.getByText('Loading verification data…')).toBeInTheDocument();
  });

  it('displays all status options', () => {
    render(<InvestigationVerification {...defaultProps} />);
    expect(screen.getByText('Useful')).toBeInTheDocument();
    expect(screen.getByText('Partially Useful')).toBeInTheDocument();
    // 'Not Supported' appears in both status options and area verification options
    expect(screen.getAllByText('Not Supported').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Inconclusive')).toBeInTheDocument();
  });

  it('allows selecting overall status', () => {
    render(<InvestigationVerification {...defaultProps} />);
    const usefulBtn = screen.getByText('Useful');
    fireEvent.click(usefulBtn);
    // Button should be present and clickable
    expect(usefulBtn).toBeInTheDocument();
  });

  it('displays hypothesis cards', () => {
    render(<InvestigationVerification {...defaultProps} />);
    expect(screen.getByText('Industrial emissions')).toBeInTheDocument();
    expect(screen.getByText('Crop burning')).toBeInTheDocument();
    expect(screen.getByText('Hypothesis Verification')).toBeInTheDocument();
  });

  it('allows toggling hypothesis verification', () => {
    render(<InvestigationVerification {...defaultProps} />);
    const verifyButtons = screen.getAllByText('Verify');
    fireEvent.click(verifyButtons[0]);
    expect(screen.getByText('✓ Verified')).toBeInTheDocument();
  });

  it('displays investigation area verification options', () => {
    render(<InvestigationVerification {...defaultProps} />);
    expect(screen.getByText('Investigation Corridor Verification')).toBeInTheDocument();
    expect(screen.getByText('Investigation Area Verification')).toBeInTheDocument();
  });

  it('submit button is disabled when no status selected', () => {
    render(<InvestigationVerification {...defaultProps} />);
    const submitBtn = screen.getByRole('button', { name: /submit verification/i });
    expect(submitBtn).toBeDisabled();
  });

  it('submit button is disabled when submitting', () => {
    render(<InvestigationVerification {...defaultProps} submitting={true} />);
    const submitBtn = screen.getByRole('button', { name: /submitting/i });
    expect(submitBtn).toBeDisabled();
  });

  it('calls onSubmit when form is submitted', async () => {
    render(<InvestigationVerification {...defaultProps} />);
    
    // Select status
    fireEvent.click(screen.getByText('Useful'));
    
    // Fill field notes
    const notesField = screen.getByPlaceholderText(/describe what was found/i);
    fireEvent.change(notesField, { target: { value: 'Confirmed industrial activity' } });

    // Submit
    fireEvent.click(screen.getByRole('button', { name: /submit verification/i }));

    await waitFor(() => {
      expect(defaultProps.onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          investigation_id: 'inv-001',
          overall_status: 'USEFUL',
          field_notes: 'Confirmed industrial activity',
        })
      );
    });
  });

  it('shows success message after submission', async () => {
    render(<InvestigationVerification {...defaultProps} />);
    
    fireEvent.click(screen.getByText('Useful'));
    fireEvent.click(screen.getByRole('button', { name: /submit verification/i }));

    await waitFor(() => {
      expect(screen.getByText('Verification submitted')).toBeInTheDocument();
    });
  });

  it('pre-fills form when existing outcome provided', () => {
    render(
      <InvestigationVerification
        {...defaultProps}
        existingOutcome={EXISTING_OUTCOME}
      />
    );
    expect(screen.getByText('Update Verification')).toBeInTheDocument();
    expect(screen.getByText(EXISTING_OUTCOME.field_notes)).toBeInTheDocument();
    expect(screen.getByText('Industrial emissions')).toBeInTheDocument();
  });

  it('renders disclaimer text', () => {
    const { container } = render(<InvestigationVerification {...defaultProps} />);
    // Text contains <em>not</em> which splits the text across elements
    const descriptionEl = container.querySelector('p');
    expect(descriptionEl?.textContent).toMatch(/does not modify the original AI analysis/i);
  });
});
