import React, { useState } from 'react';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { ViewMapPage } from './pages/ViewMapPage';
import { ReportIncidentPage } from './pages/ReportIncidentPage';
import { AlertsPage } from './pages/AlertsPage';
import { AuthPage } from './pages/AuthPage';
import { NearbyIncidentsPage } from './pages/NearbyIncidentsPage';

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing');
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const handleNavigate = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
  };

  switch (currentPage) {
    case 'map':
      return <ViewMapPage onNavigate={handleNavigate} />;
    case 'report':
      return <ReportIncidentPage onNavigate={handleNavigate} isLoggedIn={isLoggedIn} />;
    case 'alerts':
      return <AlertsPage onNavigate={handleNavigate} />;
    case 'auth':
      return <AuthPage onNavigate={handleNavigate} onLoginSuccess={handleLoginSuccess} />;
    case 'nearby':
      return <NearbyIncidentsPage onNavigate={handleNavigate} />;
    case 'landing':
    default:
      return <LandingPage currentPage={currentPage} onNavigate={handleNavigate} />;
  }
}
