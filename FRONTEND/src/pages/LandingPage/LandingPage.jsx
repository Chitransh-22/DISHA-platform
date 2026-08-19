import React from 'react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { LiveDisasterMap } from './components/LiveDisasterMap';
import { BottomActionCards } from './components/BottomActionCards';
import { Footer } from './components/Footer';

export const LandingPage = ({ currentPage, onNavigate }) => {
  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col selection:bg-orange-500 selection:text-white relative overflow-hidden">
      {/* Subtle Ambient Background Gradients & Grid Texture */}
      <div className="fixed inset-0 bg-grid-slate pointer-events-none opacity-50 z-0" />
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-275 h-112.5 bg-linear-to-b from-orange-500/8 via-amber-500/5 to-transparent blur-3xl pointer-events-none z-0 animate-float" />
      <div className="fixed bottom-10 right-0 w-125 h-125 bg-linear-to-tl from-orange-500/5 via-blue-500/5 to-transparent blur-3xl pointer-events-none z-0 animate-float-reverse" />
      
      {/* Top Navbar */}
      <Navbar currentPage={currentPage} onNavigate={onNavigate} />

      {/* Main Content */}
      <main className="flex-1 relative z-10">
        <HeroSection />

        {/* Live Disaster Map Section with Real OpenStreetMap GIS Mapping */}
        <LiveDisasterMap />

        {/* Bottom Action Cards */}
        <BottomActionCards onNavigate={onNavigate} />
      </main>

      {/* Footer */}
      <Footer onNavigate={onNavigate} />
    </div>
  );
};


