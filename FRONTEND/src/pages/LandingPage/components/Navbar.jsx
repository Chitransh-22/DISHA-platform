import React, { useState, useEffect } from 'react';
import { Map, AlertTriangle, Bell, User, Menu, X, ArrowRight } from 'lucide-react';
import { logoEmblemImg } from '../../../assets/images';

export const Navbar = ({ currentPage, onNavigate }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  // Scroll event listener to detect downward scroll
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
    <nav 
      className={`w-full sticky top-0 z-50 transition-all duration-500 ease-in-out ${
        isScrolled 
          ? 'pt-2 sm:pt-3 pb-2 bg-[#101318]/90 backdrop-blur-md shadow-2xl' 
          : 'pt-3 sm:pt-5 pb-2 bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-3 sm:px-6">
        {/* Main Dark Bar */}
        <div 
          className={`bg-[#101318]/95 backdrop-blur-lg text-white rounded-2xl sm:rounded-full px-4 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between transition-all duration-300 border border-white/10 ${
            isScrolled ? 'shadow-orange-950/20 shadow-2xl border-orange-500/20' : 'shadow-xl'
          }`}
        >
          {/* Brand Logo & Name */}
          <button 
            id="disha-brand-logo-btn"
            onClick={() => onNavigate('landing')}
            className="flex items-center gap-2 sm:gap-3 group focus:outline-none cursor-pointer"
          >
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-full overflow-hidden border border-white/20 p-0.5 bg-white shadow-md shrink-0 flex items-center justify-center transition-transform duration-300 group-hover:scale-105 group-hover:border-orange-500/50 group-hover:shadow-orange-500/20">
              <img 
                src={logoEmblemImg} 
                alt="DISHA Official Emblem" 
                className="w-full h-full object-contain rounded-full transition-transform duration-500 group-hover:rotate-6"
                referrerPolicy="no-referrer"
              />
            </div>
            
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 text-left">
              <span className="font-bold tracking-tight text-xl sm:text-2xl text-white font-sans leading-none group-hover:text-orange-400 transition-colors duration-300">
                DISHA
              </span>
              
              <span className="hidden min-[1000px]:inline-block max-[765px]:block border-l-0 min-[1000px]:border-l border-white/20 min-[1000px]:pl-2 text-[18px] max-[450px]:text-[12px] max-[450px]:leading-[1.1] leading-[1.2] text-slate-300 normal-case font-sans">
                <span className="text-[#f26522]">D</span>isaster <span className="text-[#f26522]">I</span>ntelligence and <br className="hidden min-[1000px]:inline" />
                <span className="text-[#f26522]">S</span>ituational <span className="text-[#f26522]">H</span>azard <span className="text-[#f26522]">A</span>wareness
              </span>
            </div>
          </button>

          {/* Desktop Navigation Items */}
          <div className="hidden md:flex items-center gap-2 lg:gap-4">
            
            {/* View Map Button */}
            <button
              id="nav-view-map-btn"
              onClick={() => onNavigate('map')}
              className={`group relative flex items-center gap-2 px-3.5 py-2 rounded-full text-sm font-medium transition-all duration-300 cursor-pointer overflow-hidden ${
                currentPage === 'map' ? 'text-orange-400 bg-white/5' : 'text-slate-200 hover:text-white'
              }`}
            >
              {/* Animated Hover Background Pill */}
              <span className="absolute inset-0 bg-linear-to-r from-orange-500/10 to-amber-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-full" />
              
              {/* Bottom Glowing Active/Hover Indicator */}
              <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-linear-to-r from-orange-500 to-amber-400 rounded-full transition-all duration-300 ${
                currentPage === 'map' ? 'w-3/4' : 'w-0 group-hover:w-3/4'
              }`} />

              <Map className="w-4 h-4 text-orange-400 transition-transform duration-300 group-hover:scale-125 group-hover:rotate-12" />
              <span className="relative z-10">View Map</span>
            </button>

            {/* Report Incident Button */}
            <button
              id="nav-report-incident-btn"
              onClick={() => onNavigate('report')}
              className={`group relative flex items-center gap-2 px-3.5 py-2 rounded-full text-sm font-medium transition-all duration-300 cursor-pointer overflow-hidden ${
                currentPage === 'report' ? 'text-orange-400 bg-white/5' : 'text-slate-200 hover:text-white'
              }`}
            >
              <span className="absolute inset-0 bg-linear-to-r from-red-500/10 to-orange-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-full" />
              
              <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-linear-to-r from-red-500 to-orange-400 rounded-full transition-all duration-300 ${
                currentPage === 'report' ? 'w-3/4' : 'w-0 group-hover:w-3/4'
              }`} />

              <AlertTriangle className="w-4 h-4 text-orange-500 transition-transform duration-300 group-hover:scale-125 group-hover:-rotate-12 group-hover:text-red-400" />
              <span className="relative z-10">Report Incident</span>
            </button>

            {/* Alerts Button */}
            <button
              id="nav-alerts-btn"
              onClick={() => onNavigate('alerts')}
              className={`group relative flex items-center gap-2 px-3.5 py-2 rounded-full text-sm font-medium transition-all duration-300 cursor-pointer overflow-hidden ${
                currentPage === 'alerts' ? 'text-orange-400 bg-white/5' : 'text-slate-200 hover:text-white'
              }`}
            >
              <span className="absolute inset-0 bg-linear-to-r from-orange-500/10 to-yellow-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-full" />
              
              <span className={`absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 bg-linear-to-r from-orange-500 to-amber-400 rounded-full transition-all duration-300 ${
                currentPage === 'alerts' ? 'w-3/4' : 'w-0 group-hover:w-3/4'
              }`} />

              <Bell className="w-4 h-4 text-orange-400 transition-transform duration-300 group-hover:scale-125 group-hover:rotate-12" />
              <span className="relative z-10">Alerts</span>

              {/* Pulsing Dot */}
              <span className="absolute top-2 right-2 flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500"></span>
              </span>
            </button>
          </div>

          {/* Sign In / Sign Up CTA Button */}
          <div className="hidden md:flex items-center">
            <button
              id="nav-auth-btn"
              onClick={() => onNavigate('auth')}
              className="group relative flex items-center gap-2 bg-linear-to-r from-[#f26522] to-[#ea580c] hover:from-[#ea580c] hover:to-[#c2410c] text-white font-semibold text-sm px-5 py-2.5 rounded-full transition-all duration-300 shadow-lg shadow-orange-950/40 hover:shadow-orange-500/30 hover:-translate-y-0.5 active:translate-y-0 active:scale-95 cursor-pointer overflow-hidden border border-orange-400/30"
            >
              {/* Shimmer effect across button on hover */}
              <span className="absolute inset-0 w-1/2 h-full bg-white/20 skew-x-12 -translate-x-full group-hover:translate-x-[300%] transition-transform duration-1000 ease-in-out" />

              <User className="w-4 h-4 transition-transform duration-300 group-hover:scale-110" />
              <span className="relative z-10">Sign In / Sign Up</span>
              <ArrowRight className="w-3.5 h-3.5 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300" />
            </button>
          </div>

          {/* Mobile Hamburger Toggle */}
          <div className="flex md:hidden items-center gap-2">
            <button
              id="nav-mobile-auth-btn"
              onClick={() => onNavigate('auth')}
              className="flex items-center gap-1.5 bg-[#f26522] hover:bg-[#ea580c] text-white text-xs font-semibold px-3 py-1.5 rounded-full cursor-pointer transition-transform active:scale-95 shadow-md shadow-orange-950/30"
            >
              <User className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
            <button
              id="mobile-menu-toggle-btn"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 text-slate-300 hover:text-white hover:bg-white/10 rounded-lg focus:outline-none cursor-pointer transition-colors duration-200"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Drawer Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden mt-2 bg-[#101318]/95 backdrop-blur-xl text-white rounded-2xl p-4 shadow-2xl border border-white/10 flex flex-col gap-2 animate-in fade-in slide-in-from-top-2 duration-300">
            <button
              id="mobile-nav-map-btn"
              onClick={() => {
                onNavigate('map');
                setMobileMenuOpen(false);
              }}
              className="group flex items-center gap-3 px-3.5 py-3 rounded-xl hover:bg-white/10 text-left text-sm font-medium text-slate-200 hover:text-orange-400 cursor-pointer transition-all duration-200"
            >
              <Map className="w-4 h-4 text-orange-400 transition-transform duration-200 group-hover:scale-110" />
              <span>View Map</span>
            </button>

            <button
              id="mobile-nav-report-btn"
              onClick={() => {
                onNavigate('report');
                setMobileMenuOpen(false);
              }}
              className="group flex items-center gap-3 px-3.5 py-3 rounded-xl hover:bg-white/10 text-left text-sm font-medium text-slate-200 hover:text-orange-400 cursor-pointer transition-all duration-200"
            >
              <AlertTriangle className="w-4 h-4 text-orange-500 transition-transform duration-200 group-hover:scale-110" />
              <span>Report Incident</span>
            </button>

            <button
              id="mobile-nav-alerts-btn"
              onClick={() => {
                onNavigate('alerts');
                setMobileMenuOpen(false);
              }}
              className="group flex items-center gap-3 px-3.5 py-3 rounded-xl hover:bg-white/10 text-left text-sm font-medium text-slate-200 hover:text-orange-400 justify-between cursor-pointer transition-all duration-200"
            >
              <div className="flex items-center gap-3">
                <Bell className="w-4 h-4 text-orange-400 transition-transform duration-200 group-hover:scale-110" />
                <span>Alerts</span>
              </div>
              <span className="bg-orange-500/20 text-orange-400 text-xs font-semibold px-2 py-0.5 rounded-full border border-orange-500/30">
                3 Live
              </span>
            </button>

            <button
              id="mobile-nav-auth-full-btn"
              onClick={() => {
                onNavigate('auth');
                setMobileMenuOpen(false);
              }}
              className="flex items-center justify-center gap-2 bg-linear-to-r from-[#f26522] to-[#ea580c] active:scale-[0.98] text-white font-semibold text-sm py-3 rounded-xl mt-2 cursor-pointer shadow-lg shadow-orange-950/40 transition-all duration-200"
            >
              <User className="w-4 h-4" />
              <span>Sign In / Sign Up</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  );
};