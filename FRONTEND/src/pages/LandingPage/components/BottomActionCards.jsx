import React from 'react';
import { FileWarning, MapPin, ArrowRight, ShieldAlert, Navigation } from 'lucide-react';
import { motion } from 'framer-motion';

// Container stagger configuration
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

// Smooth pop-up variant
const popUpCardVariants = {
  hidden: { 
    opacity: 0, 
    y: 20, 
  },
  visible: {
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

export const BottomActionCards = ({ onNavigate }) => {
  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 pt-2 pb-12 sm:pb-16 overflow-hidden">
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.2 }}
      >
        {/* Card 1: Report an Incident */}
        <motion.button
          id="bottom-card-report-incident-btn"
          variants={popUpCardVariants}
          whileHover={{ 
            y: -3,
            transition: { duration: 0.2, ease: 'easeOut' } 
          }}
          whileTap={{ 
            scale: 0.98,
            transition: { duration: 0.1 }
          }}
          onClick={() => onNavigate('report')}
          className="group relative overflow-hidden bg-gradient-to-br from-[#0b0f17] to-[#131926] text-white rounded-3xl p-6 sm:p-7 text-left border border-white/15 shadow-xl shadow-slate-900/10 transition-all duration-300 hover:border-orange-500/50 hover:shadow-2xl hover:shadow-orange-950/25 flex items-center justify-between gap-4 cursor-pointer focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          {/* Subtle Ambient Backlight Glow on hover */}
          <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
          <div className="absolute -bottom-8 -right-8 w-36 h-36 bg-orange-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-orange-500/20 transition-all duration-300" />

          {/* Left Block */}
          <div className="flex items-center gap-4 sm:gap-5 z-10">
            {/* Tactical Icon Container */}
            <div className="w-13 h-13 sm:w-15 sm:h-15 rounded-2xl bg-white/5 border border-white/15 flex items-center justify-center shrink-0 shadow-lg group-hover:border-orange-500/50 group-hover:bg-orange-500/15 transition-all duration-300">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-md transition-transform duration-300 group-hover:scale-105">
                <FileWarning className="w-5 h-5 text-white" />
              </div>
            </div>

            {/* Content */}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight font-sans transition-colors duration-200 group-hover:text-orange-400">
                  Report an Incident
                </h3>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-300 border border-orange-500/30 hidden sm:inline-block">
                  Citizen Feed
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 font-normal leading-relaxed max-w-xs">
                Help us respond faster by reporting incidents in your area.
              </p>
            </div>
          </div>

          {/* Right Action Button Circle */}
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-orange-500 group-hover:bg-orange-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-orange-950/40 transition-all duration-200 group-hover:scale-105 z-10">
            <ArrowRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" />
          </div>
        </motion.button>

        {/* Card 2: Nearby Incidents */}
        <motion.button
          id="bottom-card-nearby-incidents-btn"
          variants={popUpCardVariants}
          whileHover={{ 
            y: -3,
            transition: { duration: 0.2, ease: 'easeOut' } 
          }}
          whileTap={{ 
            scale: 0.98,
            transition: { duration: 0.1 }
          }}
          onClick={() => onNavigate('nearby')}
          className="group relative overflow-hidden bg-gradient-to-br from-[#0b0f17] to-[#131926] text-white rounded-3xl p-6 sm:p-7 text-left border border-white/15 shadow-xl shadow-slate-900/10 transition-all duration-300 hover:border-amber-500/50 hover:shadow-2xl hover:shadow-amber-950/25 flex items-center justify-between gap-4 cursor-pointer focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          {/* Subtle Ambient Backlight Glow on hover */}
          <div className="absolute inset-0 bg-gradient-to-r from-amber-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
          <div className="absolute -bottom-8 -right-8 w-36 h-36 bg-amber-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-amber-500/20 transition-all duration-300" />

          {/* Left Block */}
          <div className="flex items-center gap-4 sm:gap-5 z-10">
            {/* Tactical Icon Container */}
            <div className="w-13 h-13 sm:w-15 sm:h-15 rounded-2xl bg-white/5 border border-white/15 flex items-center justify-center shrink-0 shadow-lg group-hover:border-amber-500/50 group-hover:bg-amber-500/15 transition-all duration-300">
              <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-md transition-transform duration-300 group-hover:scale-105">
                <MapPin className="w-5 h-5 text-white" />
              </div>
            </div>

            {/* Content */}
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight font-sans transition-colors duration-200 group-hover:text-amber-400">
                  Nearby Incidents
                </h3>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 hidden sm:inline-block">
                  Proximity Radar
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 font-normal leading-relaxed max-w-xs">
                View recent incidents happening near your location.
              </p>
            </div>
          </div>

          {/* Right Action Button Circle */}
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-r from-amber-500 to-orange-500 group-hover:from-amber-600 group-hover:to-orange-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-amber-950/40 transition-all duration-200 group-hover:scale-105 z-10">
            <ArrowRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" />
          </div>
        </motion.button>
      </motion.div>
    </section>
  );
};