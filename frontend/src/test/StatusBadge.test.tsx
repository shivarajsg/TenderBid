import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/common/StatusBadge';

describe('StatusBadge Component', () => {
  it('renders PASS finding status with emerald styling', () => {
    render(<StatusBadge status="PASS" />);
    const badge = screen.getByTestId('status-badge-pass');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('PASS');
    expect(badge.className).toContain('emerald');
  });

  it('renders FAIL finding status with rose/red styling', () => {
    render(<StatusBadge status="FAIL" isMandatory={false} />);
    const badge = screen.getByTestId('status-badge-fail');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('FAIL');
    expect(badge.className).toContain('rose');
  });

  it('renders FAIL (Mandatory) when isMandatory is true', () => {
    render(<StatusBadge status="FAIL" isMandatory={true} />);
    const badge = screen.getByTestId('status-badge-fail');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('FAIL (Mandatory)');
    expect(badge.className).toContain('rose');
  });

  it('renders MISSING_EVIDENCE as MISSING PROOF and never as PASS', () => {
    render(<StatusBadge status="MISSING_EVIDENCE" isMandatory={true} />);
    const badge = screen.getByTestId('status-badge-missing_evidence');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('MISSING PROOF (Mandatory)');
    expect(badge.className).toContain('amber');
    expect(badge).not.toHaveTextContent('PASS');
  });

  it('renders Overall ELIGIBLE status', () => {
    render(<StatusBadge status="ELIGIBLE" />);
    const badge = screen.getByTestId('status-badge-eligible');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('ELIGIBLE');
    expect(badge.className).toContain('emerald');
  });

  it('renders Overall PARTIALLY_ELIGIBLE status with amber warning', () => {
    render(<StatusBadge status="PARTIALLY_ELIGIBLE" />);
    const badge = screen.getByTestId('status-badge-partially_eligible');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('PARTIALLY ELIGIBLE');
    expect(badge.className).toContain('amber');
  });

  it('renders Overall NOT_ELIGIBLE status with rose styling', () => {
    render(<StatusBadge status="NOT_ELIGIBLE" />);
    const badge = screen.getByTestId('status-badge-not_eligible');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('NOT ELIGIBLE');
    expect(badge.className).toContain('rose');
  });
});
