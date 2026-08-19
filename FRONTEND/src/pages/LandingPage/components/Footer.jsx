import React from 'react';
import { Shield, Phone } from 'lucide-react';
import { logoEmblemImg } from '../../../assets/images';

export const Footer = ({ onNavigate }) => {
  return (
    <footer className="w-full border-t border-slate-300/60 bg-[#eae4d8]/60 pt-10 pb-8 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-slate-600 text-xs sm:text-sm">
        
        {/* Left Branding */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full overflow-hidden bg-white border border-slate-300 shadow-sm p-0.5 flex items-center justify-center">
            <img src={logoEmblemImg} alt="DISHA" className="w-full h-full object-contain rounded-full" referrerPolicy="no-referrer" />
          </div>
          <div>
            <span className="font-bold text-slate-900 tracking-tight text-base font-sans">DISHA</span>
            <p className="text-[11px] text-slate-500">National Disaster Intelligence & Awareness Platform</p>
          </div>
        </div>

        {/* Quick Nav Links */}
        <div className="flex flex-wrap items-center justify-center gap-5 font-medium">
          <button 
            onClick={() => onNavigate('landing')} 
            className="hover:text-orange-600 transition-colors cursor-pointer"
          >
            Home
          </button>
          <button 
            onClick={() => onNavigate('map')} 
            className="hover:text-orange-600 transition-colors cursor-pointer"
          >
            Live Map
          </button>
          <button 
            onClick={() => onNavigate('report')} 
            className="hover:text-orange-600 transition-colors cursor-pointer"
          >
            Report Incident
          </button>
          <button 
            onClick={() => onNavigate('alerts')} 
            className="hover:text-orange-600 transition-colors cursor-pointer"
          >
            Alerts
          </button>
          <button 
            onClick={() => onNavigate('nearby')} 
            className="hover:text-orange-600 transition-colors cursor-pointer"
          >
            Nearby Incidents
          </button>
        </div>

        {/* Helplines Pill */}
        <div className="flex items-center gap-3 bg-white/80 border border-slate-300/80 px-3.5 py-1.5 rounded-full shadow-xs">
          <Phone className="w-3.5 h-3.5 text-orange-600" />
          <span className="text-xs font-semibold text-slate-700">NDRF Emergency: 1070 / 112</span>
        </div>

      </div>

      <div className="max-w-7xl mx-auto mt-6 pt-4 border-t border-slate-300/40 text-center text-[11px] text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
        <p>© 2026 DISHA - Disaster Intelligence and Situational Hazard Awareness. All rights reserved.</p>
        <p className="flex items-center gap-1">
          <Shield className="w-3 h-3 text-orange-500" />
          <span>Integrated with National Disaster Management Network</span>
        </p>
      </div>
    </footer>
  );
};
