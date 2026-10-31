import React, { useState, useEffect, useRef } from 'react';
import { App as CapApp } from '@capacitor/app';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { ViewMapPage } from './pages/ViewMapPage';
import { ReportIncidentPage } from './pages/ReportIncidentPage';
import { AlertsPage } from './pages/AlertsPage';
import { AuthPage } from './pages/AuthPage';
import { NearbyIncidentsPage } from './pages/NearbyIncidentsPage';
import { AnalysisPage } from './pages/AnalysisPage/AnalysisPage';
import { GraphsAnalyticsPage } from './pages/AnalysisPage/GraphsAnalyticsPage';
import { RecentNewsPage } from './pages/RecentNewsPage';
import { NewsDetailPage } from './pages/NewsDetailPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { NotificationToast } from './components/common/NotificationToast';
import { MobileBottomNav } from './components/common/MobileBottomNav';
import { AppUpdateModal } from './components/common/AppUpdateModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TimeRangeProvider } from './context/TimeRangeContext';
import { logoEmblemImg } from './assets/images';
import {
  isNativePlatform,
  initializeNativeApp,
  registerBackButtonHandler,
  registerNetworkListener,
  registerDeepLinkListener,
} from './services/nativeService';
import { checkForAppUpdate } from './services/appUpdateService';

function AppContent() {
  const isNative = isNativePlatform();
  const { user, isLoggedIn, isLoading, notification, clearNotification, showNotification, logout, loginWithToken } = useAuth();

  // On Native Android: First screen is strictly 'auth' when unauthenticated.
  // On Web: Initial screen is 'landing'.
  const [currentPage, setCurrentPage] = useState(() => (isNative ? 'auth' : 'landing'));
  const [redirectAfterAuth, setRedirectAfterAuth] = useState(null);
  const [selectedNewsId, setSelectedNewsId] = useState(null);
  const [selectedNewsArticle, setSelectedNewsArticle] = useState(null);
  const [focusedEvent, setFocusedEvent] = useState(null);
  const [updateModalInfo, setUpdateModalInfo] = useState(null);

  const currentPageRef = useRef(currentPage);
  currentPageRef.current = currentPage;
  const isLoggedInRef = useRef(isLoggedIn);
  isLoggedInRef.current = isLoggedIn;

  // ─── 1. Native Platform Initializations & Event Listeners ──────────────────
  useEffect(() => {
    initializeNativeApp();

    // Register hardware back button listener for Android
    const unregisterBack = registerBackButtonHandler(
      () => ({
        currentPage: currentPageRef.current,
        isLoggedIn: isLoggedInRef.current,
        isModalOpen: !!updateModalInfo,
        closeModal: () => setUpdateModalInfo(null),
      }),
      (target) => handleNavigate(target)
    );

    // Register network online/offline listener
    const unregisterNetwork = registerNetworkListener(({ connected }) => {
      if (!connected) {
        showNotification?.('warning', 'Internet connection lost. Displaying cached disaster data.');
      } else {
        showNotification?.('success', 'Internet connection restored.');
      }
    });

    // Register deep link listener for OAuth callbacks (e.g. in.disha.app://auth/google/success?...)
    const unregisterDeepLink = registerDeepLinkListener(async ({ accessToken, refreshToken, error }) => {
      if (accessToken) {
        try {
          await loginWithToken(accessToken, refreshToken);
          setCurrentPage('landing');
        } catch (e) {
          showNotification?.('error', 'Authentication failed from login provider.');
        }
      } else if (error) {
        showNotification?.('error', error);
      }
    });

    // Check for Android APK updates on startup
    checkForAppUpdate(false)
      .then((res) => {
        if (res?.hasUpdate && res.updateInfo) {
          setUpdateModalInfo(res.updateInfo);
        }
      })
      .catch(() => {});

    // Check for updates when app resumes to foreground
    let appStateSub = null;
    if (isNative) {
      appStateSub = CapApp.addListener('appStateChange', (state) => {
        if (state.isActive) {
          checkForAppUpdate(false)
            .then((res) => {
              if (res?.hasUpdate && res.updateInfo) {
                setUpdateModalInfo(res.updateInfo);
              }
            })
            .catch(() => {});
        }
      });
    }

    return () => {
      unregisterBack();
      unregisterNetwork();
      unregisterDeepLink();
      if (appStateSub) {
        appStateSub.then((s) => s.remove()).catch(() => {});
      }
    };
  }, [isNative, showNotification, loginWithToken, updateModalInfo]);

  // ─── 2. Web OAuth Redirect URL parsing ─────────────────────────────────────
  useEffect(() => {
    if (window.location.pathname.startsWith('/auth/google/success')) {
      const searchParams = new URLSearchParams(window.location.search);
      const hasError = searchParams.has('error');

      let target = hasError ? 'auth' : 'landing';
      try {
        const savedRedirect = sessionStorage.getItem('disha_auth_redirect');
        if (savedRedirect && !hasError) {
          sessionStorage.removeItem('disha_auth_redirect');
          target = savedRedirect;
        }
      } catch (e) {}
      setCurrentPage(target);
    }
  }, []);

  // ─── 3. Strict Android Login-First Enforcement ─────────────────────────────
  useEffect(() => {
    if (isNative && !isLoading) {
      if (!isLoggedIn && currentPage !== 'auth') {
        // Enforce: unauthenticated Android users MUST always be on the login screen
        setCurrentPage('auth');
      } else if (isLoggedIn && currentPage === 'auth') {
        // Automatically proceed to landing after successful login
        setCurrentPage('landing');
      }
    }
  }, [isNative, isLoading, isLoggedIn, currentPage]);

  const handleNavigate = (page, extra = null) => {
    // Critical: Prevent bypassing authentication on Android
    if (isNative && !isLoggedIn && page !== 'auth') {
      setCurrentPage('auth');
      return;
    }

    if (typeof extra === 'string') {
      setRedirectAfterAuth(extra);
    } else if (extra && typeof extra === 'object') {
      if (extra.newsId) setSelectedNewsId(extra.newsId);
      if (extra.article) setSelectedNewsArticle(extra.article);
      if (extra.redirectTarget) setRedirectAfterAuth(extra.redirectTarget);
      if (extra.focusEvent) setFocusedEvent(extra.focusEvent);
    }
    setCurrentPage(page);

    if (extra && typeof extra === 'object' && extra.scrollToMap) {
      setTimeout(() => {
        const mapEl = document.getElementById('disha-live-map-section');
        if (mapEl) {
          mapEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleLoginSuccess = () => {
    if (redirectAfterAuth) {
      const target = redirectAfterAuth;
      setRedirectAfterAuth(null);
      setCurrentPage(target);
    } else {
      setCurrentPage('landing');
    }
  };

  const handleLogout = async () => {
    await logout();
    // On native platform, immediately return to login
    if (isNative) {
      setCurrentPage('auth');
    } else {
      setCurrentPage('landing');
    }
  };

  // ─── 4. Native Initializing Splash Screen ──────────────────────────────────
  if (isNative && isLoading) {
    return (
      <div className="min-h-screen bg-[#101318] flex flex-col items-center justify-center p-6 text-white select-none">
        <div className="w-24 h-24 rounded-full bg-white/10 p-2.5 border border-white/20 mb-5 shadow-2xl shadow-orange-500/20 animate-pulse">
          <img
            src={logoEmblemImg}
            alt="DISHA Logo"
            className="w-full h-full object-contain rounded-full"
          />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white font-sans">DISHA</h1>
        <p className="text-xs text-orange-400 mt-2 font-medium tracking-wide">
          Verifying Secure Session…
        </p>
      </div>
    );
  }

  const renderSecondaryPage = () => {
    switch (currentPage) {
      case 'map':
        return <ViewMapPage onNavigate={handleNavigate} />;
      case 'report':
        return <ReportIncidentPage onNavigate={handleNavigate} isLoggedIn={isLoggedIn} />;
      case 'alerts':
        return <AlertsPage onNavigate={handleNavigate} />;
      case 'analysis':
        return <AnalysisPage currentPage={currentPage} onNavigate={handleNavigate} />;
      case 'graphs':
        return <GraphsAnalyticsPage onNavigate={handleNavigate} />;
      case 'news':
        return (
          <RecentNewsPage
            onNavigate={handleNavigate}
            onSelectNews={(article) => {
              setSelectedNewsArticle(article);
              setSelectedNewsId(article.id || article.article_id || article.event_id);
            }}
          />
        );
      case 'news-detail':
        return (
          <NewsDetailPage
            newsId={selectedNewsId}
            initialArticle={selectedNewsArticle}
            onNavigate={handleNavigate}
          />
        );
      case 'auth':
        return (
          <AuthPage
            onNavigate={handleNavigate}
            onLoginSuccess={handleLoginSuccess}
            redirectTarget={redirectAfterAuth}
            isLoggedIn={isLoggedIn}
          />
        );
      case 'nearby':
        return <NearbyIncidentsPage onNavigate={handleNavigate} />;
      default:
        return null;
    }
  };

  return (
    <ErrorBoundary title="DISHA Application Error">
      <NotificationToast notification={notification} onClose={clearNotification} />

      {/* APK Update Dialog Modal */}
      {updateModalInfo && (
        <AppUpdateModal
          updateInfo={updateModalInfo}
          onClose={() => setUpdateModalInfo(null)}
        />
      )}

      {/* 
        Keep LandingPage permanently mounted in the DOM to preserve Leaflet map state,
        zoom level, filters, and avoid destruction/recreation cycles during navigation.
        Leaflet ResizeObserver in LiveDisasterMap recalculates container dimensions
        automatically when switching back to display: block.
      */}
      <div
        id="disha-landing-page-container"
        className="pb-16 md:pb-0"
        style={{ display: currentPage === 'landing' ? 'block' : 'none' }}
      >
        <LandingPage
          currentPage={currentPage}
          onNavigate={handleNavigate}
          isLoggedIn={isLoggedIn}
          currentUser={user}
          onLogout={handleLogout}
          focusedEvent={focusedEvent}
          onClearFocusEvent={() => setFocusedEvent(null)}
        />
      </div>

      {currentPage !== 'landing' && (
        <div className="pb-16 md:pb-0">
          {renderSecondaryPage()}
        </div>
      )}

      {/* Adaptive Mobile Bottom Navigation Bar (Visible only on < md screens and hidden on auth screen) */}
      {currentPage !== 'auth' && (
        <MobileBottomNav
          currentPage={currentPage}
          onNavigate={handleNavigate}
          isLoggedIn={isLoggedIn}
        />
      )}
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <TimeRangeProvider>
        <AppContent />
      </TimeRangeProvider>
    </AuthProvider>
  );
}
