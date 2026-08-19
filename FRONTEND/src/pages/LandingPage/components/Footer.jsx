import React from 'react';
import { ShieldCheck, Phone, Radio, ExternalLink, Lock } from 'lucide-react';
import { logoEmblemImg } from '../../../assets/images';

export const Footer = ({ onNavigate }) => {
  return (
    <footer className="w-full border-t border-slate-200/80 bg-[#0b0f17] text-slate-400 pt-12 pb-8 px-4 sm:px-6 relative z-10">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8 text-xs sm:text-sm">
        
        {/* Left Branding */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-2xl overflow-hidden bg-white p-1 border border-white/20 shadow-md shrink-0 flex items-center justify-center">
            <img src={logoEmblemImg} alt="DISHA Emblem" className="w-full h-full object-contain rounded-full" referrerPolicy="no-referrer" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-white tracking-tight text-lg font-sans">DISHA</span>
              <span className="text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30">
                OFFICIAL PORTAL
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">National Disaster Intelligence & Hazard Awareness</p>
          </div>
        </div>

        {/* Quick Nav Links */}
        <div className="flex flex-wrap items-center justify-center gap-6 font-medium text-slate-300">
          <button 
            onClick={() => onNavigate('landing')} 
            className="hover:text-orange-400 transition-colors cursor-pointer text-xs sm:text-sm"
          >
            Home
          </button>
          <button 
            onClick={() => onNavigate('map')} 
            className="hover:text-orange-400 transition-colors cursor-pointer text-xs sm:text-sm"
          >
            Live Map
          </button>
          <button 
            onClick={() => onNavigate('report')} 
            className="hover:text-orange-400 transition-colors cursor-pointer text-xs sm:text-sm"
          >
            Report Incident
          </button>
          <button 
            onClick={() => onNavigate('alerts')} 
            className="hover:text-orange-400 transition-colors cursor-pointer text-xs sm:text-sm"
          >
            Alerts
          </button>
          <button 
            onClick={() => onNavigate('nearby')} 
            className="hover:text-orange-400 transition-colors cursor-pointer text-xs sm:text-sm"
          >
            Nearby Incidents
          </button>
        </div>

        {/* Emergency Helplines Pill */}
        <div className="flex items-center gap-3 bg-white/5 border border-white/15 px-4 py-2 rounded-2xl shadow-inner">
          <div className="w-7 h-7 rounded-xl bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-400">
            <Phone className="w-3.5 h-3.5" />
          </div>
          <div className="text-left">
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Emergency Helplines</div>
            <div className="text-xs font-bold text-white font-mono">
              <a href="tel:1070" className="hover:text-orange-400 transition-colors">1070</a> / <a href="tel:112" className="hover:text-orange-400 transition-colors">112</a> (NDRF)
            </div>
          </div>
        </div>

      </div>

      {/* Bottom Legal & Integration Bar */}
      <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-white/10 text-center text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-3">
        <p className="text-slate-400 font-normal">
          © 2026 DISHA - Disaster Intelligence and Situational Hazard Awareness. All rights reserved.
        </p>
        <div className="flex items-center gap-4 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Integrated with National Disaster Management Network</span>
          </span>
        </div>
      </div>
    </footer>
  );
};

