import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  authLogin,
  authRegister,
  authVerifyEmail,
  authResendOtp,
  authRefreshToken,
  authGetMe,
  authLogout,
  authLogoutAll,
  authGoogleLoginUrl,
  setAccessToken,
  getAccessToken,
  getRefreshToken,
  getStoredUser,
  setStoredUser,
} from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => getStoredUser());
  const [isLoading, setIsLoading] = useState(() => {
    // Only start in loading state if there's no stored user but a session or token exists to check
    return !getStoredUser() && (!!getAccessToken() || localStorage.getItem('disha_has_session') === 'true');
  });
  const [authError, setAuthError] = useState(null);
  const [notification, setNotification] = useState(null);

  const clearAuthError = useCallback(() => setAuthError(null), []);
  const clearNotification = useCallback(() => setNotification(null), []);
  const showNotification = useCallback((type, message) => {
    setNotification({ type, message });
  }, []);

  /**
   * Loads user profile using the current access token.
   */
  const refreshUser = useCallback(async () => {
    try {
      const data = await authGetMe();
      if (data?.user) {
        setUser(data.user);
        setStoredUser(data.user);
        return data.user;
      }
    } catch (err) {
      setUser(null);
      setStoredUser(null);
      setAccessToken(null, null);
    }
    return null;
  }, []);

  /**
   * Initializes session on application startup:
   * 1. Checks for Google OAuth redirect callback (?access_token=... or ?error=...)
   * 2. Validates existing access token or attempts silent token refresh
   */
  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      try {
        const searchParams = new URLSearchParams(window.location.search);
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        const tokenFromUrl = searchParams.get('access_token') || hashParams.get('access_token');
        const refreshTokenFromUrl = searchParams.get('refresh_token') || hashParams.get('refresh_token');
        const errorFromUrl = searchParams.get('error') || hashParams.get('error');

        // 1. Handle Google OAuth Callback Success
        if (tokenFromUrl) {
          setAccessToken(tokenFromUrl, refreshTokenFromUrl || null);
          
          // Remove access token from URL immediately to prevent exposure in browser history
          const cleanPath = window.location.pathname.replace(/\/auth\/google\/success\/?/, '/') || '/';
          window.history.replaceState({}, document.title, cleanPath);

          const profile = await authGetMe().catch(() => null);
          if (isMounted && profile?.user) {
            setUser(profile.user);
            setStoredUser(profile.user);
            setNotification({
              type: 'success',
              message: 'Sign in successful',
            });
          }
          if (isMounted) setIsLoading(false);
          return;
        }

        // 2. Handle Google OAuth Callback Error
        if (errorFromUrl) {
          const cleanPath = window.location.pathname.replace(/\/auth\/google\/success\/?/, '/') || '/';
          window.history.replaceState({}, document.title, cleanPath);
          if (isMounted) {
            setAuthError(decodeURIComponent(errorFromUrl));
            setNotification({
              type: 'error',
              message: decodeURIComponent(errorFromUrl),
            });
            setIsLoading(false);
          }
          return;
        }

        // 3. Validate existing access token or attempt silent refresh
        const existingToken = getAccessToken();
        if (existingToken) {
          try {
            const profile = await authGetMe();
            if (isMounted && profile?.user) {
              setUser(profile.user);
              setStoredUser(profile.user);
            }
          } catch (e) {
            // Token might be expired, attempt silent refresh
            try {
              const refreshRes = await authRefreshToken();
              if (refreshRes?.access_token) {
                const profile = await authGetMe();
                if (isMounted && profile?.user) {
                  setUser(profile.user);
                  setStoredUser(profile.user);
                }
              }
            } catch (refreshErr) {
              if (isMounted) {
                setUser(null);
                setStoredUser(null);
                setAccessToken(null, null);
              }
            }
          }
        } else if (localStorage.getItem('disha_has_session') === 'true' || getRefreshToken()) {
          try {
            const refreshRes = await authRefreshToken();
            if (refreshRes?.access_token) {
              const profile = await authGetMe();
              if (isMounted && profile?.user) {
                setUser(profile.user);
                setStoredUser(profile.user);
              }
            }
          } catch (e) {
            if (isMounted) {
              setUser(null);
              setStoredUser(null);
              setAccessToken(null, null);
            }
          }
        }
      } catch (err) {
        if (isMounted) {
          setUser(null);
          setStoredUser(null);
          setAccessToken(null, null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Log in with email and password.
   */
  const login = useCallback(async ({ email, password }) => {
    setAuthError(null);
    const data = await authLogin({ email, password });
    if (data?.user) {
      setUser(data.user);
      setStoredUser(data.user);
      setNotification({
        type: 'success',
        message: 'Sign in successful',
      });
    } else {
      await refreshUser();
      setNotification({
        type: 'success',
        message: 'Sign in successful',
      });
    }
    return data;
  }, [refreshUser]);

  /**
   * Ingest token directly (e.g. from Google OAuth).
   */
  const loginWithToken = useCallback(async (token, refreshToken = null) => {
    setAccessToken(token, refreshToken);
    const u = await refreshUser();
    if (u) {
      setNotification({
        type: 'success',
        message: 'Sign in successful',
      });
    }
    return u;
  }, [refreshUser]);

  /**
   * Register a new account.
   */
  const register = useCallback(async (userData) => {
    setAuthError(null);
    return await authRegister(userData);
  }, []);

  /**
   * Verify email OTP.
   */
  const verifyEmail = useCallback(async ({ email, otp }) => {
    setAuthError(null);
    const res = await authVerifyEmail({ email, otp });
    if (res?.user) {
      setUser(res.user);
      setStoredUser(res.user);
      setNotification({
        type: 'success',
        message: 'Sign in successful',
      });
    }
    return res;
  }, []);

  /**
   * Resend verification OTP.
   */
  const resendOtp = useCallback(async (email) => {
    return await authResendOtp(email);
  }, []);

  /**
   * Redirects browser to Google OAuth initiate route.
   */
  const googleLogin = useCallback((target = null) => {
    if (target) {
      try {
        sessionStorage.setItem('disha_auth_redirect', target);
      } catch (e) {}
    }
    window.location.href = authGoogleLoginUrl();
  }, []);

  /**
   * Log out current session.
   */
  const logout = useCallback(async () => {
    setNotification(null);
    await authLogout();
    setUser(null);
    setAccessToken(null, null);
    setStoredUser(null);
  }, []);

  /**
   * Log out all active sessions across devices.
   */
  const logoutAll = useCallback(async () => {
    setNotification(null);
    await authLogoutAll();
    setUser(null);
    setAccessToken(null, null);
    setStoredUser(null);
  }, []);

  const value = {
    user,
    accessToken: getAccessToken(),
    isLoggedIn: !!user,
    isLoading,
    authError,
    setAuthError,
    clearAuthError,
    notification,
    showNotification,
    clearNotification,
    login,
    loginWithToken,
    register,
    verifyEmail,
    resendOtp,
    googleLogin,
    logout,
    logoutAll,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
