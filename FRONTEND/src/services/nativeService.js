import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';
import { StatusBar, Style } from '@capacitor/status-bar';
import { Network } from '@capacitor/network';
import { Browser } from '@capacitor/browser';

/**
 * Returns true if running natively inside Android or iOS via Capacitor.
 */
export const isNativePlatform = () => {
  return Capacitor.isNativePlatform();
};

/**
 * Returns true if running specifically on Android.
 */
export const isAndroid = () => {
  return Capacitor.getPlatform() === 'android';
};

/**
 * Initialize native device integrations (Status Bar, Safe Overlays).
 */
export const initializeNativeApp = async () => {
  if (!isNativePlatform()) return;

  try {
    // Configure system status bar
    await StatusBar.setStyle({ style: Style.Dark });
    await StatusBar.setBackgroundColor({ color: '#101318' });
    await StatusBar.setOverlaysWebView({ overlay: false });
  } catch (err) {
    console.warn('[DISHA Native] StatusBar init note:', err);
  }
};

/**
 * Sets up the native Android hardware back button handler.
 * @param {Function} getCurrentState - Function returning { currentPage, isLoggedIn, isModalOpen, closeModal }
 * @param {Function} onNavigate - Navigation handler
 */
export const registerBackButtonHandler = (getCurrentState, onNavigate) => {
  if (!isNativePlatform()) return () => {};

  const backListener = App.addListener('backButton', ({ canGoBack }) => {
    const state = getCurrentState();
    const { currentPage, isLoggedIn, isModalOpen, closeModal } = state;

    // 1. If an active modal is open, dismiss the modal first
    if (isModalOpen && typeof closeModal === 'function') {
      closeModal();
      return;
    }

    // 2. If unauthenticated, user is on login screen; pressing back exits the app
    if (!isLoggedIn || currentPage === 'auth') {
      App.exitApp();
      return;
    }

    // 3. If on landing page (the root authenticated screen), pressing back exits the app
    if (currentPage === 'landing') {
      App.exitApp();
      return;
    }

    // 4. If on any secondary page (map, report, alerts, analysis, news), back returns to landing page
    if (currentPage !== 'landing') {
      onNavigate('landing');
      return;
    }

    // Fallback
    if (canGoBack) {
      window.history.back();
    } else {
      App.exitApp();
    }
  });

  return () => {
    backListener.then((sub) => sub.remove()).catch(() => {});
  };
};

/**
 * Registers network change listener to handle offline/online states.
 * @param {Function} onNetworkChange - callback receiving { connected, connectionType }
 */
export const registerNetworkListener = (onNetworkChange) => {
  if (!isNativePlatform()) {
    const handleOnline = () => onNetworkChange({ connected: true, connectionType: 'wifi' });
    const handleOffline = () => onNetworkChange({ connected: false, connectionType: 'none' });

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }

  const listener = Network.addListener('networkStatusChange', (status) => {
    onNetworkChange({
      connected: status.connected,
      connectionType: status.connectionType,
    });
  });

  return () => {
    listener.then((sub) => sub.remove()).catch(() => {});
  };
};

/**
 * Registers deep link listener for OAuth redirects (e.g., in.disha.app://auth/google/success?...)
 * @param {Function} onAuthCallback - callback receiving { accessToken, refreshToken, error }
 */
export const registerDeepLinkListener = (onAuthCallback) => {
  if (!isNativePlatform()) return () => {};

  const listener = App.addListener('appUrlOpen', async (event) => {
    try {
      const url = event?.url;
      if (!url) return;

      // Close In-App Browser if it was open for OAuth
      try {
        await Browser.close();
      } catch (e) {}

      // Check if URL is an auth redirect
      if (url.includes('/auth/google/success') || url.includes('access_token=') || url.includes('error=')) {
        const queryIdx = url.indexOf('?');
        const hashIdx = url.indexOf('#');
        const queryString = queryIdx !== -1 ? url.slice(queryIdx + 1) : '';
        const hashString = hashIdx !== -1 ? url.slice(hashIdx + 1) : '';

        const params = new URLSearchParams(queryString || hashString);
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        const error = params.get('error');

        onAuthCallback({
          accessToken,
          refreshToken,
          error: error ? decodeURIComponent(error) : null,
        });
      }
    } catch (err) {
      console.warn('[DISHA Native] Deep link parse notice:', err);
    }
  });

  return () => {
    listener.then((sub) => sub.remove()).catch(() => {});
  };
};

/**
 * Opens an external URL safely in the system browser or In-App Browser.
 */
export const openExternalUrl = async (url) => {
  if (isNativePlatform()) {
    try {
      await Browser.open({ url, windowName: '_system' });
      return;
    } catch (e) {
      console.warn('[DISHA Native] Browser open fallback:', e);
    }
  }
  window.open(url, '_blank', 'noopener,noreferrer');
};
