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
} from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  const clearAuthError = useCallback(() => setAuthError(null), []);

  /**
   * Loads user profile using the current access token.
   */
  const refreshUser = useCallback(async () => {
    try {
      const data = await authGetMe();
      if (data?.user) {
        setUser(data.user);
        return data.user;
      }
    } catch (err) {
      setUser(null);
      setAccessToken(null);
    }
    return null;
  }, []);

  /**
   * Initializes session on application startup:
   * 1. Checks for Google OAuth redirect callback (?access_token=... or ?error=...)
   * 2. Otherwise attempts silent token refresh if session flag exists
   */
  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      try {
        const searchParams = new URLSearchParams(window.location.search);
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        const tokenFromUrl = searchParams.get('access_token') || hashParams.get('access_token');
        const errorFromUrl = searchParams.get('error') || hashParams.get('error');

        // Handle Google OAuth Callback
        if (tokenFromUrl) {
          setAccessToken(tokenFromUrl);
          
          // Remove access token from URL immediately to prevent exposure in history
          const cleanPath = window.location.pathname.replace(/\/auth\/google\/success\/?/, '/') || '/';
          window.history.replaceState({}, document.title, cleanPath);

          const profile = await authGetMe().catch(() => null);
          if (isMounted && profile?.user) {
            setUser(profile.user);
          }
          if (isMounted) setIsLoading(false);
          return;
        }

        if (errorFromUrl) {
          const cleanPath = window.location.pathname.replace(/\/auth\/google\/success\/?/, '/') || '/';
          window.history.replaceState({}, document.title, cleanPath);
          if (isMounted) {
            setAuthError(decodeURIComponent(errorFromUrl));
            setIsLoading(false);
          }
          return;
        }

        // Silent refresh on startup if session flag is set
        if (localStorage.getItem('disha_has_session') === 'true') {
          try {
            const refreshRes = await authRefreshToken();
            if (refreshRes?.access_token) {
              const profile = await authGetMe();
              if (isMounted && profile?.user) {
                setUser(profile.user);
              }
            }
          } catch (e) {
            if (isMounted) {
              setUser(null);
              setAccessToken(null);
            }
          }
        }
      } catch (err) {
        if (isMounted) {
          setUser(null);
          setAccessToken(null);
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
    } else {
      await refreshUser();
    }
    return data;
  }, [refreshUser]);

  /**
   * Ingest token directly (e.g. from Google OAuth).
   */
  const loginWithToken = useCallback(async (token) => {
    setAccessToken(token);
    return await refreshUser();
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
    return await authVerifyEmail({ email, otp });
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
    await authLogout();
    setUser(null);
    setAccessToken(null);
  }, []);

  /**
   * Log out all active sessions across devices.
   */
  const logoutAll = useCallback(async () => {
    await authLogoutAll();
    setUser(null);
    setAccessToken(null);
  }, []);

  const value = {
    user,
    accessToken: getAccessToken(),
    isLoggedIn: !!user,
    isLoading,
    authError,
    setAuthError,
    clearAuthError,
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
