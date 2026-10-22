import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AdminRoute } from './components/layout/AdminRoute';

import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { CompanyProfilePage } from './pages/company/CompanyProfilePage';
import { DocumentVaultPage } from './pages/vault/DocumentVaultPage';
import { TendersListPage } from './pages/tenders/TendersListPage';
import { TenderDetailPage } from './pages/tenders/TenderDetailPage';
import { ApplicationsPage } from './pages/applications/ApplicationsPage';
import { ComplianceAnalysisPage } from './pages/compliance/ComplianceAnalysisPage';
import { ComplianceReportsListPage } from './pages/compliance/ComplianceReportsListPage';
import { ComplianceReportDetailPage } from './pages/compliance/ComplianceReportDetailPage';
import { AdminTendersPage } from './pages/admin/AdminTendersPage';
import { AdminTenderFormPage } from './pages/admin/AdminTenderFormPage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/company" element={<CompanyProfilePage />} />
            <Route path="/vault" element={<DocumentVaultPage />} />
            <Route path="/tenders" element={<TendersListPage />} />
            <Route path="/tenders/:tenderId" element={<TenderDetailPage />} />
            <Route path="/applications" element={<ApplicationsPage />} />
            <Route path="/compliance/analyze" element={<ComplianceAnalysisPage />} />
            <Route path="/compliance/reports" element={<ComplianceReportsListPage />} />
            <Route path="/compliance/reports/:reportId" element={<ComplianceReportDetailPage />} />

            {/* Admin Only Routes */}
            <Route
              path="/admin/tenders"
              element={
                <AdminRoute>
                  <AdminTendersPage />
                </AdminRoute>
              }
            />
            <Route
              path="/admin/tenders/new"
              element={
                <AdminRoute>
                  <AdminTenderFormPage />
                </AdminRoute>
              }
            />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
