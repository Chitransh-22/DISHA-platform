import React, { useState } from 'react';
import {
  ArrowLeft, CheckCircle, Loader2, Shield, AlertCircle,
  Radio, MapPin, Activity, ExternalLink
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

// ─── Google Sign-In Button ───────────────────────────────────────────────────
const GoogleButton = ({ onClick, text = 'Continue with Google', disabled = false, loading = false }) => (
  <button
    id="google-oauth-btn"
    type="button"
    onClick={onClick}
    disabled={disabled || loading}
    className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-300 hover:border-slate-400 disabled:opacity-60 text-slate-700 font-semibold py-3.5 px-4 rounded-2xl shadow-xs transition-all cursor-pointer text-sm sm:text-base hover:shadow-md"
  >
    {loading ? (
      <Loader2 className="w-5 h-5 animate-spin text-orange-500" />
    ) : (
      <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
        />
      </svg>
    )}
    <span>{loading ? 'Connecting to Google…' : text}</span>
  </button>
);

// ─── Single Google Sign-In Panel ──────────────────────────────────────────────
const GoogleSignInPanel = ({ onGoogleClick, error, loading }) => {
  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold text-slate-800">
          Sign In to DISHA
        </h2>
        <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
          National Disaster Intelligence & Situational Hazard Awareness Network
        </p>
      </div>

      {/* Error Alert if any */}
      {error && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2.5 text-xs text-red-700">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block">Authentication Notice</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Prominent Google Sign-In Action */}
      <div className="pt-2">
        <GoogleButton
          onClick={onGoogleClick}
          text="Continue with Google"
          disabled={loading}
          loading={loading}
        />
        <p className="text-center text-[11px] text-slate-400 mt-2.5">
          Fast, secure, one-click sign-in with your Google account.
        </p>
      </div>

      {/* Platform Features / Capabilities */}
      <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 space-y-2.5 text-xs text-slate-600">
        <p className="font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
          With your DISHA Account:
        </p>
        <div className="flex items-center gap-2.5 text-slate-600">
          <Radio className="w-4 h-4 text-orange-500 shrink-0" />
          <span>Real-time early warnings and multi-hazard threat alerts</span>
        </div>
        <div className="flex items-center gap-2.5 text-slate-600">
          <MapPin className="w-4 h-4 text-red-500 shrink-0" />
          <span>Crowdsourced geo-tagged emergency hazard reporting</span>
        </div>
        <div className="flex items-center gap-2.5 text-slate-600">
          <Activity className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Verified responder coordination & AI situational analysis</span>
        </div>
      </div>
    </div>
  );
};

// ─── Success Screen ────────────────────────────────────────────────────────────
const SuccessScreen = ({ name, onNavigate, redirectTarget = 'report' }) => (
  <div className="text-center py-6">
    <div className="w-20 h-20 rounded-full bg-emerald-100 border-2 border-emerald-300 flex items-center justify-center mx-auto mb-5">
      <CheckCircle className="w-10 h-10 text-emerald-500" />
    </div>
    <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome, {name}! 🎉</h2>
    <p className="text-slate-500 text-sm mb-8 leading-relaxed">
      Your Google account is authenticated and active.<br />You can now report hazards and monitor live disaster feeds.
    </p>
    <div className="space-y-3">
      <button
        id="go-report-btn"
        onClick={() => onNavigate(redirectTarget || 'report')}
        className="w-full flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 text-white font-bold py-3.5 rounded-xl shadow-md shadow-orange-200 transition-opacity hover:opacity-90 cursor-pointer"
      >
        {redirectTarget === 'report' ? 'Proceed to Report Incident' : 'Continue to Dashboard'}
      </button>
      <button
        id="go-home-from-auth-btn"
        onClick={() => onNavigate('landing')}
        className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold py-3.5 rounded-xl transition-colors cursor-pointer"
      >
        Back to Home
      </button>
    </div>
  </div>
);

// ─── Main AuthPage ─────────────────────────────────────────────────────────────
export const AuthPage = ({ onNavigate, onLoginSuccess, redirectTarget = 'landing' }) => {
  const { googleLogin, authError, clearAuthError } = useAuth();
  const [screen, setScreen] = useState('signin');
  const [userName, setUserName] = useState('');
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleGoogleAuth = () => {
    clearAuthError();
    setIsRedirecting(true);
    googleLogin(redirectTarget);
  };

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-8">
      <div className="max-w-md mx-auto w-full">

        {/* ── Header ── */}
        <div className="flex items-center gap-4 mb-8">
          <button
            id="back-to-home-btn"
            onClick={() => onNavigate(redirectTarget || 'landing')}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm px-4 py-2 rounded-xl shadow-sm border border-slate-200 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-orange-400 to-red-500 flex items-center justify-center shadow-xs">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              {screen === 'success' ? 'Account Ready' : 'DISHA Portal'}
            </h1>
          </div>
        </div>

        {/* ── Main Auth Card ── */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-md">
          {screen === 'signin' && (
            <GoogleSignInPanel
              onGoogleClick={handleGoogleAuth}
              error={authError}
              loading={isRedirecting}
            />
          )}

          {screen === 'success' && (
            <SuccessScreen
              name={userName}
              onNavigate={onNavigate}
              redirectTarget={redirectTarget}
            />
          )}
        </div>

        {/* ── Trust Badges ── */}
        {screen !== 'success' && (
          <div className="flex items-center justify-center gap-6 mt-6 text-xs text-slate-400">
            {['🔒 Secure OAuth 2.0', '🛡️ DISHA Verified', '🇮🇳 Govt. Platform'].map((b, i) => (
              <span key={i} className="font-medium">{b}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
