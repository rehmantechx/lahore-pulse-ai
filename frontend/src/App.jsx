import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { DemoModeProvider } from './demo';
import { AuthProvider } from './contexts/AuthContext.jsx';
import ErrorBoundary from './components/common/ErrorBoundary.jsx';
import PageTransition from './components/common/PageTransition.jsx';

/* Shell Layouts */
import PublicShell from './components/layout/PublicShell.jsx';
import GovernmentShell from './components/layout/GovernmentShell.jsx';

/* Auth */
import ProtectedRoute from './components/auth/ProtectedRoute.jsx';
import LoginPage from './pages/LoginPage.jsx';

/* Landing */
import LandingPage from './pages/LandingPage.jsx';

/* Public Pages */
import HomePage from './pages/HomePage.jsx';
import AirQualityPage from './pages/AirQualityPage.jsx';
import CityMapPage from './pages/CityMapPage.jsx';
import AlertsPage from './pages/AlertsPage.jsx';
import InsightsPage from './pages/InsightsPage.jsx';
import ReportPage from './pages/ReportPage.jsx';
import MyLahorePage from './pages/MyLahorePage.jsx';
import DataTrustPage from './pages/DataTrustPage.jsx';
import Dashboard from './pages/Dashboard.jsx';

/* Government Pages */
import GovCommandCenter from './pages/GovCommandCenter.jsx';
import GovIncidentsPage from './pages/GovIncidentsPage.jsx';
import GovForecastsPage from './pages/GovForecastsPage.jsx';
import GovAnalyticsPage from './pages/GovAnalyticsPage.jsx';
import GovInvestigationsPage from './pages/GovInvestigationsPage.jsx';
import GovReportsPage from './pages/GovReportsPage.jsx';
import GovSystemPage from './pages/GovSystemPage.jsx';
import ReplayView from './pages/ReplayView';

import './styles/index.css';
import './styles/motion.css';
import './styles/receipt.css';

function NotFound() {
  return (
    <div className="app app--public">
      <main className="app-content" role="main" style={{ textAlign: 'center', paddingTop: 'var(--sp-12)' }}>
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--lp-text-primary)', marginBottom: 'var(--sp-3)' }}>
          Page not found
        </h1>
        <p style={{ color: 'var(--lp-text-tertiary)', marginBottom: 'var(--sp-4)' }}>
          The requested page does not exist.
        </p>
        <a href="/" className="btn btn--primary">Go to Home</a>
      </main>
    </div>
  );
}

function AppRoutes() {
  const location = useLocation();
  const transitionKey = location.pathname + location.search;

  // Scroll to top on route change
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <Routes location={location}>
      {/* ── Landing Page ─────────────────────────────── */}
      <Route path="/" element={
        <PageTransition key={transitionKey}><LandingPage /></PageTransition>
      } />

      {/* ── Citizen Routes ───────────────────────────── */}
      <Route element={<PublicShell />}>
        <Route path="/citizen" element={<Dashboard />} />
        <Route path="/air-quality" element={<AirQualityPage />} />
        <Route path="/city-map" element={<CityMapPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/reports" element={<ReportPage />} />
        <Route path="/my-lahore" element={<MyLahorePage />} />
        <Route path="/data-trust" element={<DataTrustPage />} />
      </Route>

      {/* ── Legacy Redirects ─────────────────────────── */}
      <Route path="/dashboard" element={<Navigate to="/citizen" replace />} />
      <Route path="/citizen/*" element={<Navigate to="/citizen" replace />} />

      {/* ── Login ─────────────────────────────────────── */}
      <Route path="/login" element={
        <PageTransition key={transitionKey}><LoginPage /></PageTransition>
      } />

      {/* ── Government Routes (protected) ────────────── */}
      <Route element={<ProtectedRoute><GovernmentShell /></ProtectedRoute>}>
        <Route path="/government" element={<GovCommandCenter />} />
        <Route path="/government/incidents" element={<GovIncidentsPage />} />
        <Route path="/government/forecasts" element={<GovForecastsPage />} />
        <Route path="/government/analytics" element={<GovAnalyticsPage />} />
        <Route path="/government/investigations" element={<GovInvestigationsPage />} />
        <Route path="/government/reports" element={<GovReportsPage />} />
        <Route path="/government/replay" element={<ReplayView />} />
      </Route>

      {/* ── Government Routes — Admin Only ──────────── */}
      <Route element={<ProtectedRoute requiredRole="admin"><GovernmentShell /></ProtectedRoute>}>
        <Route path="/government/system" element={<GovSystemPage />} />
      </Route>

      {/* ── Legacy Routes ────────────────────────────── */}
      <Route path="/replay" element={<Navigate to="/government/replay" replace />} />

      {/* ── 404 ──────────────────────────────────────── */}
      <Route path="*" element={
        <PageTransition key={transitionKey}><NotFound /></PageTransition>
      } />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <DemoModeProvider>
      <AuthProvider>
        <ErrorBoundary fallbackTitle="Lahore+ encountered an unexpected error" fallbackMessage="Please refresh the page to continue.">
          <AppRoutes />
        </ErrorBoundary>
      </AuthProvider>
      </DemoModeProvider>
    </BrowserRouter>
  );
}
