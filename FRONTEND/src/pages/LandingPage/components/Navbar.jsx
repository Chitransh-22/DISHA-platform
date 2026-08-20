import React, { useState, useEffect } from 'react';
import {
  Map,
  AlertTriangle,
  Bell,
  BarChart2,
  User,
  Menu,
  X,
  ArrowRight,
} from 'lucide-react';
import { logoEmblemImg } from '../../../assets/images';
import { useAuth } from '../../../context/AuthContext';

export const Navbar = ({
  currentPage,
  onNavigate,
  isLoggedIn: propIsLoggedIn,
  currentUser: propCurrentUser,
  onLogout: propOnLogout,
}) => {
  let authContext = null;
  try {
    authContext = useAuth();
  } catch (e) {
    authContext = null;
  }

  const isLoggedIn = propIsLoggedIn !== undefined ? propIsLoggedIn : (authContext?.isLoggedIn || false);
  const currentUser = propCurrentUser !== undefined ? propCurrentUser : (authContext?.user || null);
  const onLogout = propOnLogout !== undefined ? propOnLogout : authContext?.logout;

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  /* =========================================================
     SCROLL DETECTION
  ========================================================= */

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  /* =========================================================
     CLOSE MOBILE MENU AT 900PX+
  ========================================================= */

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 900) {
        setMobileMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  /* =========================================================
     NAVIGATION HANDLER
  ========================================================= */

  const handleNavigation = (page) => {
    onNavigate(page);
    setMobileMenuOpen(false);
  };

  return (
    <nav
      className={`
        fixed
        top-0
        left-0
        right-0
        z-50
        w-full
        transition-all
        duration-300
        ease-in-out
        ${
          isScrolled
            ? 'py-2 bg-[#101318]/90 backdrop-blur-md shadow-2xl'
            : 'pt-3 sm:pt-4 lg:pt-5 pb-2'
        }
      `}
    >

      {/* =====================================================
          OUTER CONTAINER
      ===================================================== */}

      <div
        className="
          w-full
          max-w-[1600px]
          mx-auto
          px-2
          sm:px-4
          md:px-5
          lg:px-6
          xl:px-8
        "
      >

        {/* ===================================================
            MAIN NAVBAR
        =================================================== */}

        <div
          className={`
            relative
            w-full
            bg-[#101318]/95
            backdrop-blur-lg
            text-white
            rounded-2xl
            min-[900px]:rounded-full
            px-3
            sm:px-4
            md:px-5
            lg:px-6
            xl:px-7
            py-2
            sm:py-2.5
            lg:py-3
            flex
            items-center
            justify-between
            gap-2
            sm:gap-3
            transition-all
            duration-300
            border
            border-white/10
            ${
              isScrolled
                ? 'shadow-orange-950/20 shadow-2xl border-orange-500/20'
                : 'shadow-xl'
            }
          `}
        >

          {/* =================================================
              BRAND
          ================================================= */}

          <button
            id="disha-brand-logo-btn"
            onClick={() => handleNavigation('landing')}
            className="
              flex
              items-center
              gap-2
              sm:gap-2.5
              lg:gap-3
              group
              focus:outline-none
              cursor-pointer
              min-w-0
              shrink-0
            "
          >

            {/* LOGO */}

            <div
              className="
                w-9
                h-9
                sm:w-10
                sm:h-10
                lg:w-11
                lg:h-11
                rounded-full
                overflow-hidden
                border
                border-white/20
                p-0.5
                bg-white
                shadow-md
                shrink-0
                flex
                items-center
                justify-center
                transition-all
                duration-300
                group-hover:scale-105
                group-hover:border-orange-500/50
                group-hover:shadow-orange-500/20
              "
            >
              <img
                src={logoEmblemImg}
                alt="DISHA Official Emblem"
                className="
                  w-full
                  h-full
                  object-contain
                  rounded-full
                  transition-transform
                  duration-500
                  group-hover:rotate-6
                "
                referrerPolicy="no-referrer"
              />
            </div>

            {/* =================================================
                BRAND NAME
            ================================================= */}

            <div className="flex items-center min-w-0">

              <span
                className="
                  font-bold
                  tracking-tight
                  text-lg
                  sm:text-xl
                  lg:text-2xl
                  text-white
                  font-sans
                  leading-none
                  group-hover:text-orange-400
                  transition-colors
                  duration-300
                  whitespace-nowrap
                "
              >
                DISHA
              </span>

              {/* =================================================
                  TAGLINE
                  ONLY VISIBLE AT 900PX+
              ================================================= */}

              <span
                className="
                  hidden
                  min-[900px]:flex
                  items-center
                  ml-2
                  lg:ml-2.5
                  pl-2
                  lg:pl-2.5
                  border-l
                  border-white/20
                  text-[11px]
                  lg:text-[14px]
                  xl:text-[16px]
                  2xl:text-[17px]
                  leading-[1.15]
                  text-slate-300
                  font-sans
                  whitespace-nowrap
                "
              >
                <span>
                  <span className="text-[#f26522]">D</span>isaster{' '}
                  <span className="text-[#f26522]">I</span>ntelligence and
                  <br />
                  <span className="text-[#f26522]">S</span>ituational{' '}
                  <span className="text-[#f26522]">H</span>azard{' '}
                  <span className="text-[#f26522]">A</span>wareness
                </span>
              </span>

            </div>

          </button>

          {/* =================================================
              DESKTOP NAVIGATION
              ONLY 900PX+
          ================================================= */}

          <div
            className="
              hidden
              min-[900px]:flex
              items-center
              justify-center
              gap-1
              sm:gap-2
              lg:gap-3
              flex-1
              min-w-0
              mx-1
              sm:mx-2
              lg:mx-4
            "
          >

            {/* =================================================
                VIEW MAP
            ================================================= */}

            <button
              id="nav-view-map-btn"
              onClick={() => handleNavigation('map')}
              className={`
                group
                relative
                flex
                items-center
                gap-2
                px-3
                lg:px-3.5
                xl:px-4
                py-2
                lg:py-2.5
                rounded-full
                text-sm
                font-medium
                transition-all
                duration-300
                cursor-pointer
                overflow-hidden
                whitespace-nowrap
                shrink-0
                ${
                  currentPage === 'map'
                    ? 'text-orange-400 bg-white/5'
                    : 'text-slate-200 hover:text-white'
                }
              `}
            >

              <span
                className="
                  absolute
                  inset-0
                  bg-linear-to-r
                  from-orange-500/10
                  to-amber-500/10
                  opacity-0
                  group-hover:opacity-100
                  transition-opacity
                  duration-300
                  rounded-full
                "
              />

              <span
                className={`
                  absolute
                  bottom-0
                  left-1/2
                  -translate-x-1/2
                  h-0.5
                  bg-linear-to-r
                  from-orange-500
                  to-amber-400
                  rounded-full
                  transition-all
                  duration-300
                  ${
                    currentPage === 'map'
                      ? 'w-3/4'
                      : 'w-0 group-hover:w-3/4'
                  }
                `}
              />

              <Map
                className="
                  relative
                  z-10
                  w-4
                  h-4
                  text-orange-400
                  shrink-0
                  transition-transform
                  duration-300
                  group-hover:scale-125
                  group-hover:rotate-12
                "
              />

              <span className="relative z-10">
                View Map
              </span>

            </button>

            {/* =================================================
                REPORT INCIDENT
            ================================================= */}

            <button
              id="nav-report-incident-btn"
              onClick={() => handleNavigation('report')}
              className={`
                group
                relative
                flex
                items-center
                gap-2
                px-3
                lg:px-3.5
                xl:px-4
                py-2
                lg:py-2.5
                rounded-full
                text-sm
                font-medium
                transition-all
                duration-300
                cursor-pointer
                overflow-hidden
                whitespace-nowrap
                shrink-0
                ${
                  currentPage === 'report'
                    ? 'text-orange-400 bg-white/5'
                    : 'text-slate-200 hover:text-white'
                }
              `}
            >

              <span
                className="
                  absolute
                  inset-0
                  bg-linear-to-r
                  from-red-500/10
                  to-orange-500/10
                  opacity-0
                  group-hover:opacity-100
                  transition-opacity
                  duration-300
                  rounded-full
                "
              />

              <span
                className={`
                  absolute
                  bottom-0
                  left-1/2
                  -translate-x-1/2
                  h-0.5
                  bg-linear-to-r
                  from-red-500
                  to-orange-400
                  rounded-full
                  transition-all
                  duration-300
                  ${
                    currentPage === 'report'
                      ? 'w-3/4'
                      : 'w-0 group-hover:w-3/4'
                  }
                `}
              />

              <AlertTriangle
                className="
                  relative
                  z-10
                  w-4
                  h-4
                  text-orange-500
                  shrink-0
                  transition-all
                  duration-300
                  group-hover:scale-125
                  group-hover:-rotate-12
                  group-hover:text-red-400
                "
              />

              <span className="relative z-10">
                Report Incident
              </span>

            </button>

            {/* =================================================
                ALERTS
            ================================================= */}

            <button
              id="nav-alerts-btn"
              onClick={() => handleNavigation('alerts')}
              className={`
                group
                relative
                flex
                items-center
                gap-2
                px-3
                lg:px-3.5
                xl:px-4
                py-2
                lg:py-2.5
                rounded-full
                text-sm
                font-medium
                transition-all
                duration-300
                cursor-pointer
                overflow-hidden
                whitespace-nowrap
                shrink-0
                ${
                  currentPage === 'alerts'
                    ? 'text-orange-400 bg-white/5'
                    : 'text-slate-200 hover:text-white'
                }
              `}
            >

              <span
                className="
                  absolute
                  inset-0
                  bg-linear-to-r
                  from-orange-500/10
                  to-yellow-500/10
                  opacity-0
                  group-hover:opacity-100
                  transition-opacity
                  duration-300
                  rounded-full
                "
              />

              <span
                className={`
                  absolute
                  bottom-0
                  left-1/2
                  -translate-x-1/2
                  h-0.5
                  bg-linear-to-r
                  from-orange-500
                  to-amber-400
                  rounded-full
                  transition-all
                  duration-300
                  ${
                    currentPage === 'alerts'
                      ? 'w-3/4'
                      : 'w-0 group-hover:w-3/4'
                  }
                `}
              />

              <Bell
                className="
                  relative
                  z-10
                  w-4
                  h-4
                  text-orange-400
                  shrink-0
                  transition-transform
                  duration-300
                  group-hover:scale-125
                  group-hover:rotate-12
                "
              />

              <span className="relative z-10">
                Alerts
              </span>

              {/* LIVE DOT */}

              <span
                className="
                  absolute
                  top-1.5
                  right-1.5
                  flex
                  h-2
                  w-2
                "
              >
                <span
                  className="
                    animate-ping
                    absolute
                    inline-flex
                    h-full
                    w-full
                    rounded-full
                    bg-orange-400
                    opacity-75
                  "
                />

                <span
                  className="
                    relative
                    inline-flex
                    rounded-full
                    h-2
                    w-2
                    bg-orange-500
                  "
                />
              </span>

            </button>

            {/* =================================================
                ANALYSIS
            ================================================= */}

            <button
              id="nav-analysis-btn"
              onClick={() => handleNavigation('analysis')}
              className={`
                group
                relative
                flex
                items-center
                gap-2
                px-3
                lg:px-3.5
                xl:px-4
                py-2
                lg:py-2.5
                rounded-full
                text-sm
                font-medium
                transition-all
                duration-300
                cursor-pointer
                overflow-hidden
                whitespace-nowrap
                shrink-0
                ${
                  currentPage === 'analysis' || currentPage === 'graphs'
                    ? 'text-orange-400 bg-white/5'
                    : 'text-slate-200 hover:text-white'
                }
              `}
            >

              <span
                className="
                  absolute
                  inset-0
                  bg-linear-to-r
                  from-orange-500/10
                  to-amber-500/10
                  opacity-0
                  group-hover:opacity-100
                  transition-opacity
                  duration-300
                  rounded-full
                "
              />

              <span
                className={`
                  absolute
                  bottom-0
                  left-1/2
                  -translate-x-1/2
                  h-0.5
                  bg-linear-to-r
                  from-orange-500
                  to-amber-400
                  rounded-full
                  transition-all
                  duration-300
                  ${
                    currentPage === 'analysis' || currentPage === 'graphs'
                      ? 'w-3/4'
                      : 'w-0 group-hover:w-3/4'
                  }
                `}
              />

              <BarChart2
                className="
                  relative
                  z-10
                  w-4
                  h-4
                  text-orange-400
                  shrink-0
                  transition-transform
                  duration-300
                  group-hover:scale-125
                  group-hover:rotate-6
                "
              />

              <span className="relative z-10">
                Analysis
              </span>

            </button>

          </div>

          {/* =================================================
              FULL AUTH BUTTON
              ONLY 900PX+
          ================================================= */}

          <div
            className="
              hidden
              min-[900px]:flex
              items-center
              shrink-0
            "
          >

            {isLoggedIn ? (
              <div className="flex items-center gap-2">
                <button
                  id="nav-auth-user-btn"
                  onClick={() => handleNavigation('report')}
                  className="
                    group
                    relative
                    flex
                    items-center
                    justify-center
                    gap-2
                    min-w-max
                    whitespace-nowrap
                    bg-linear-to-r
                    from-emerald-600
                    to-teal-600
                    text-white
                    font-semibold
                    text-xs
                    lg:text-sm
                    px-3.5
                    lg:px-4
                    py-2
                    lg:py-2.5
                    rounded-full
                    shadow-md
                    shadow-emerald-950/20
                    transition-all
                    cursor-pointer
                  "
                >
                  <User className="w-3.5 h-3.5 lg:w-4 lg:h-4 shrink-0" />
                  <span className="relative z-10 whitespace-nowrap max-w-[120px] truncate">
                    {currentUser?.name ? currentUser.name.split(' ')[0] : (currentUser?.username || 'Verified User')}
                  </span>
                </button>
                {onLogout && (
                  <button
                    id="nav-logout-btn"
                    onClick={onLogout}
                    className="
                      text-xs
                      font-semibold
                      text-slate-400
                      hover:text-red-400
                      bg-white/5
                      hover:bg-red-500/10
                      border
                      border-white/10
                      hover:border-red-500/30
                      px-3
                      py-2
                      rounded-full
                      transition-all
                      cursor-pointer
                    "
                  >
                    Sign Out
                  </button>
                )}
              </div>
            ) : (
              <button
                id="nav-auth-btn"
                onClick={() => handleNavigation('auth')}
                className="
                  group
                  relative
                  flex
                  items-center
                  justify-center
                  gap-2
                  min-w-max
                  whitespace-nowrap
                  bg-linear-to-r
                  from-[#f26522]
                  to-[#ea580c]
                  hover:from-[#ea580c]
                  hover:to-[#c2410c]
                  text-white
                  font-semibold
                  text-xs
                  lg:text-sm
                  px-3.5
                  lg:px-5
                  py-2
                  lg:py-2.5
                  rounded-full
                  transition-all
                  duration-300
                  shadow-lg
                  shadow-orange-950/40
                  hover:shadow-orange-500/30
                  hover:-translate-y-0.5
                  active:translate-y-0
                  active:scale-95
                  cursor-pointer
                  overflow-hidden
                  border
                  border-orange-400/30
                "
              >
                <span
                  className="
                    absolute
                    inset-0
                    w-1/2
                    h-full
                    bg-white/20
                    skew-x-12
                    -translate-x-full
                    group-hover:translate-x-[300%]
                    transition-transform
                    duration-1000
                    ease-in-out
                  "
                />
                <User
                  className="
                    relative
                    z-10
                    w-3.5
                    h-3.5
                    lg:w-4
                    lg:h-4
                    shrink-0
                    transition-transform
                    duration-300
                    group-hover:scale-110
                  "
                />
                <span className="relative z-10 whitespace-nowrap">
                  Sign In / Sign Up
                </span>
                <ArrowRight
                  className="
                    relative
                    z-10
                    w-3
                    h-3
                    lg:w-3.5
                    lg:h-3.5
                    shrink-0
                    opacity-0
                    -translate-x-2
                    group-hover:opacity-100
                    group-hover:translate-x-0
                    transition-all
                    duration-300
                  "
                />
              </button>
            )}

          </div>

          {/* =================================================
              BELOW 900PX
              
              ONLY:
              SIGN IN + HAMBURGER
              
              NO ALERTS
              NO MAP
              NO REPORT
          ================================================= */}

          <div
            className="
              flex
              min-[900px]:hidden
              items-center
              gap-1.5
              sm:gap-2
              shrink-0
            "
          >

            {/* COMPACT SIGN IN / USER BADGE */}

            {isLoggedIn ? (
              <button
                id="nav-mobile-user-btn"
                onClick={() => handleNavigation('report')}
                className="
                  flex
                  items-center
                  justify-center
                  gap-1.5
                  whitespace-nowrap
                  bg-linear-to-r
                  from-emerald-600
                  to-teal-600
                  text-white
                  text-[11px]
                  sm:text-xs
                  font-semibold
                  px-2.5
                  sm:px-3.5
                  py-1.5
                  sm:py-2
                  rounded-full
                  cursor-pointer
                  transition-all
                  duration-200
                  active:scale-95
                  shadow-md
                  shadow-emerald-950/30
                  border
                  border-emerald-400/20
                  max-w-[120px]
                "
              >
                <User
                  className="
                    w-3
                    h-3
                    sm:w-3.5
                    sm:h-3.5
                    shrink-0
                  "
                />
                <span className="truncate">
                  {currentUser?.name ? currentUser.name.split(' ')[0] : (currentUser?.username || 'Verified')}
                </span>
              </button>
            ) : (
              <button
                id="nav-mobile-auth-btn"
                onClick={() => handleNavigation('auth')}
                className="
                  flex
                  items-center
                  justify-center
                  gap-1.5
                  whitespace-nowrap
                  bg-linear-to-r
                  from-[#f26522]
                  to-[#ea580c]
                  hover:from-[#ea580c]
                  hover:to-[#c2410c]
                  text-white
                  text-[11px]
                  sm:text-xs
                  font-semibold
                  px-2.5
                  sm:px-3.5
                  py-1.5
                  sm:py-2
                  rounded-full
                  cursor-pointer
                  transition-all
                  duration-200
                  active:scale-95
                  shadow-md
                  shadow-orange-950/30
                  border
                  border-orange-400/20
                "
              >
                <User
                  className="
                    w-3
                    h-3
                    sm:w-3.5
                    sm:h-3.5
                    shrink-0
                  "
                />
                <span className="whitespace-nowrap">
                  Sign In
                </span>
              </button>
            )}

            {/* HAMBURGER */}

            <button
              id="mobile-menu-toggle-btn"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="
                flex
                items-center
                justify-center
                w-8
                h-8
                sm:w-9
                sm:h-9
                md:w-10
                md:h-10
                text-slate-300
                hover:text-white
                hover:bg-white/10
                rounded-xl
                focus:outline-none
                cursor-pointer
                transition-all
                duration-200
                shrink-0
              "
              aria-label="Toggle menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 sm:w-6 sm:h-6" />
              ) : (
                <Menu className="w-5 h-5 sm:w-6 sm:h-6" />
              )}
            </button>

          </div>

        </div>

        {/* =====================================================
            MOBILE / TABLET DRAWER
            BELOW 900PX
        ===================================================== */}

        {mobileMenuOpen && (
          <div
            className="
              min-[900px]:hidden
              mt-2
              w-full
              bg-[#101318]/95
              backdrop-blur-xl
              text-white
              rounded-2xl
              p-3
              sm:p-4
              shadow-2xl
              border
              border-white/10
              flex
              flex-col
              gap-1.5
              animate-in
              fade-in
              slide-in-from-top-2
              duration-300
            "
          >

            {/* VIEW MAP */}

            <button
              id="mobile-nav-map-btn"
              onClick={() => handleNavigation('map')}
              className="
                group
                flex
                items-center
                gap-3
                px-3.5
                py-3
                rounded-xl
                hover:bg-white/10
                text-left
                text-sm
                font-medium
                text-slate-200
                hover:text-orange-400
                cursor-pointer
                transition-all
                duration-200
              "
            >

              <Map
                className="
                  w-4
                  h-4
                  text-orange-400
                  shrink-0
                  transition-transform
                  duration-200
                  group-hover:scale-110
                "
              />

              <span>
                View Map
              </span>

            </button>

            {/* REPORT INCIDENT */}

            <button
              id="mobile-nav-report-btn"
              onClick={() => handleNavigation('report')}
              className="
                group
                flex
                items-center
                gap-3
                px-3.5
                py-3
                rounded-xl
                hover:bg-white/10
                text-left
                text-sm
                font-medium
                text-slate-200
                hover:text-orange-400
                cursor-pointer
                transition-all
                duration-200
              "
            >

              <AlertTriangle
                className="
                  w-4
                  h-4
                  text-orange-500
                  shrink-0
                  transition-transform
                  duration-200
                  group-hover:scale-110
                "
              />

              <span>
                Report Incident
              </span>

            </button>

            {/* ALERTS */}

            <button
              id="mobile-nav-alerts-btn"
              onClick={() => handleNavigation('alerts')}
              className="
                group
                flex
                items-center
                gap-3
                px-3.5
                py-3
                rounded-xl
                hover:bg-white/10
                text-left
                text-sm
                font-medium
                text-slate-200
                hover:text-orange-400
                justify-between
                cursor-pointer
                transition-all
                duration-200
              "
            >

              <div className="flex items-center gap-3">

                <Bell
                  className="
                    w-4
                    h-4
                    text-orange-400
                    transition-transform
                    duration-200
                    group-hover:scale-110
                  "
                />

                <span>
                  Alerts
                </span>

              </div>

              <span
                className="
                  bg-orange-500/20
                  text-orange-400
                  text-xs
                  font-semibold
                  px-2
                  py-0.5
                  rounded-full
                  border
                  border-orange-500/30
                  whitespace-nowrap
                "
              >
                3 Live
              </span>

            </button>

            {/* ANALYSIS */}

            <button
              id="mobile-nav-analysis-btn"
              onClick={() => handleNavigation('analysis')}
              className={`
                group
                flex
                items-center
                gap-3
                px-3.5
                py-3
                rounded-xl
                hover:bg-white/10
                text-left
                text-sm
                font-medium
                cursor-pointer
                transition-all
                duration-200
                ${
                  currentPage === 'analysis' || currentPage === 'graphs'
                    ? 'text-orange-400 bg-white/5'
                    : 'text-slate-200 hover:text-orange-400'
                }
              `}
            >

              <BarChart2
                className="
                  w-4
                  h-4
                  text-orange-400
                  transition-transform
                  duration-200
                  group-hover:scale-110
                "
              />

              <span>
                Analysis
              </span>

            </button>

            {/* FULL AUTH */}

            {isLoggedIn ? (
              <div className="flex flex-col gap-2 mt-2 pt-2 border-t border-white/10">
                <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-sm font-semibold">
                  <User className="w-4 h-4 shrink-0" />
                  <span className="truncate">
                    {currentUser?.name || currentUser?.username || 'Verified User'}
                  </span>
                </div>
                {onLogout && (
                  <button
                    id="mobile-nav-logout-btn"
                    onClick={() => {
                      onLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="
                      flex
                      items-center
                      justify-center
                      gap-2
                      bg-white/5
                      hover:bg-red-500/10
                      border
                      border-white/10
                      hover:border-red-500/30
                      text-slate-300
                      hover:text-red-400
                      font-semibold
                      text-sm
                      py-2.5
                      rounded-xl
                      cursor-pointer
                      transition-all
                    "
                  >
                    Sign Out
                  </button>
                )}
              </div>
            ) : (
              <button
                id="mobile-nav-auth-full-btn"
                onClick={() => handleNavigation('auth')}
                className="
                  flex
                  items-center
                  justify-center
                  gap-2
                  bg-linear-to-r
                  from-[#f26522]
                  to-[#ea580c]
                  hover:from-[#ea580c]
                  hover:to-[#c2410c]
                  active:scale-[0.98]
                  text-white
                  font-semibold
                  text-sm
                  py-3
                  rounded-xl
                  mt-2
                  cursor-pointer
                  shadow-lg
                  shadow-orange-950/40
                  transition-all
                  duration-200
                "
              >
                <User className="w-4 h-4" />
                <span>
                  Sign In / Sign Up
                </span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}

          </div>
        )}

      </div>
    </nav>
  );
};