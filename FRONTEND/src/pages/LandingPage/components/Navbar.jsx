import React, { useState, useEffect } from 'react';
import { Map, AlertTriangle, Bell, User, Menu, X, ArrowRight, ShieldCheck } from 'lucide-react';
import { logoEmblemImg } from '../../../assets/images';

export const Navbar = ({ currentPage, onNavigate }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  // Scroll event listener to adapt navbar styling on scroll
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header 
      className={`w-full sticky top-0 z-50 transition-all duration-300 ease-out ${
        isScrolled 
          ? 'py-2.5 bg-[#0a0e17]/90 backdrop-blur-xl shadow-2xl shadow-black/30 border-b border-white/10' 
          : 'py-3.5 sm:py-5 bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-3 sm:px-6">
        {/* Main Command Bar Container */}
        <div 
          className={`bg-[#0b0f17]/95 backdrop-blur-2xl text-white rounded-2xl sm:rounded-full px-3.5 sm:px-6 py-2 sm:py-2.5 flex items-center justify-between transition-all duration-300 border ${
            isScrolled 
              ? 'border-white/10 shadow-lg shadow-black/40' 
              : 'border-white/15 shadow-2xl shadow-slate-900/10'
          }`}
        >
          {/* Brand Logo & Name */}
          <button 
            id="disha-brand-logo-btn"
            onClick={() => onNavigate('landing')}
            className="flex items-center gap-2.5 sm:gap-3.5 group focus:outline-none cursor-pointer text-left"
          >
            {/* Emblem with Command Bezel */}
            <div className="relative w-10 h-10 sm:w-11 sm:h-11 rounded-full p-0.5 bg-gradient-to-br from-orange-500/80 via-white/20 to-amber-500/50 shadow-md shrink-0 flex items-center justify-center transition-all duration-300 group-hover:scale-105 group-hover:shadow-orange-500/25">
              <div className="w-full h-full rounded-full bg-white p-0.5 overflow-hidden flex items-center justify-center">
                <img 
                  src={logoEmblemImg} 
                  alt="DISHA Official Emblem" 
                  className="w-full h-full object-contain rounded-full transition-transform duration-500 group-hover:scale-110"
                  referrerPolicy="no-referrer"
                />
              </div>
            </div>
            
            {/* Title & Acronym */}
            <div className="flex flex-col text-left">
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-tight text-xl sm:text-2xl text-white font-sans leading-none group-hover:text-orange-400 transition-colors duration-300">
                  DISHA
                </span>
                <span className="hidden xl:inline-flex items-center gap-1 text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-full bg-orange-500/15 text-orange-400 border border-orange-500/30">
                  <ShieldCheck className="w-3 h-3" />
                  <span>National Intel</span>
                </span>
              </div>
              
              <span className="hidden min-[960px]:inline-block text-[11px] lg:text-[12px] leading-tight text-slate-300 font-medium tracking-normal mt-0.5">
                <span className="text-orange-400 font-bold">D</span>isaster <span className="text-orange-400 font-bold">I</span>ntelligence & <span className="text-orange-400 font-bold">S</span>ituational <span className="text-orange-400 font-bold">H</span>azard <span className="text-orange-400 font-bold">A</span>wareness
              </span>
            </div>
          </button>

          {/* Desktop Navigation Items */}
          <div className="hidden md:flex items-center gap-1.5 lg:gap-2">
            
            {/* View Map Button */}
            <button
              id="nav-view-map-btn"
              onClick={() => onNavigate('map')}
              className={`relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 cursor-pointer overflow-hidden ${
                currentPage === 'map' 
                  ? 'text-white bg-white/10 shadow-inner' 
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <Map className={`w-4 h-4 transition-transform duration-200 ${currentPage === 'map' ? 'text-orange-400 scale-110' : 'text-slate-400 group-hover:text-orange-400'}`} />
              <span>View Map</span>
              {currentPage === 'map' && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1/2 h-0.5 bg-orange-500 rounded-full shadow-[0_0_8px_rgba(249,115,22,0.8)]" />
              )}
            </button>

            {/* Report Incident Button */}
            <button
              id="nav-report-incident-btn"
              onClick={() => onNavigate('report')}
              className={`relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 cursor-pointer overflow-hidden ${
                currentPage === 'report' 
                  ? 'text-white bg-white/10 shadow-inner' 
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <AlertTriangle className={`w-4 h-4 transition-transform duration-200 ${currentPage === 'report' ? 'text-orange-400 scale-110' : 'text-amber-400 group-hover:text-amber-300'}`} />
              <span>Report Incident</span>
              {currentPage === 'report' && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1/2 h-0.5 bg-orange-500 rounded-full shadow-[0_0_8px_rgba(249,115,22,0.8)]" />
              )}
            </button>

            {/* Alerts Button */}
            <button
              id="nav-alerts-btn"
              onClick={() => onNavigate('alerts')}
              className={`relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 cursor-pointer overflow-hidden ${
                currentPage === 'alerts' 
                  ? 'text-white bg-white/10 shadow-inner' 
                  : 'text-slate-300 hover:text-white hover:bg-white/5'
              }`}
            >
              <Bell className={`w-4 h-4 transition-transform duration-200 ${currentPage === 'alerts' ? 'text-orange-400 scale-110' : 'text-slate-400 group-hover:text-orange-400'}`} />
              <span>Alerts</span>
              
              {/* Pulsing Live Alert Indicator */}
              <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/40 ml-0.5">
                <span className="relative flex h-1.5 w-1.5 mr-1">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-orange-500"></span>
                </span>
                3
              </span>
              
              {currentPage === 'alerts' && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1/2 h-0.5 bg-orange-500 rounded-full shadow-[0_0_8px_rgba(249,115,22,0.8)]" />
              )}
            </button>
          </div>

          {/* Sign In / Sign Up CTA Button */}
          <div className="hidden md:flex items-center">
            <button
              id="nav-auth-btn"
              onClick={() => onNavigate('auth')}
              className="group relative flex items-center gap-2 bg-gradient-to-r from-orange-600 via-orange-500 to-amber-500 hover:from-orange-500 hover:to-amber-500 text-white font-semibold text-sm px-5 py-2.5 rounded-full transition-all duration-200 shadow-md shadow-orange-950/40 hover:shadow-lg hover:shadow-orange-500/25 hover:-translate-y-0.5 active:translate-y-0 active:scale-95 cursor-pointer overflow-hidden border border-orange-400/40"
            >
              {/* Shimmer reflection */}
              <span className="absolute inset-0 w-1/2 h-full bg-white/20 skew-x-12 -translate-x-full group-hover:translate-x-[300%] transition-transform duration-700 ease-in-out pointer-events-none" />

              <User className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
              <span className="relative z-10">Sign In / Sign Up</span>
              <ArrowRight className="w-3.5 h-3.5 opacity-70 -translate-x-0.5 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
            </button>
          </div>

          {/* Mobile Hamburger Toggle & Fast Auth */}
          <div className="flex md:hidden items-center gap-2">
            <button
              id="nav-mobile-auth-btn"
              onClick={() => onNavigate('auth')}
              className="flex items-center gap-1.5 bg-gradient-to-r from-orange-600 to-amber-500 text-white text-xs font-semibold px-3 py-1.5 rounded-full cursor-pointer transition-transform active:scale-95 shadow-md shadow-orange-950/30 border border-orange-400/30"
            >
              <User className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
            <button
              id="mobile-menu-toggle-btn"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-300 hover:text-white hover:bg-white/10 rounded-xl focus:outline-none cursor-pointer transition-colors duration-200 border border-white/10"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Drawer Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden mt-2 bg-[#0b0f17]/95 backdrop-blur-2xl text-white rounded-2xl p-4 shadow-2xl border border-white/15 flex flex-col gap-1.5 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-white/10 mb-1">
              <span>Command Navigation</span>
              <span className="flex items-center gap-1 text-emerald-400 font-mono text-[11px]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                ONLINE
              </span>
            </div>

            <button
              id="mobile-nav-map-btn"
              onClick={() => {
                onNavigate('map');
                setMobileMenuOpen(false);
              }}
              className={`group flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-left text-sm font-medium cursor-pointer transition-all duration-200 ${
                currentPage === 'map' ? 'bg-white/10 text-orange-400' : 'text-slate-200 hover:bg-white/5 hover:text-white'
              }`}
            >
              <div className="w-7 h-7 rounded-lg bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-orange-400">
                <Map className="w-4 h-4" />
              </div>
              <span>View Map</span>
            </button>

            <button
              id="mobile-nav-report-btn"
              onClick={() => {
                onNavigate('report');
                setMobileMenuOpen(false);
              }}
              className={`group flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-left text-sm font-medium cursor-pointer transition-all duration-200 ${
                currentPage === 'report' ? 'bg-white/10 text-orange-400' : 'text-slate-200 hover:bg-white/5 hover:text-white'
              }`}
            >
              <div className="w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <span>Report Incident</span>
            </button>

            <button
              id="mobile-nav-alerts-btn"
              onClick={() => {
                onNavigate('alerts');
                setMobileMenuOpen(false);
              }}
              className={`group flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left text-sm font-medium cursor-pointer transition-all duration-200 ${
                currentPage === 'alerts' ? 'bg-white/10 text-orange-400' : 'text-slate-200 hover:bg-white/5 hover:text-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-orange-400">
                  <Bell className="w-4 h-4" />
                </div>
                <span>Alerts</span>
              </div>
              <span className="bg-orange-500/20 text-orange-400 text-xs font-bold px-2 py-0.5 rounded-full border border-orange-500/30">
                3 Live
              </span>
            </button>

            <div className="pt-2 border-t border-white/10 mt-1">
              <button
                id="mobile-nav-auth-full-btn"
                onClick={() => {
                  onNavigate('auth');
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-orange-600 via-orange-500 to-amber-500 active:scale-[0.98] text-white font-semibold text-sm py-3 rounded-xl cursor-pointer shadow-lg shadow-orange-950/40 transition-all duration-200 border border-orange-400/30"
              >
                <User className="w-4 h-4" />
                <span>Sign In / Sign Up</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};