import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from '../components/common/Navbar';
import { Sidebar } from '../components/layout/Sidebar';
import * as AuthContextModule from '../context/AuthContext';
import { tokenStorage } from '../api/client';

describe('Frontend End-to-End User Journeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('renders MSME navigation links and restricts admin links for MSME user', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 'user-msme-1',
        email: 'msme@engineering.in',
        full_name: 'Priya Sharma',
        role: 'MSME_USER',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAuthenticated: true,
      isAdmin: false,
      loading: false,
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      clearError: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // MSME links present
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Find Tenders')).toBeInTheDocument();
    expect(screen.getByText('Evaluate Tender')).toBeInTheDocument();
    expect(screen.getByText('Document Vault')).toBeInTheDocument();
    expect(screen.getByText('Company Profile')).toBeInTheDocument();

    // Admin links hidden
    expect(screen.queryByText('Manage Tenders')).not.toBeInTheDocument();
    expect(screen.queryByText('Create New Tender')).not.toBeInTheDocument();
  });

  it('renders admin console navigation links for ADMIN user', () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: {
        id: 'user-admin-1',
        email: 'admin@platform.gov.in',
        full_name: 'Gov Administrator',
        role: 'ADMIN',
        is_active: true,
        created_at: new Date().toISOString(),
      },
      isAuthenticated: true,
      isAdmin: true,
      loading: false,
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      clearError: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    // Admin links visible
    expect(screen.getByText('Manage Tenders')).toBeInTheDocument();
    expect(screen.getByText('Create New Tender')).toBeInTheDocument();
    expect(screen.getByText('PRIVILEGED')).toBeInTheDocument();
  });

  it('handles token storage and logout securely', () => {
    tokenStorage.set('test-jwt-token-xyz');
    expect(tokenStorage.get()).toBe('test-jwt-token-xyz');

    tokenStorage.clear();
    expect(tokenStorage.get()).toBeNull();
  });
});
