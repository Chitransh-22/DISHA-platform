import React, { useState } from 'react';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { ViewMapPage } from './pages/ViewMapPage';
import { ReportIncidentPage } from './pages/ReportIncidentPage';
import { AlertsPage } from './pages/AlertsPage';
import { AuthPage } from './pages/AuthPage';
import { NearbyIncidentsPage } from './pages/NearbyIncidentsPage';

export default function App() {
  const [currentPage, setCurrentPage] = useState('landing');

  const handleNavigate = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  switch (currentPage) {
    case 'map':
      return <ViewMapPage onNavigate={handleNavigate} />;
    case 'report':
      return <ReportIncidentPage onNavigate={handleNavigate} />;
    case 'alerts':
      return <AlertsPage onNavigate={handleNavigate} />;
    case 'auth':
      return <AuthPage onNavigate={handleNavigate} />;
    case 'nearby':
      return <NearbyIncidentsPage onNavigate={handleNavigate} />;
    case 'landing':
    default:
      return <LandingPage currentPage={currentPage} onNavigate={handleNavigate} />;
  }
}
