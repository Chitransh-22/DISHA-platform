import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowLeft, User, Mail, Lock, Eye, EyeOff, Phone,
  MapPin, CheckCircle, Loader2, Shield, KeyRound,
  ArrowRight, RefreshCw, UserPlus
} from 'lucide-react';

// ─── Helpers ──────────────────────────────────────────────────────────────────
const generateOTP = () => Math.floor(100000 + Math.random() * 900000).toString();

const InputField = ({ id, label, type = 'text', value, onChange, placeholder, icon: Icon, error, rightEl, disabled }) => (
  <div>
    <label htmlFor={id} className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">
      {label}
    </label>
    <div className="relative">
      {Icon && (
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <Icon className="w-4 h-4" />
        </span>
      )}
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full bg-slate-50 border rounded-xl py-3 text-sm text-slate-800 placeholder:text-slate-400
          focus:outline-none focus:ring-2 focus:ring-orange-300 focus:border-orange-400 transition-all
          disabled:opacity-50 disabled:cursor-not-allowed
          ${Icon ? 'pl-10' : 'pl-4'} ${rightEl ? 'pr-12' : 'pr-4'}
          ${error ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}
      />
      {rightEl && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2">{rightEl}</span>
      )}
    </div>
    {error && <p className="text-red-500 text-xs mt-1.5">{error}</p>}
  </div>
);

// ─── Sign In Panel ─────────────────────────────────────────────────────────────
const SignInPanel = ({ onSuccess, onSwitch }) => {
  const [form, setForm] = useState({ email: '', password: '' });
  const [showPass, setShowPass] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const validate = () => {
    const e = {};
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) e.email = 'Enter a valid email address.';
    if (form.password.length < 6) e.password = 'Password must be at least 6 characters.';
    setErrors(e);
    return !Object.keys(e).length;
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setLoading(true);
    await new Promise(r => setTimeout(r, 1500));
    setLoading(false);
    onSuccess(form.email.split('@')[0]);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <InputField
        id="signin-email" label="Email Address" type="email"
        value={form.email} onChange={set('email')}
        placeholder="you@example.com" icon={Mail} error={errors.email}
      />
      <InputField
        id="signin-password" label="Password" type={showPass ? 'text' : 'password'}
        value={form.password} onChange={set('password')}
        placeholder="••••••••" icon={Lock} error={errors.password}
        rightEl={
          <button type="button" onClick={() => setShowPass(p => !p)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        }
      />

      <div className="text-right">
        <button type="button" className="text-xs text-orange-500 hover:text-orange-600 font-semibold cursor-pointer">
          Forgot password?
        </button>
      </div>

      <button
        id="signin-submit-btn" type="submit" disabled={loading}
        className="w-full flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:opacity-60 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-orange-200 transition-all cursor-pointer"
      >
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Signing In…</> : <><ArrowRight className="w-4 h-4" /> Sign In</>}
      </button>

      <p className="text-center text-sm text-slate-500">
        Don't have an account?{' '}
        <button type="button" onClick={onSwitch} className="text-orange-500 hover:text-orange-600 font-bold cursor-pointer">
          Sign Up
        </button>
      </p>
    </form>
  );
};

// ─── OTP Verification Panel ────────────────────────────────────────────────────
const OTPPanel = ({ email, onVerified, onBack }) => {
  const REAL_OTP = useRef(generateOTP());
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(30);
  const inputRefs = useRef([]);

  // Countdown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  const handleDigit = (i, val) => {
    if (!/^\d?$/.test(val)) return;
    const next = [...digits];
    next[i] = val;
    setDigits(next);
    setError('');
    if (val && i < 5) inputRefs.current[i + 1]?.focus();
  };

  const handleKeyDown = (i, e) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) {
      inputRefs.current[i - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setDigits(pasted.split(''));
      inputRefs.current[5]?.focus();
    }
    e.preventDefault();
  };

  const handleVerify = async () => {
    const entered = digits.join('');
    if (entered.length < 6) { setError('Please enter all 6 digits.'); return; }
    setLoading(true);
    await new Promise(r => setTimeout(r, 1200));
    setLoading(false);
    // For demo: any 6-digit code passes, or match REAL_OTP
    if (entered === REAL_OTP.current || entered.length === 6) {
      onVerified();
    } else {
      setError('Incorrect OTP. Please try again.');
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    }
  };

  const handleResend = () => {
    REAL_OTP.current = generateOTP();
    setDigits(['', '', '', '', '', '']);
    setError('');
    setResendCooldown(30);
    inputRefs.current[0]?.focus();
  };

  return (
    <div className="space-y-5">
      <div className="text-center">
        <div className="w-14 h-14 rounded-2xl bg-linear-to-br from-orange-400 to-red-500 flex items-center justify-center mx-auto mb-3 shadow-md shadow-orange-200">
          <KeyRound className="w-7 h-7 text-white" />
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">
          We sent a 6-digit OTP to<br />
          <span className="font-bold text-slate-800">{email}</span>
        </p>
        <p className="text-xs text-slate-400 mt-1">(Check your inbox or spam folder)</p>
      </div>

      {/* OTP Boxes */}
      <div className="flex gap-2 justify-center" onPaste={handlePaste}>
        {digits.map((d, i) => (
          <input
            key={i}
            ref={el => inputRefs.current[i] = el}
            id={`otp-digit-${i}`}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={d}
            onChange={e => handleDigit(i, e.target.value)}
            onKeyDown={e => handleKeyDown(i, e)}
            className={`w-11 h-13 text-center text-xl font-bold border rounded-xl bg-slate-50
              focus:outline-none focus:ring-2 focus:ring-orange-300 focus:border-orange-400 transition-all
              ${error ? 'border-red-300 bg-red-50' : 'border-slate-200'}`}
          />
        ))}
      </div>
      {error && <p className="text-red-500 text-xs text-center">{error}</p>}

      <button
        id="verify-otp-btn"
        onClick={handleVerify} disabled={loading}
        className="w-full flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:opacity-60 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-orange-200 transition-all cursor-pointer"
      >
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Verifying…</> : <><CheckCircle className="w-4 h-4" /> Verify OTP</>}
      </button>

      <div className="flex items-center justify-between text-sm">
        <button type="button" onClick={onBack} className="text-slate-500 hover:text-slate-700 font-medium cursor-pointer flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        <button
          type="button" onClick={handleResend} disabled={resendCooldown > 0}
          className="flex items-center gap-1.5 text-orange-500 hover:text-orange-600 font-semibold disabled:text-slate-400 disabled:cursor-not-allowed cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend OTP'}
        </button>
      </div>
    </div>
  );
};

// ─── Sign Up Panel ─────────────────────────────────────────────────────────────
const SignUpPanel = ({ onOTPRequired, onSwitch }) => {
  const [form, setForm] = useState({
    name: '', phone: '', email: '', city: '', pincode: '', password: '', confirm: ''
  });
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const validate = () => {
    const e = {};
    if (!form.name.trim() || form.name.trim().length < 2) e.name = 'Enter your full name.';
    if (!form.phone.match(/^[6-9]\d{9}$/)) e.phone = 'Enter a valid 10-digit Indian mobile number.';
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) e.email = 'Enter a valid email address.';
    if (!form.city.trim()) e.city = 'Enter your city name.';
    if (!form.pincode.match(/^\d{6}$/)) e.pincode = 'Enter a valid 6-digit PIN code.';
    if (form.password.length < 8) e.password = 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(form.password)) e.password = 'Password needs at least one uppercase letter.';
    if (!/\d/.test(form.password)) e.password = 'Password needs at least one number.';
    if (form.password !== form.confirm) e.confirm = 'Passwords do not match.';
    setErrors(e);
    return !Object.keys(e).length;
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    if (!validate()) return;
    setLoading(true);
    await new Promise(r => setTimeout(r, 1000)); // simulate sending OTP
    setLoading(false);
    onOTPRequired(form.email, form.name);
  };

  const passStrength = (() => {
    const p = form.password;
    if (!p) return null;
    let s = 0;
    if (p.length >= 8) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/\d/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    if (s <= 1) return { label: 'Weak', color: 'bg-red-400', w: 'w-1/4' };
    if (s === 2) return { label: 'Fair', color: 'bg-amber-400', w: 'w-2/4' };
    if (s === 3) return { label: 'Good', color: 'bg-blue-400', w: 'w-3/4' };
    return { label: 'Strong', color: 'bg-emerald-400', w: 'w-full' };
  })();

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <InputField id="signup-name" label="Full Name" value={form.name} onChange={set('name')}
        placeholder="Aarav Sharma" icon={User} error={errors.name} />

      <InputField id="signup-phone" label="Mobile Number" type="tel" value={form.phone} onChange={set('phone')}
        placeholder="98XXXXXXXX" icon={Phone} error={errors.phone} />

      <InputField id="signup-email" label="Email Address" type="email" value={form.email} onChange={set('email')}
        placeholder="you@example.com" icon={Mail} error={errors.email} />

      {/* Location Row */}
      <div className="grid grid-cols-2 gap-3">
        <InputField id="signup-city" label="City" value={form.city} onChange={set('city')}
          placeholder="Mumbai" icon={MapPin} error={errors.city} />
        <InputField id="signup-pincode" label="PIN Code" value={form.pincode} onChange={set('pincode')}
          placeholder="400001" error={errors.pincode} />
      </div>

      {/* Password */}
      <div>
        <InputField id="signup-password" label="Password" type={showPass ? 'text' : 'password'}
          value={form.password} onChange={set('password')}
          placeholder="Min 8 chars, 1 upper, 1 number" icon={Lock} error={errors.password}
          rightEl={
            <button type="button" onClick={() => setShowPass(p => !p)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
              {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          }
        />
        {passStrength && (
          <div className="mt-2 flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-300 ${passStrength.color} ${passStrength.w}`} />
            </div>
            <span className="text-xs font-semibold text-slate-500">{passStrength.label}</span>
          </div>
        )}
      </div>

      <InputField id="signup-confirm" label="Confirm Password" type={showConfirm ? 'text' : 'password'}
        value={form.confirm} onChange={set('confirm')}
        placeholder="Re-enter password" icon={Lock} error={errors.confirm}
        rightEl={
          <button type="button" onClick={() => setShowConfirm(p => !p)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
            {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        }
      />

      <p className="text-xs text-slate-400 leading-relaxed pt-1">
        An OTP will be sent to your email for verification.
      </p>

      <button
        id="signup-submit-btn" type="submit" disabled={loading}
        className="w-full flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:opacity-60 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-orange-200 transition-all cursor-pointer"
      >
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending OTP…</> : <><UserPlus className="w-4 h-4" /> Create Account</>}
      </button>

      <p className="text-center text-sm text-slate-500">
        Already have an account?{' '}
        <button type="button" onClick={onSwitch} className="text-orange-500 hover:text-orange-600 font-bold cursor-pointer">
          Sign In
        </button>
      </p>
    </form>
  );
};

// ─── Success Screen ────────────────────────────────────────────────────────────
const SuccessScreen = ({ name, onNavigate }) => (
  <div className="text-center py-6">
    <div className="w-20 h-20 rounded-full bg-emerald-100 border-2 border-emerald-300 flex items-center justify-center mx-auto mb-5">
      <CheckCircle className="w-10 h-10 text-emerald-500" />
    </div>
    <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome, {name}! 🎉</h2>
    <p className="text-slate-500 text-sm mb-8 leading-relaxed">
      Your account is verified and ready.<br />You can now report incidents and track alerts.
    </p>
    <div className="space-y-3">
      <button
        id="go-report-btn"
        onClick={() => onNavigate('report')}
        className="w-full flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 text-white font-bold py-3.5 rounded-xl shadow-md shadow-orange-200 transition-opacity hover:opacity-90 cursor-pointer"
      >
        Report an Incident
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
export const AuthPage = ({ onNavigate, onLoginSuccess }) => {
  // 'signin' | 'signup' | 'otp' | 'success'
  const [screen, setScreen] = useState('signin');
  const [otpEmail, setOtpEmail] = useState('');
  const [userName, setUserName] = useState('');

  const handleOTPRequired = (email, name) => {
    setOtpEmail(email);
    setUserName(name);
    setScreen('otp');
  };

  // Called after OTP verified (sign-up) or password check (sign-in)
  const handleAuthSuccess = (name) => {
    setUserName(name);
    setScreen('success');
    if (onLoginSuccess) onLoginSuccess();
  };

  const handleOTPVerified = () => handleAuthSuccess(userName);
  const handleSignInSuccess = (name) => handleAuthSuccess(name);

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-8">
      <div className="max-w-md mx-auto w-full">

        {/* ── Header ── */}
        <div className="flex items-center gap-4 mb-8">
          <button
            id="back-to-home-btn"
            onClick={() => onNavigate('landing')}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm px-4 py-2 rounded-xl shadow-sm border border-slate-200 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-orange-400 to-red-500 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              {screen === 'success' ? 'Account Ready' : screen === 'otp' ? 'Verify Email' : 'DISHA Account'}
            </h1>
          </div>
        </div>

        {/* ── Card ── */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-md">

          {/* Tab switcher (only for signin / signup) */}
          {(screen === 'signin' || screen === 'signup') && (
            <div className="flex bg-slate-100 rounded-2xl p-1 mb-6">
              {['signin', 'signup'].map(tab => (
                <button
                  key={tab}
                  id={`tab-${tab}-btn`}
                  onClick={() => setScreen(tab)}
                  className={`flex-1 py-2.5 text-sm font-bold rounded-xl transition-all cursor-pointer
                    ${screen === tab ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  {tab === 'signin' ? 'Sign In' : 'Sign Up'}
                </button>
              ))}
            </div>
          )}

          {/* ── Screen Router ── */}
          {screen === 'signin' && (
            <SignInPanel onSuccess={handleSignInSuccess} onSwitch={() => setScreen('signup')} />
          )}
          {screen === 'signup' && (
            <SignUpPanel onOTPRequired={handleOTPRequired} onSwitch={() => setScreen('signin')} />
          )}
          {screen === 'otp' && (
            <OTPPanel email={otpEmail} onVerified={handleOTPVerified} onBack={() => setScreen('signup')} />
          )}
          {screen === 'success' && (
            <SuccessScreen name={userName} onNavigate={onNavigate} onGoReport={() => onNavigate('report')} />
          )}
        </div>

        {/* Trust badges */}
        {screen !== 'success' && (
          <div className="flex items-center justify-center gap-6 mt-6 text-xs text-slate-400">
            {['🔒 Encrypted', '🛡️ DISHA Verified', '🇮🇳 Govt. Platform'].map((b, i) => (
              <span key={i} className="font-medium">{b}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
