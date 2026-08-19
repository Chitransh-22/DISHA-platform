import React from 'react';
import { ShieldCheck, Activity, Bell, MapPin, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

// Fast, smooth stagger container variant
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

// Smooth fade up animation variant
const fadeInUpVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] },
  },
};

export const HeroSection = () => {
  const featurePills = [
    { icon: Activity, label: 'Detect', desc: 'NCS Seismic Sensors', color: 'text-orange-600', bg: 'bg-orange-500/10', border: 'border-orange-500/20' },
    { icon: Bell, label: 'Alert', desc: 'NDMA SACHET Warnings', color: 'text-amber-600', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
    { icon: MapPin, label: 'Respond', desc: 'Geospatial Coordination', color: 'text-blue-600', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
    { icon: ShieldCheck, label: 'Protect', desc: 'National Preparedness', color: 'text-emerald-600', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
  ];

  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 pt-6 sm:pt-10 pb-6 sm:pb-10 relative z-10">
      <motion.div
        className="w-full flex flex-col justify-center"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.2 }}
      >
        {/* Official Badge */}
        <motion.div
          variants={fadeInUpVariants}
          className="inline-flex items-center gap-2.5 bg-orange-50/90 border border-orange-200/90 px-4 py-1.5 rounded-full w-fit mb-4 sm:mb-5 shadow-xs"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-500 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-600" />
          </span>
          <ShieldCheck className="w-4 h-4 text-orange-600" />
          <span className="text-xs sm:text-sm font-semibold text-orange-950 tracking-tight">
            National Disaster Intelligence Platform
          </span>
        </motion.div>

        {/* Main Title Heading - Horizontally extended */}
        <motion.h1
          variants={fadeInUpVariants}
          className="text-3xl sm:text-5xl lg:text-6xl xl:text-[62px] leading-[1.14] font-black text-slate-900 tracking-tight font-sans max-w-5xl"
        >
          Disaster{' '}
          <span className="bg-gradient-to-r from-orange-600 via-orange-500 to-amber-500 bg-clip-text text-transparent">
            intelligence
          </span>{' '}
          and situational hazard awareness
        </motion.h1>

        {/* Subtitle Description - Horizontally extended */}
        <motion.p
          variants={fadeInUpVariants}
          className="mt-4 sm:mt-5 text-base sm:text-lg lg:text-[19px] text-slate-600 max-w-4xl leading-relaxed font-normal"
        >
          Track real-time disasters, view affected areas, and stay informed with the latest updates across India and neighbouring countries.
        </motion.p>

        {/* Feature Capability Pills - Extended Horizontally */}
        <motion.div
          variants={fadeInUpVariants}
          className="mt-6 sm:mt-8 flex flex-wrap items-center gap-3 sm:gap-4 pt-1"
        >
          {featurePills.map((pill, index) => {
            const IconComponent = pill.icon;
            return (
              <div
                key={index}
                className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-2xl bg-white/90 border border-slate-200/90 shadow-xs hover:shadow-md hover:border-orange-400/60 hover:-translate-y-0.5 transition-all duration-200 cursor-default group"
              >
                <div className={`w-8 h-8 rounded-xl ${pill.bg} border ${pill.border} flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-110`}>
                  <IconComponent className={`w-4 h-4 ${pill.color}`} />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-bold text-slate-800 text-xs sm:text-sm leading-tight group-hover:text-orange-600 transition-colors">
                    {pill.label}
                  </span>
                  <span className="text-[11px] text-slate-400 hidden sm:inline">
                    {pill.desc}
                  </span>
                </div>
              </div>
            );
          })}
        </motion.div>

        {/* Trust & Network Status Bar - Extended Horizontally */}
        <motion.div
          variants={fadeInUpVariants}
          className="mt-6 flex flex-wrap items-center gap-3 text-xs sm:text-sm text-slate-500 font-medium"
        >
          <div className="flex items-center gap-1.5 text-emerald-600 font-semibold">
            <CheckCircle2 className="w-4 h-4" />
            <span>NCS & NDMA Feeds Active</span>
          </div>
          <span className="text-slate-300 hidden sm:inline">•</span>
          <span>24/7 National Emergency Surveillance</span>
          <span className="text-slate-300 hidden sm:inline">•</span>
          <span>Geospatial Incident Tracking</span>
        </motion.div>
      </motion.div>
    </section>
  );
};