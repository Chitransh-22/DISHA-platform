import React from 'react';
import { ShieldCheck, Activity, Bell, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';
import { heroRescueImg } from '../../../assets/images';

// Stagger container variant for smooth sequential loading
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.1,
    },
  },
};

// Fade up animation variant for text and pill elements
const fadeInUpVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 5, ease: [0.22, 1, 0.36, 1] },
  },
};

export const HeroSection = () => {
  const featurePills = [
    { icon: Activity, label: 'Detect' },
    { icon: Bell, label: 'Alert' },
    { icon: MapPin, label: 'Respond' },
    { icon: ShieldCheck, label: 'Protect' },
  ];

  // Heading split into structured lines & words to preserve breaks while making every word interactive
  const headingLines = [
    [
      { text: 'Disaster', highlight: false },
      { text: 'intelligence', highlight: true },
    ],
    [
      { text: 'and', highlight: false },
      { text: 'situational', highlight: false },
    ],
    [
      { text: 'hazard', highlight: false },
      { text: 'awareness', highlight: false },
    ],
  ];

  return (
    <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 pt-6 sm:pt-10 pb-8 sm:pb-12">
      <div className="relative overflow-hidden rounded-3xl bg-transparent flex flex-col lg:flex-row items-stretch gap-6 lg:gap-8 min-h-95 lg:min-h-110">
        
        {/* Left Content Column */}
        <motion.div
          className="w-full lg:w-6/12 flex flex-col justify-center py-6 sm:py-8 z-10"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
        >
          {/* Tagline Badge */}
          <motion.div
            variants={fadeInUpVariants}
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-2 bg-[#ffedd5] border border-orange-200/80 px-3.5 py-1.5 rounded-full w-fit mb-4 sm:mb-6 shadow-sm cursor-pointer transition-colors hover:border-orange-300 hover:shadow-md"
          >
            <ShieldCheck className="w-4 h-4 text-[#ea580c]" />
            <span className="text-xs sm:text-sm font-semibold text-[#9a3412] tracking-normal">
              Building a Safer India, Together
            </span>
          </motion.div>

          {/* Main Title Heading - Hover animation on EVERY word */}
          <motion.h1
            variants={fadeInUpVariants}
            className="text-3xl sm:text-5xl lg:text-[52px] leading-[1.15] font-extrabold text-[#111827] tracking-tight font-sans select-none"
          >
            {headingLines.map((line, lineIndex) => (
              <React.Fragment key={lineIndex}>
                {line.map((wordObj, wordIndex) => (
                  <React.Fragment key={wordIndex}>
                    <motion.span
                      className={`inline-block cursor-pointer ${
                        wordObj.highlight ? 'text-[#e65100]' : 'text-[#111827]'
                      }`}
                      whileHover={{ scale: 1.06, color: '#c2410c' }}
                      transition={{ type: 'spring', stiffness: 350, damping: 20 }}
                    >
                      {wordObj.text}
                    </motion.span>
                    {wordIndex < line.length - 1 && ' '}
                  </React.Fragment>
                ))}
                {lineIndex < headingLines.length - 1 && (
                  <>
                    {' '}
                    <br className="hidden sm:inline" />
                  </>
                )}
              </React.Fragment>
            ))}
          </motion.h1>

          {/* Subtitle Description */}
          <motion.p
            variants={fadeInUpVariants}
            className="mt-4 sm:mt-5 text-sm sm:text-base lg:text-[17px] text-slate-600 max-w-xl leading-relaxed font-normal"
          >
            Track real-time disasters, view affected areas, and stay informed with the latest updates across India and neighbouring countries.
          </motion.p>

          {/* 4 Feature Action Pills */}
          <motion.div
            variants={fadeInUpVariants}
            className="mt-7 sm:mt-9 flex flex-wrap items-center gap-4 sm:gap-6 pt-2"
          >
            {featurePills.map((pill, index) => {
              const IconComponent = pill.icon;
              return (
                <motion.div
                  key={index}
                  whileHover={{ y: -4, scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 17 }}
                  className="flex items-center gap-2 text-slate-800 font-semibold text-sm sm:text-base group cursor-pointer select-none"
                >
                  <motion.div
                    className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600 shadow-sm group-hover:bg-orange-500 group-hover:text-white transition-colors duration-300"
                    whileHover={{ rotate: 12 }}
                  >
                    <IconComponent className="w-4 h-4 text-[#ea580c] group-hover:text-white transition-colors duration-300" />
                  </motion.div>
                  <span className="font-medium text-slate-800 group-hover:text-orange-600 transition-colors">
                    {pill.label}
                  </span>
                </motion.div>
              );
            })}
          </motion.div>
        </motion.div>

        {/* Right Hero Image Column */}
        <motion.div
          className="w-full lg:w-6/12 relative mt-4 lg:mt-0 min-h-75 sm:min-h-100 lg:min-h-full rounded-2xl lg:rounded-3xl overflow-hidden shadow-xl border border-slate-200/60 group"
          initial={{ opacity: 0, x: 40, scale: 0.95 }}
          whileInView={{ opacity: 1, x: 0, scale: 1 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
        >
          {/* Subtle Ambient Light Glow behind image */}
          <div className="absolute -inset-1 bg-linear-to-r from-orange-400/20 to-amber-300/20 rounded-3xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

          {/* Interactive Image with Motion Scale */}
          <motion.img
            src={heroRescueImg}
            alt="Disaster Response and Rescue Operations"
            className="w-full h-full object-cover object-center rounded-2xl lg:rounded-3xl"
            whileHover={{ scale: 1.06 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            referrerPolicy="no-referrer"
          />

          {/* Border Overlay */}
          <div className="absolute inset-0 ring-1 ring-black/5 rounded-2xl lg:rounded-3xl pointer-events-none" />
        </motion.div>

      </div>
    </section>
  );
};