import React from 'react';
import {
  ShieldCheck,
  Activity,
  Bell,
  MapPin,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { heroRescueImg } from '../../../assets/images';

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
    y: 20,
    filter: 'blur(8px)',
  },

  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',

    transition: {
      duration: 2,
      ease: [0.22, 1, 0.36, 1],
    },
  },
};

/* =========================================================
   WORD HOVER ANIMATION
========================================================= */

const wordHover = {
  y: -6,
  scale: 1.05,

  transition: {
    type: 'spring',
    stiffness: 400,
    damping: 15,
  },
};

/* =========================================================
   HERO SECTION
========================================================= */

export const HeroSection = () => {
  const featurePills = [
    { icon: Activity, label: 'Detect' },
    { icon: Bell, label: 'Alert' },
    { icon: MapPin, label: 'Respond' },
    { icon: ShieldCheck, label: 'Protect' },
  ];

  return (
    <section
      className="
        relative
        w-full
        overflow-hidden
        px-4
        sm:px-6
        pt-16
        sm:pt-20
        pb-10
        sm:pb-12
      "
    >

      {/* =====================================================
          BACKGROUND ATMOSPHERE
      ===================================================== */}

      <motion.div
        className="
          absolute
          left-1/2
          top-20
          -translate-x-1/2
          w-112.5
          h-112.5
          rounded-full
          bg-orange-500/10
          blur-[100px]
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
          HERO CONTAINER
      ===================================================== */}

      <div
        className="
          relative
          max-w-6xl
          mx-auto
          min-h-125
          flex
          items-center
          justify-center
        "
      >

        {/* ===================================================
            BACKGROUND RESCUE IMAGE
            RECTANGULAR VERSION
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
            scale: 0.92,
          }}
          animate={{
            opacity: 1,
            scale: 1,
          }}
          transition={{
            duration: 1.4,
            ease: [0.22, 1, 0.36, 1],
          }}
        >

          {/* RECTANGLE IMAGE CONTAINER */}

          <div
            className="
              relative
              w-[92%]
              max-w-5xl
              h-82.5
              sm:h-97.5
              lg:h-107.5
              rounded-[28px]
              overflow-hidden
            "
          >

            {/* ===============================================
                RESCUE IMAGE
            =============================================== */}

            <motion.img
              src={heroRescueImg}
              alt=""
              className="
                absolute
                inset-0
                w-full
                h-full
                object-cover
                rounded-[28px]
                opacity-[0.45]
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

            {/* ===============================================
                DARK OVERLAY
            =============================================== */}

            <div
              className="
                absolute
                inset-0
                rounded-[28px]
                bg-slate-950/35
              "
            />

            {/* ===============================================
                DARK + ORANGE GRADIENT
            =============================================== */}

            <div
              className="
                absolute
                inset-0
                rounded-[28px]
                bg-linear-to-br
                from-slate-950/50
                via-slate-900/20
                to-orange-950/50
              "
            />

            {/* ===============================================
                SOFT WHITE BORDER
            =============================================== */}

            <div
              className="
                absolute
                inset-0
                rounded-[28px]
                border
                border-white/30
              "
            />

            {/* ===============================================
                CENTER CROSSHAIR
            =============================================== */}

            <div className="absolute inset-0 opacity-30">

              {/* Vertical Line */}

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

              {/* Horizontal Line */}

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

            {/* ===============================================
                OUTER RADAR RECTANGLE
            =============================================== */}

            <motion.div
              className="
                absolute
                inset-[6%]
                rounded-[22px]
                border
                border-orange-500/40
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

            {/* ===============================================
                INNER DASHED RADAR RECTANGLE
            =============================================== */}

            <motion.div
              className="
                absolute
                inset-[14%]
                rounded-[18px]
                border
                border-orange-400/30
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

            {/* ===============================================
                ROTATING ORANGE CLOCK / RADAR HAND
            =============================================== */}

            <motion.div
              className="
                absolute
                left-1/2
                top-[5%]
                w-1
                h-[45%]
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

            {/* ===============================================
                BRIGHT CENTER RADAR POINT
            =============================================== */}

            <motion.div
              className="
                absolute
                left-1/2
                top-1/2
                -translate-x-1/2
                -translate-y-1/2
                w-3
                h-3
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

            {/* ===============================================
                SMALL RADAR DOTS
            =============================================== */}

            <motion.div
              className="
                absolute
                top-[25%]
                left-[30%]
                w-2
                h-2
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

            <motion.div
              className="
                absolute
                top-[65%]
                right-[25%]
                w-2
                h-2
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
            mt-16
            sm:mt-20
          "
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >

          {/* =================================================
              BADGE
          ================================================= */}

          <motion.div
            variants={fadeUpVariants}
            className="
              inline-flex
              items-center
              gap-2
              bg-[#ffedd5]
              border
              border-orange-200/80
              px-3.5
              py-1.5
              rounded-full
              shadow-sm
            "
          >

            <motion.span
              className="
                w-2
                h-2
                rounded-full
                bg-orange-500
              "
              animate={{
                scale: [1, 1.5, 1],
                opacity: [1, 0.5, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
              }}
            />

            <ShieldCheck
              className="
                w-3.5
                h-3.5
                text-[#ea580c]
              "
            />

            <span
              className="
                text-xs
                font-semibold
                text-[#9a3412]
              "
            >
              Building a Safer India, Together
            </span>

          </motion.div>

          {/* =================================================
              MAIN HEADING
          ================================================= */}

          <motion.h1
            variants={fadeUpVariants}
            className="
              mt-5
              sm:mt-6
              text-3xl
              sm:text-5xl
              lg:text-6xl
              leading-[1.1]
              font-extrabold
              tracking-tight
              text-[#f5f6f9]
              select-none
            "
          >

            {/* ROW 1 */}

            <span className="block">

              <motion.span
                className="
                  inline-block
                  cursor-pointer
                  text-orange-100
                "
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Disaster 
              </motion.span>

              {' '}

              <motion.span
                className="
                  inline-block
                  cursor-pointer
                  text-[#ff5900]
                "
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Intelligence
              </motion.span>

            </span>

            {/* ROW 2 */}

            <span
              className="
                block
                mt-1
                sm:mt-2
              "
            >

              <motion.span
                className="
                  inline-block
                  cursor-pointer
                  text-orange-100
                "
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                and
              </motion.span>

              {' '}

              <motion.span
                className="
                  inline-block
                  cursor-pointer
                  text-orange-100
                "
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Situational
              </motion.span>

            </span>

            {/* ROW 3 */}

            <span
              className="
                block
                mt-1
                sm:mt-2
              "
            >

              <motion.span
                className="
                  inline-block
                  cursor-pointer
                  text-orange-100
                "
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Hazard
              </motion.span>

              {' '}

              <motion.span
                className="
                  inline-block
                  cursor-pointer
                  text-orange-100
                "
                whileHover={{
                  ...wordHover,
                  color: '#c2410c',
                }}
              >
                Awareness
              </motion.span>

            </span>

          </motion.h1>

          {/* =================================================
              DESCRIPTION
          ================================================= */}

          <motion.p
            variants={fadeUpVariants}
            className="
              mt-4
              sm:mt-5
              max-w-xl
              text-sm
              sm:text-base
              lg:text-lg
              text-orange-50
              leading-relaxed
              font-normal
            "
          >
            Track real-time disasters, view affected areas, and stay
            informed with intelligent updates across India and
            neighbouring countries.
          </motion.p>

          {/* =================================================
              FEATURE PILLS
          ================================================= */}

          <motion.div
            variants={fadeUpVariants}
            className="
              mt-6
              sm:mt-8
              flex
              flex-wrap
              items-center
              justify-center
              gap-2.5
              sm:gap-4
            "
          >

            {featurePills.map((pill, index) => {

              const IconComponent = pill.icon;

              return (
                <motion.div
                  key={index}
                  whileHover={{
                    y: -3,
                    scale: 1.03,
                  }}
                  whileTap={{
                    scale: 0.97,
                  }}
                  transition={{
                    type: 'spring',
                    stiffness: 350,
                    damping: 18,
                  }}
                  className="
                    group
                    flex
                    items-center
                    gap-2
                    rounded-full
                    border
                    border-slate-200/80
                    bg-white/75
                    backdrop-blur-md
                    px-3.5
                    py-2
                    shadow-sm
                    cursor-pointer
                    select-none
                  "
                >

                  {/* ICON */}

                  <motion.div
                    className="
                      w-7
                      h-7
                      rounded-full
                      bg-orange-100
                      flex
                      items-center
                      justify-center
                    "
                    whileHover={{
                      rotate: 12,
                      backgroundColor: '#f97316',
                    }}
                    transition={{
                      type: 'spring',
                      stiffness: 300,
                      damping: 15,
                    }}
                  >

                    <IconComponent
                      className="
                        w-3.5
                        h-3.5
                        text-[#ea580c]
                        group-hover:text-white
                        transition-colors
                        duration-300
                      "
                    />

                  </motion.div>

                  {/* LABEL */}

                  <span
                    className="
                      font-medium
                      text-xs
                      sm:text-sm
                      text-slate-700
                      group-hover:text-orange-600
                      transition-colors
                      duration-300
                    "
                  >
                    {pill.label}
                  </span>

                </motion.div>
              );
            })}

          </motion.div>

        </motion.div>

      </div>
    </section>
  );
};