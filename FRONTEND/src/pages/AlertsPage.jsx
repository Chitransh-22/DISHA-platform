import React from 'react';
import { ArrowLeft, Bell } from 'lucide-react';

export const AlertsPage = ({ onNavigate }) => {
  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-8">
      <div className="max-w-4xl mx-auto w-full">
        {/* Header with Back Button */}
        <div className="flex items-center gap-4 mb-8">
          <button
            id="back-to-home-btn"
            onClick={() => onNavigate('landing')}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm px-4 py-2 rounded-xl shadow-sm border border-slate-200 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Home</span>
          </button>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-[#ea580c]" />
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">National Emergency Alerts</h1>
          </div>
        </div>

        {/* Empty Page Container for Future Implementation */}
        <div className="bg-white rounded-3xl p-8 sm:p-12 border border-slate-200/80 shadow-md text-center flex flex-col items-center justify-center min-h-100">
          <div className="w-16 h-16 rounded-2xl bg-orange-50 border border-orange-200 flex items-center justify-center text-[#ea580c] mb-4">
            <Bell className="w-8 h-8" />
          </div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 mb-2">
            Real-Time Alert Notification Feed
          </h2>
          <p className="text-sm text-slate-500 max-w-md mb-6 leading-relaxed">
            This page is configured for broadcast emergency warnings, IMD weather bulletins, state-wise red/orange alerts, and early warning notifications.
          </p>
          <button
            onClick={() => onNavigate('landing')}
            className="bg-[#101318] hover:bg-slate-800 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-colors cursor-pointer"
          >
            Return to Landing Page
          </button>
        </div>
      </div>
    </div>
  );
};
