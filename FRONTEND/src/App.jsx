import React, { useState, useEffect } from 'react';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { ViewMapPage } from './pages/ViewMapPage';
import { ReportIncidentPage } from './pages/ReportIncidentPage';
import { AlertsPage } from './pages/AlertsPage';
import { AuthPage } from './pages/AuthPage';
import { NearbyIncidentsPage } from './pages/NearbyIncidentsPage';
import { AnalysisPage } from './pages/AnalysisPage/AnalysisPage';
import { GraphsAnalyticsPage } from './pages/AnalysisPage/GraphsAnalyticsPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [redirectAfterAuth, setRedirectAfterAuth] = useState(null);
  const { user, isLoggedIn, logout } = useAuth();

  // If user arrives directly on an auth callback route
  useEffect(() => {
    if (window.location.pathname.startsWith('/auth/google/success')) {
      let target = 'landing';
      try {
        const savedRedirect = sessionStorage.getItem('disha_auth_redirect');
        if (savedRedirect) {
          sessionStorage.removeItem('disha_auth_redirect');
          target = savedRedirect;
        }
      } catch (e) {}
      setCurrentPage(target);
    }
  }, []);

  const handleNavigate = (page, redirectTarget = null) => {
    if (redirectTarget) {
      setRedirectAfterAuth(redirectTarget);
    }
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLoginSuccess = () => {
    if (redirectAfterAuth) {
      const target = redirectAfterAuth;
      setRedirectAfterAuth(null);
      setCurrentPage(target);
    } else {
      setCurrentPage('landing');
    }
  };

  const handleLogout = async () => {
    await logout();
    setCurrentPage('landing');
  };

  const renderContent = () => {
    switch (currentPage) {
      case 'map':
        return <ViewMapPage onNavigate={handleNavigate} />;
      case 'report':
        return <ReportIncidentPage onNavigate={handleNavigate} isLoggedIn={isLoggedIn} />;
      case 'alerts':
        return <AlertsPage onNavigate={handleNavigate} />;
      case 'analysis':
        return <AnalysisPage currentPage={currentPage} onNavigate={handleNavigate} />;
      case 'graphs':
        return <GraphsAnalyticsPage onNavigate={handleNavigate} />;
      case 'auth':
        return (
          <AuthPage
            onNavigate={handleNavigate}
            onLoginSuccess={handleLoginSuccess}
            redirectTarget={redirectAfterAuth}
          />
        );
      case 'nearby':
        return <NearbyIncidentsPage onNavigate={handleNavigate} />;
      case 'landing':
      default:
        return (
          <LandingPage
            currentPage={currentPage}
            onNavigate={handleNavigate}
            isLoggedIn={isLoggedIn}
            currentUser={user}
            onLogout={handleLogout}
          />
        );
    }
  };

  return (
    <ErrorBoundary title="DISHA Application Error">
      {renderContent()}
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
