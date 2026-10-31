import React from 'react';
import { Home, Map, Newspaper, AlertTriangle, Bell, User } from 'lucide-react';

export const MobileBottomNav = ({ currentPage, onNavigate, isLoggedIn = false }) => {
  const handleTabClick = (target) => {
    if (target === 'map') {
      if (currentPage === 'landing') {
        const mapEl = document.getElementById('disha-live-map-section');
        if (mapEl) {
          mapEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
          window.scrollTo({ top: 350, behavior: 'smooth' });
        }
      } else {
        onNavigate('landing', { scrollToMap: true });
      }
      return;
    }

    if (target === 'home') {
      if (currentPage === 'landing') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        onNavigate('landing');
      }
      return;
    }

    onNavigate(target);
  };

  const isHomeActive = currentPage === 'landing';
  const isNewsActive = currentPage === 'news' || currentPage === 'news-detail';
  const isReportActive = currentPage === 'report';
  const isAlertsActive = currentPage === 'alerts';

  const navItems = [
    {
      id: 'home',
      label: 'Home',
      icon: Home,
      isActive: isHomeActive,
    },
    {
      id: 'map',
      label: 'Live Map',
      icon: Map,
      isActive: false, // Map is a fast-jump action
    },
    {
      id: 'news',
      label: 'News',
      icon: Newspaper,
      isActive: isNewsActive,
    },
    {
      id: 'report',
      label: 'Report',
      icon: AlertTriangle,
      isActive: isReportActive,
      highlight: true,
    },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: Bell,
      isActive: isAlertsActive,
    },
  ];

  return (
    <nav
      id="disha-mobile-bottom-nav"
      aria-label="Mobile Navigation"
      className="fixed bottom-0 left-0 right-0 z-40 md:hidden bg-[#101318]/95 backdrop-blur-xl border-t border-white/10 shadow-[0_-8px_24px_rgba(0,0,0,0.5)] px-2 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
    >
      <div className="grid grid-cols-5 items-center justify-around max-w-lg mx-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = item.isActive;

          if (item.highlight) {
            return (
              <button
                key={item.id}
                onClick={() => handleTabClick(item.id)}
                className="flex flex-col items-center justify-center -mt-4 group cursor-pointer focus:outline-none"
                aria-label={item.label}
              >
                <div className="w-12 h-12 rounded-full bg-linear-to-br from-orange-500 to-amber-600 text-white flex items-center justify-center shadow-lg shadow-orange-950/60 ring-4 ring-[#101318] group-active:scale-95 transition-all">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-[10px] font-bold text-orange-400 mt-0.5">
                  {item.label}
                </span>
              </button>
            );
          }

          return (
            <button
              key={item.id}
              onClick={() => handleTabClick(item.id)}
              className={`flex flex-col items-center justify-center py-1 px-1 rounded-xl transition-all cursor-pointer min-h-[44px] focus:outline-none ${
                active ? 'text-orange-400 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
              aria-label={item.label}
            >
              <div className="relative">
                <Icon className={`w-5 h-5 transition-transform ${active ? 'scale-110 text-orange-400' : ''}`} />
                {active && (
                  <span className="absolute -top-1 -right-1 w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse" />
                )}
              </div>
              <span className={`text-[10px] tracking-tight mt-0.5 ${active ? 'font-bold text-white' : 'font-medium'}`}>
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
