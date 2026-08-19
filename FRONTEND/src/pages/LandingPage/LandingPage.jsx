import React from 'react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { LiveDisasterMap } from './components/LiveDisasterMap';
import { BottomActionCards } from './components/BottomActionCards';
import { Footer } from './components/Footer';

export const LandingPage = ({ currentPage, onNavigate }) => {
  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col selection:bg-orange-500 selection:text-white">
      {/* Top Navbar */}
      <Navbar currentPage={currentPage} onNavigate={onNavigate} />

      {/* Main Content */}
      <main className="flex-1">
        <HeroSection />

        {/* Live Disaster Map Section with Realistic GIS Mapping */}
        <LiveDisasterMap />

        {/* Bottom Action Cards */}
        <BottomActionCards onNavigate={onNavigate} />
      </main>

      {/* Footer */}
      <Footer onNavigate={onNavigate} />
    </div>
  );
};
