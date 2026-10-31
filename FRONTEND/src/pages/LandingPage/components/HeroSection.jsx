import React from 'react';
import { motion } from 'framer-motion';
import { heroRescueImg } from '../../../assets/images';
import { DownloadApkButton } from '../../../components/common/DownloadApkButton';

/* =========================================================
   ANIMATION VARIANTS
========================================================= */

const containerVariants = {
  hidden: {
    opacity: 0,
  },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.15,
    },
  },
};

const fadeUpVariants = {
  hidden: {
    opacity: 0,
    y: 18,
    filter: 'blur(6px)',
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 1.2,
      ease: [0.22, 1, 0.36, 1],
    },
  },
};

/* =========================================================
   WORD HOVER ANIMATION
========================================================= */

const wordHover = {
  y: -4,
  scale: 1.04,
  transition: {
    type: 'spring',
    stiffness: 400,
    damping: 16,
  },
};

/* =========================================================
   HERO SECTION
========================================================= */

export const HeroSection = ({ onNavigate }) => {
  const scrollToMap = () => {
    const el =
      document.getElementById('disaster-map-section') ||
      document.getElementById('disha-live-map-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      window.scrollTo({ top: 400, behavior: 'smooth' });
    }
  };

  return (
    <section
      className="
        relative
        w-full
        overflow-hidden
        px-3
        sm:px-6
        pt-28
        sm:pt-32
        lg:pt-36
        pb-4
        sm:pb-8
        mt-2
        sm:mt-4
      "
    >
      {/* =====================================================
          BACKGROUND AMBIENT ATMOSPHERE
          Soft orange-amber glow that gently integrates with
          the homepage ambient lighting.
      ===================================================== */}
      <motion.div
        className="
          absolute
          left-1/2
          top-16
          -translate-x-1/2
          w-72
          h-72
          sm:w-96
          sm:h-96
          lg:w-120
          lg:h-120
          rounded-full
          bg-orange-500/10
          blur-[110px]
          pointer-events-none
        "
        animate={{
          scale: [1, 1.08, 1],
          opacity: [0.35, 0.6, 0.35],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* =====================================================
          HERO COMPOSITION WRAPPER
          Harmoniously scaled and centered on the homepage.
      ===================================================== */}
      <div
        className="
          relative
          max-w-5xl
          mx-auto
          min-h-[360px]
          sm:min-h-[410px]
          lg:min-h-[450px]
          flex
          items-center
          justify-center
        "
      >
        {/* ===================================================
            ATMOSPHERIC RESCUE & RADAR CANVAS
            Features edge-feathered vignette blending so the
            visual canvas dissolves smoothly into the homepage.
        =================================================== */}
        <motion.div
          className="
            absolute
            inset-0
            flex
            items-center
            justify-center
            pointer-events-none
          "
          initial={{
            opacity: 0,
            scale: 0.96,
          }}
          animate={{
            opacity: 1,
            scale: 1,
          }}
          transition={{
            duration: 1.2,
            ease: [0.22, 1, 0.36, 1],
          }}
        >
          {/* Rescue Image Canvas with subtle border and edge feathering */}
          <div
            className="
              relative
              w-full
              h-full
              rounded-2xl
              sm:rounded-3xl
              lg:rounded-[28px]
              overflow-hidden
              border
              border-white/25
              shadow-[0_8px_30px_rgba(15,23,42,0.12)]
            "
          >
            {/* Rescue Image with subtle grayscale and mix-blend */}
            <motion.img
              src={heroRescueImg}
              alt="DISHA Disaster Response Operations"
              className="
                absolute
                inset-0
                w-full
                h-full
                object-cover
                rounded-2xl
                sm:rounded-3xl
                lg:rounded-[28px]
                opacity-[0.42]
                grayscale
                mix-blend-multiply
              "
              animate={{
                scale: [1, 1.025, 1],
              }}
              transition={{
                duration: 7,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            {/* Dark Slate Overlay for Text Legibility */}
            <div
              className="
                absolute
                inset-0
                rounded-2xl
                sm:rounded-3xl
                lg:rounded-[28px]
                bg-slate-950/35
              "
            />

            {/* Dark + Orange Ambient Gradient */}
            <div
              className="
                absolute
                inset-0
                rounded-2xl
                sm:rounded-3xl
                lg:rounded-[28px]
                bg-linear-to-br
                from-slate-950/55
                via-slate-900/25
                to-orange-950/55
              "
            />

            {/* Subtle Inner Glow Border */}
            <div
              className="
                absolute
                inset-0
                rounded-2xl
                sm:rounded-3xl
                lg:rounded-[28px]
                ring-1
                ring-inset
                ring-white/20
              "
            />

            {/* =================================================
                TACTICAL RADAR & RESCUE VISUAL ELEMENTS
            ================================================= */}
            <div className="absolute inset-0 opacity-30">
              {/* Vertical Crosshair Line */}
              <div
                className="
                  absolute
                  left-1/2
                  top-0
                  h-full
                  w-px
                  bg-orange-400/40
                "
              />
              {/* Horizontal Crosshair Line */}
              <div
                className="
                  absolute
                  left-0
                  top-1/2
                  w-full
                  h-px
                  bg-orange-400/40
                "
              />
            </div>

            {/* Outer Radar Rectangle */}
            <motion.div
              className="
                absolute
                inset-[6%]
                rounded-[16px]
                sm:rounded-[22px]
                border
                border-orange-500/35
              "
              animate={{
                opacity: [0.35, 0.75, 0.35],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            {/* Inner Dashed Radar Rectangle */}
            <motion.div
              className="
                absolute
                inset-[14%]
                rounded-[13px]
                sm:rounded-[18px]
                border
                border-orange-400/25
                border-dashed
              "
              animate={{
                opacity: [0.25, 0.65, 0.25],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            {/* Rotating Orange Radar Sweep Hand */}
            <motion.div
              className="
                absolute
                left-1/2
                top-[6%]
                w-1
                h-[44%]
                origin-bottom
                rounded-full
                bg-linear-to-t
                from-orange-600
                via-red-500
                to-red-600
                shadow-[0_0_12px_rgba(249,115,22,0.95)]
              "
              animate={{
                rotate: 360,
              }}
              transition={{
                duration: 6,
                repeat: Infinity,
                ease: 'linear',
              }}
            />

            {/* Bright Center Radar Point */}
            <motion.div
              className="
                absolute
                left-1/2
                top-1/2
                -translate-x-1/2
                -translate-y-1/2
                w-2.5
                h-2.5
                sm:w-3
                sm:h-3
                rounded-full
                bg-orange-400
                shadow-[0_0_20px_rgba(249,115,22,1)]
              "
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.8, 1, 0.8],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            {/* Small Radar Dot 1 */}
            <motion.div
              className="
                absolute
                top-[25%]
                left-[28%]
                w-1.5
                h-1.5
                sm:w-2
                sm:h-2
                rounded-full
                bg-orange-400
                shadow-[0_0_12px_rgba(249,115,22,0.9)]
              "
              animate={{
                opacity: [0.2, 1, 0.2],
                scale: [0.8, 1.3, 0.8],
              }}
              transition={{
                duration: 2.5,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />

            {/* Small Radar Dot 2 */}
            <motion.div
              className="
                absolute
                top-[65%]
                right-[25%]
                w-1.5
                h-1.5
                sm:w-2
                sm:h-2
                rounded-full
                bg-orange-400
                shadow-[0_0_12px_rgba(249,115,22,0.9)]
              "
              animate={{
                opacity: [1, 0.2, 1],
                scale: [1.3, 0.8, 1.3],
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          </div>
        </motion.div>

        {/* ===================================================
            CENTER CONTENT
            Original typography, wording, and responsive CTAs.
        =================================================== */}
        <motion.div
          className="
            relative
            z-20
            w-full
            max-w-4xl
            mx-auto
            flex
            flex-col
            items-center
            text-center
            px-3
            sm:px-6
            py-8
            sm:py-10
            lg:py-12
          "
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* MAIN HEADING */}
          <motion.h1
            variants={fadeUpVariants}
            className="
              text-[26px]
              xs:text-[30px]
              sm:text-5xl
              lg:text-6xl
              leading-[1.12]
              font-extrabold
              tracking-tight
              text-[#f5f6f9]
              select-none
            "
          >
            {/* ROW 1 */}
            <span className="block">
              <motion.span
                className="inline-block cursor-pointer text-orange-100"
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Disaster
              </motion.span>{' '}
              <motion.span
                className="inline-block cursor-pointer text-[#ff5900]"
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Intelligence
              </motion.span>
            </span>

            {/* ROW 2 */}
            <span className="block mt-1 sm:mt-2">
              <motion.span
                className="inline-block cursor-pointer text-orange-100"
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                and
              </motion.span>{' '}
              <motion.span
                className="inline-block cursor-pointer text-orange-100"
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Situational
              </motion.span>
            </span>

            {/* ROW 3 */}
            <span className="block mt-1 sm:mt-2">
              <motion.span
                className="inline-block cursor-pointer text-orange-100"
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Hazard
              </motion.span>{' '}
              <motion.span
                className="inline-block cursor-pointer text-orange-100"
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Awareness
              </motion.span>
            </span>
          </motion.h1>

          {/* DESCRIPTION */}
          <motion.p
            variants={fadeUpVariants}
            className="
              mt-3.5
              sm:mt-5
              max-w-130
              text-xs
              sm:text-sm
              lg:text-base
              text-orange-50/95
              leading-relaxed
              font-normal
            "
          >
            Track real-time disasters, view affected areas, and stay informed
            with intelligent updates across India and neighbouring countries.
          </motion.p>

          {/* OFFICIAL ANDROID APK CTA */}
          <motion.div
            variants={fadeUpVariants}
            className="flex items-center justify-center mt-6 sm:mt-7 w-full z-30"
          >
            <DownloadApkButton variant="hero" />
          </motion.div>
        </motion.div>
      </div>

      {/* =====================================================
          SEAMLESS HERO-TO-MAP TRANSITION BRIDGE
          Subtle visual guide leading downward into the Main
          Disaster Map section without abrupt boundaries.
      ===================================================== */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 1 }}
        onClick={scrollToMap}
        className="
          mt-4
          sm:mt-6
          flex
          flex-col
          items-center
          justify-center
          cursor-pointer
          group
          select-none
        "
      >
        <span
          className="
            text-[11px]
            sm:text-xs
            font-medium
            text-slate-400
            group-hover:text-orange-600
            transition-colors
            duration-200
            tracking-wider
            uppercase
            flex
            items-center
            gap-1.5
          "
        >
          <span>Live Disaster Surveillance Map Below</span>
          <motion.span
            animate={{ y: [0, 3, 0] }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
            className="text-orange-500 font-bold"
          >
            ↓
          </motion.span>
        </span>
      </motion.div>
    </section>
  );
};
