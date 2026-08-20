import React from 'react';
import { FileWarning, MapPin, BarChart2, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

// Container stagger configuration
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15, // Smooth interval between card pop-ups
    },
  },
};

// Box Pop-Up (Scale & Spring) animation variant
const popUpCardVariants = {
  hidden: { 
    opacity: 0, 
    scale: 0.85, 
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 2, // Increases pop-up duration to 1.2 seconds
      ease: [0.6, 1, 0.3, 1], // Keeps the pop smooth without snapping
    },
  },
};

export const BottomActionCards = ({ onNavigate }) => {
  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 pt-2 pb-12 sm:pb-16 overflow-hidden">
      <motion.div
        className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
      >
        {/* Card 1: Report an Incident */}
        <motion.button
          id="bottom-card-report-incident-btn"
          variants={popUpCardVariants}
          whileHover={{ 
            scale: 1.02, 
            transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } 
          }}
          whileTap={{ 
            scale: 0.97,
            transition: { duration: 0.5, ease: 'easeOut' }
          }}
          onClick={() => onNavigate('report')}
          className="group relative overflow-hidden bg-[#101318] text-white rounded-3xl p-5 sm:p-7 text-left border border-white/10 shadow-xl transition-all duration-500 ease-out hover:border-orange-500/40 hover:shadow-orange-950/30 flex items-center justify-between gap-4 cursor-pointer focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          {/* Ambient Glow Transition */}
          <div className="absolute inset-0 bg-linear-to-t from-orange-900/20 via-transparent to-transparent pointer-events-none opacity-40 group-hover:opacity-100 transition-opacity duration-700 ease-out" />
          <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-orange-600/15 blur-2xl pointer-events-none group-hover:bg-orange-500/25 group-hover:h-28 transition-all duration-700 ease-out" />

          {/* Left Block */}
          <div className="flex items-center gap-4 sm:gap-5 z-10">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-[#1e222b] border border-orange-500/30 flex items-center justify-center shrink-0 shadow-lg group-hover:border-orange-500/60 transition-all duration-500 ease-out">
              <div className="w-10 h-10 rounded-full bg-linear-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-md transition-transform duration-500 ease-out group-hover:scale-110">
                <FileWarning className="w-5 h-5 text-white" />
              </div>
            </div>

            <div className="space-y-1">
              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight font-sans transition-colors duration-500 ease-out group-hover:text-orange-400">
                Report Incident
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 font-normal leading-relaxed max-w-xs">
                Help us respond faster by reporting incidents in your area.
              </p>
            </div>
          </div>

          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-full bg-[#f26522] group-hover:bg-[#ea580c] flex items-center justify-center text-white shrink-0 shadow-lg shadow-orange-950/40 transition-all duration-500 ease-out z-10">
            <ArrowRight className="w-5 h-5 transition-transform duration-500 ease-out group-hover:translate-x-1.5" />
          </div>
        </motion.button>

        {/* Card 2: Nearby Incidents */}
        <motion.button
          id="bottom-card-nearby-incidents-btn"
          variants={popUpCardVariants}
          whileHover={{ 
            scale: 1.02, 
            transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } 
          }}
          whileTap={{ 
            scale: 0.97,
            transition: { duration: 0.5, ease: 'easeOut' }
          }}
          onClick={() => onNavigate('nearby')}
          className="group relative overflow-hidden bg-[#101318] text-white rounded-3xl p-5 sm:p-7 text-left border border-white/10 shadow-xl transition-all duration-500 ease-out hover:border-orange-500/40 hover:shadow-orange-950/30 flex items-center justify-between gap-4 cursor-pointer focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          <div className="absolute inset-0 bg-linear-to-t from-orange-900/20 via-transparent to-transparent pointer-events-none opacity-40 group-hover:opacity-100 transition-opacity duration-700 ease-out" />
          <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-orange-600/15 blur-2xl pointer-events-none group-hover:bg-orange-500/25 group-hover:h-28 transition-all duration-700 ease-out" />

          <div className="flex items-center gap-4 sm:gap-5 z-10">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-[#1e222b] border border-orange-500/30 flex items-center justify-center shrink-0 shadow-lg group-hover:border-orange-500/60 transition-all duration-500 ease-out">
              <div className="w-10 h-10 rounded-full bg-linear-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-md transition-transform duration-500 ease-out group-hover:scale-110">
                <MapPin className="w-5 h-5 text-white" />
              </div>
            </div>

            <div className="space-y-1">
              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight font-sans transition-colors duration-500 ease-out group-hover:text-orange-400">
                Nearby Incidents
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 font-normal leading-relaxed max-w-xs">
                View recent incidents happening near your location.
              </p>
            </div>
          </div>

          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-full bg-[#f26522] group-hover:bg-[#ea580c] flex items-center justify-center text-white shrink-0 shadow-lg shadow-orange-950/40 transition-all duration-500 ease-out z-10">
            <ArrowRight className="w-5 h-5 transition-transform duration-500 ease-out group-hover:translate-x-1.5" />
          </div>
        </motion.button>

        {/* Card 3: Disaster Analysis & Analytics */}
        <motion.button
          id="bottom-card-disaster-analysis-btn"
          variants={popUpCardVariants}
          whileHover={{ 
            scale: 1.02, 
            transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } 
          }}
          whileTap={{ 
            scale: 0.97,
            transition: { duration: 0.5, ease: 'easeOut' }
          }}
          onClick={() => onNavigate('analysis')}
          className="group relative overflow-hidden bg-[#101318] text-white rounded-3xl p-5 sm:p-7 text-left border border-white/10 shadow-xl transition-all duration-500 ease-out hover:border-orange-500/40 hover:shadow-orange-950/30 flex items-center justify-between gap-4 cursor-pointer focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          <div className="absolute inset-0 bg-linear-to-t from-orange-900/20 via-transparent to-transparent pointer-events-none opacity-40 group-hover:opacity-100 transition-opacity duration-700 ease-out" />
          <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-orange-600/15 blur-2xl pointer-events-none group-hover:bg-orange-500/25 group-hover:h-28 transition-all duration-700 ease-out" />

          <div className="flex items-center gap-4 sm:gap-5 z-10">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-[#1e222b] border border-orange-500/30 flex items-center justify-center shrink-0 shadow-lg group-hover:border-orange-500/60 transition-all duration-500 ease-out">
              <div className="w-10 h-10 rounded-full bg-linear-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-md transition-transform duration-500 ease-out group-hover:scale-110">
                <BarChart2 className="w-5 h-5 text-white" />
              </div>
            </div>

            <div className="space-y-1">
              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight font-sans transition-colors duration-500 ease-out group-hover:text-orange-400">
                Intelligence Analysis
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 font-normal leading-relaxed max-w-xs">
                Explore 40 data-driven disaster analytics graphs & KPIs.
              </p>
            </div>
          </div>

          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-full bg-[#f26522] group-hover:bg-[#ea580c] flex items-center justify-center text-white shrink-0 shadow-lg shadow-orange-950/40 transition-all duration-500 ease-out z-10">
            <ArrowRight className="w-5 h-5 transition-transform duration-500 ease-out group-hover:translate-x-1.5" />
          </div>
        </motion.button>
      </motion.div>
    </section>
  );
};