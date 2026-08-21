import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ArrowLeft, AlertTriangle, MapPin, ChevronDown, Image as ImageIcon,
  Camera, Upload, X, CheckCircle, Loader2, LogIn, Shield,
  FileText, Zap, Clock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { submitIncidentReport } from '../services/api';



// ─── Disaster categories ─────────────────────────────────────────────────────
const DISASTER_TYPES = [
  { value: '', label: 'Select event type…', emoji: '' },
  { value: 'flood', label: 'Flood', emoji: '🌊' },
  { value: 'cyclone', label: 'Cyclone / Tropical Storm', emoji: '🌀' },
  { value: 'earthquake', label: 'Earthquake', emoji: '🌍' },
  { value: 'landslide', label: 'Landslide / Mudslide', emoji: '⛰️' },
  { value: 'tsunami', label: 'Tsunami', emoji: '🌊' },
  { value: 'wildfire', label: 'Wildfire / Forest Fire', emoji: '🔥' },
  { value: 'drought', label: 'Drought', emoji: '☀️' },
  { value: 'heatwave', label: 'Heatwave', emoji: '🌡️' },
  { value: 'coldwave', label: 'Cold Wave / Frost', emoji: '❄️' },
  { value: 'lightning', label: 'Lightning Strike', emoji: '⚡' },
  { value: 'building_collapse', label: 'Building Collapse', emoji: '🏚️' },
  { value: 'road_accident', label: 'Road Accident', emoji: '🚗' },
  { value: 'industrial_accident', label: 'Industrial / Chemical Accident', emoji: '🏭' },
  { value: 'gas_leak', label: 'Gas Leak', emoji: '💨' },
  { value: 'power_outage', label: 'Power Outage', emoji: '🔌' },
  { value: 'bridge_collapse', label: 'Bridge Collapse', emoji: '🌉' },
  { value: 'dam_breach', label: 'Dam Breach', emoji: '🚧' },
  { value: 'riot', label: 'Civil Unrest / Riot', emoji: '⚠️' },
  { value: 'disease_outbreak', label: 'Disease Outbreak', emoji: '🦠' },
  { value: 'other', label: 'Other', emoji: '📋' },
];

// ─── Word count helper ────────────────────────────────────────────────────────
const countWords = (text) => text.trim().split(/\s+/).filter(Boolean).length;

// ─── Login Prompt ─────────────────────────────────────────────────────────────
const LoginPrompt = ({ onNavigate }) => (
  <div className="bg-white rounded-3xl p-8 sm:p-12 border border-slate-200/80 shadow-md flex flex-col items-center justify-center min-h-125 text-center">
    <div className="relative mb-6">
      <div className="w-20 h-20 rounded-3xl bg-linear-to-br from-orange-400 to-red-500 flex items-center justify-center shadow-lg shadow-orange-200">
        <Shield className="w-10 h-10 text-white" />
      </div>
      <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold">!</span>
    </div>

    <h2 className="text-2xl font-bold text-slate-900 mb-2">Sign In Required</h2>
    <p className="text-slate-500 max-w-sm mb-8 text-sm leading-relaxed">
      You must be logged in to submit an incident report. This helps us verify reports and keep our platform accountable.
    </p>

    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-md mb-8">
      {[
        { icon: <Zap className="w-4 h-4" />, label: 'Instant dispatch' },
        { icon: <Clock className="w-4 h-4" />, label: 'Track your report' },
        { icon: <CheckCircle className="w-4 h-4" />, label: 'Verified reports' },
      ].map((item, i) => (
        <div key={i} className="flex flex-col items-center gap-1.5 bg-orange-50 border border-orange-100 rounded-2xl py-4 px-3">
          <span className="text-[#ea580c]">{item.icon}</span>
          <span className="text-xs font-semibold text-slate-700">{item.label}</span>
        </div>
      ))}
    </div>

    <div className="flex flex-col sm:flex-row gap-3 w-full max-w-xs">
      <button
        id="login-to-report-btn"
        onClick={() => onNavigate('auth', 'report')}
        className="flex-1 flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white font-semibold text-sm px-5 py-3 rounded-xl shadow-md shadow-orange-200 transition-all duration-200 cursor-pointer"
      >
        <LogIn className="w-4 h-4" />
        Sign In
      </button>
      <button
        id="create-account-btn"
        onClick={() => onNavigate('auth', 'report')}
        className="flex-1 bg-slate-900 hover:bg-slate-700 text-white font-semibold text-sm px-5 py-3 rounded-xl transition-colors cursor-pointer"
      >
        Create Account
      </button>
    </div>
  </div>
);

// ─── Main Component ───────────────────────────────────────────────────────────
export const ReportIncidentPage = ({ onNavigate, isLoggedIn: propIsLoggedIn }) => {
  const { isLoggedIn: contextIsLoggedIn, user: contextUser } = useAuth();
  const isLoggedIn = propIsLoggedIn !== undefined ? propIsLoggedIn : contextIsLoggedIn;

  // ── form state ──
  const [location, setLocation] = useState({ lat: null, lng: null, address: '', loading: false, error: '' });
  const [eventType, setEventType] = useState('');
  const [description, setDescription] = useState('');
  const [images, setImages] = useState([]);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [reportId, setReportId] = useState('');

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  // ── auto-fetch GPS on mount ──
  useEffect(() => {
    if (!isLoggedIn) return;
    fetchGPS();
  }, [isLoggedIn]);

  const fetchGPS = useCallback(() => {
    if (!navigator.geolocation) {
      setLocation(prev => ({ ...prev, error: 'Geolocation is not supported by your browser.' }));
      return;
    }
    setLocation({ lat: null, lng: null, address: '', loading: true, error: '' });
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude: lat, longitude: lng } = pos.coords;
        let address = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`
          );
          const data = await res.json();
          if (data?.display_name) address = data.display_name;
        } catch (_) { /* use coordinate fallback */ }
        setLocation({ lat, lng, address, loading: false, error: '' });
      },
      (err) => {
        setLocation({ lat: null, lng: null, address: '', loading: false, error: 'Could not get location. ' + err.message });
      },
      { timeout: 10000 }
    );
  }, []);

  // ── word count ──
  const wordCount = countWords(description);
  const MAX_WORDS = 100;
  const wordPct = Math.min((wordCount / MAX_WORDS) * 100, 100);
  const wordColor = wordCount > MAX_WORDS ? 'text-red-500' : wordCount >= 80 ? 'text-amber-500' : 'text-slate-500';
  const barColor = wordCount > MAX_WORDS ? 'bg-red-400' : wordCount >= 80 ? 'bg-amber-400' : 'bg-emerald-400';

  // ── image helpers ──
  const handleImages = (files) => {
    const valid = Array.from(files).filter(f => f.type.startsWith('image/'));
    const readers = valid.slice(0, 5 - images.length).map(file => {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve({ url: reader.result, name: file.name });
        reader.readAsDataURL(file);
      });
    });
    Promise.all(readers).then(newImgs => setImages(prev => [...prev, ...newImgs]));
  };

  const removeImage = (index) => setImages(prev => prev.filter((_, i) => i !== index));

  // ── validation ──
  const validate = () => {
    const e = {};
    if (!location.lat && !location.address) e.location = 'Please capture your location.';
    if (!eventType) e.eventType = 'Please select an event type.';
    if (wordCount < 10) e.description = 'Please provide at least 10 words of description.';
    if (wordCount > MAX_WORDS) e.description = `Description exceeds ${MAX_WORDS} words (current: ${wordCount}).`;
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // ── submit ──
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitting(true);
    setErrors(prev => ({ ...prev, submit: '' }));

    try {
      const payload = {
        event_type: eventType,
        description: description.trim(),
        location: {
          lat: location.lat,
          lng: location.lng,
          latitude: location.lat,
          longitude: location.lng,
          address: location.address,
        },
        images: images.map(img => ({ name: img.name, url: img.url })),
      };

      const res = await submitIncidentReport(payload);
      const generatedId = res.report_id || res.report?.report_id || ('INC-' + Date.now().toString().slice(-6));
      setReportId(generatedId);
      setSubmitted(true);
    } catch (err) {
      setErrors(prev => ({
        ...prev,
        submit: err.message || 'Failed to submit incident report. Please check your connection and try again.',
      }));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Success Screen ──
  if (submitted) {
    return (
      <div className="min-h-screen bg-[#f5f2ea] flex flex-col p-4 sm:p-8">
        <div className="max-w-lg mx-auto w-full mt-16 text-center">
          <div className="bg-white rounded-3xl p-10 border border-slate-200/80 shadow-md">
            <div className="w-20 h-20 rounded-full bg-emerald-100 border-2 border-emerald-300 flex items-center justify-center mx-auto mb-5">
              <CheckCircle className="w-10 h-10 text-emerald-500" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-1">Report Submitted!</h2>
            <p className="text-slate-500 text-sm mb-4">Your incident has been logged and dispatched to the nearest response team.</p>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl px-6 py-3 inline-block mb-6">
              <span className="text-xs text-slate-400 font-medium">Report ID</span>
              <div className="text-lg font-bold text-[#ea580c] tracking-widest">{reportId}</div>
            </div>
            <ul className="text-left text-sm space-y-3 mb-8">
              {['Report received by DISHA', 'Nearest team notified', 'Estimated response in 15–30 min'].map((step, i) => (
                <li key={i} className="flex items-center gap-3">
                  <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span className="text-slate-700">{step}</span>
                </li>
              ))}
            </ul>
            <button
              id="report-another-btn"
              onClick={() => { setSubmitted(false); setEventType(''); setDescription(''); setImages([]); setErrors({}); }}
              className="w-full bg-linear-to-r from-orange-500 to-red-500 text-white font-semibold py-3 rounded-xl mb-3 cursor-pointer transition-opacity hover:opacity-90"
            >
              Report Another Incident
            </button>
            <button
              id="go-home-after-submit-btn"
              onClick={() => onNavigate('landing')}
              className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold py-3 rounded-xl cursor-pointer transition-colors"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-slate-900 flex flex-col p-4 sm:p-8">
      <div className="max-w-2xl mx-auto w-full">

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
              <AlertTriangle className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Report an Incident</h1>
          </div>
        </div>

        {/* ── Auth Gate ── */}
        {!isLoggedIn ? (
          <LoginPrompt onNavigate={onNavigate} />
        ) : (
          <form id="report-incident-form" onSubmit={handleSubmit} className="space-y-5">

            {/* ── 1. Location ── */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
              <label className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-3">
                <MapPin className="w-4 h-4 text-[#ea580c]" />
                Location
              </label>

              {location.loading ? (
                <div className="flex items-center gap-3 text-slate-500 text-sm py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-[#ea580c]" />
                  Detecting your location…
                </div>
              ) : location.lat ? (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-sm text-emerald-800 leading-snug">
                  <div className="font-semibold text-xs text-emerald-600 mb-0.5 uppercase tracking-wide">GPS Captured</div>
                  {location.address}
                  <div className="text-xs text-emerald-500 mt-1">{location.lat.toFixed(5)}, {location.lng.toFixed(5)}</div>
                </div>
              ) : location.error ? (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 mb-3">
                  {location.error}
                </div>
              ) : null}

              <button
                type="button"
                id="get-location-btn"
                onClick={fetchGPS}
                className="mt-3 flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors cursor-pointer"
              >
                <MapPin className="w-4 h-4" />
                {location.lat ? 'Re-capture Location' : 'Capture Current Location'}
              </button>
              {errors.location && <p className="text-red-500 text-xs mt-2">{errors.location}</p>}
            </div>

            {/* ── 2. Event Type ── */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
              <label htmlFor="event-type-select" className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-3">
                <AlertTriangle className="w-4 h-4 text-[#ea580c]" />
                Event Type
              </label>
              <div className="relative">
                <select
                  id="event-type-select"
                  value={eventType}
                  onChange={e => { setEventType(e.target.value); setErrors(prev => ({ ...prev, eventType: '' })); }}
                  className="w-full appearance-none bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pr-10 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-orange-300 focus:border-orange-400 cursor-pointer transition-all"
                >
                  {DISASTER_TYPES.map(d => (
                    <option key={d.value} value={d.value} disabled={d.value === ''}>
                      {d.emoji ? `${d.emoji}  ${d.label}` : d.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
              </div>
              {eventType && (
                <div className="mt-3 flex items-center gap-3 bg-orange-50 border border-orange-100 rounded-xl px-4 py-2.5">
                  <span className="text-xl">{DISASTER_TYPES.find(d => d.value === eventType)?.emoji}</span>
                  <div>
                    <div className="text-xs font-semibold text-orange-600 uppercase tracking-wide">Selected</div>
                    <div className="text-sm font-bold text-slate-800">{DISASTER_TYPES.find(d => d.value === eventType)?.label}</div>
                  </div>
                </div>
              )}
              {errors.eventType && <p className="text-red-500 text-xs mt-2">{errors.eventType}</p>}
            </div>

            {/* ── 3. Description ── */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
              <label htmlFor="description-textarea" className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-3">
                <FileText className="w-4 h-4 text-[#ea580c]" />
                Description
                <span className="text-xs font-normal text-slate-400 ml-auto">max 100 words</span>
              </label>
              <textarea
                id="description-textarea"
                value={description}
                onChange={e => { setDescription(e.target.value); setErrors(prev => ({ ...prev, description: '' })); }}
                rows={5}
                placeholder="Describe what happened, severity, number of people affected, immediate hazards…"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-300 focus:border-orange-400 resize-none transition-all"
              />
              {/* Word count bar */}
              <div className="mt-2 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-300 ${barColor}`} style={{ width: `${wordPct}%` }} />
                </div>
                <span className={`text-xs font-semibold tabular-nums ${wordColor}`}>{wordCount}/{MAX_WORDS}</span>
              </div>
              {errors.description && <p className="text-red-500 text-xs mt-2">{errors.description}</p>}
            </div>

            {/* ── 4. Images ── */}
            <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
              <label className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-1">
                <ImageIcon className="w-4 h-4 text-[#ea580c]" />
                Photos
                <span className="text-xs font-normal text-slate-400 ml-auto">optional · up to 5</span>
              </label>
              <p className="text-xs text-slate-400 mb-4">Add photos or video frames as evidence. Use the camera or upload from your device.</p>

              {/* Hidden inputs */}
              <input ref={fileInputRef} type="file" accept="image/*" multiple className="hidden"
                onChange={e => handleImages(e.target.files)} />
              <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" className="hidden"
                onChange={e => handleImages(e.target.files)} />

              <div className="flex gap-3 mb-4">
                <button type="button" id="capture-camera-btn"
                  onClick={() => cameraInputRef.current?.click()}
                  disabled={images.length >= 5}
                  className="flex-1 flex items-center justify-center gap-2 border-2 border-dashed border-slate-300 hover:border-orange-400 hover:bg-orange-50 text-slate-600 hover:text-orange-600 font-semibold text-sm py-3 rounded-xl transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Camera className="w-4 h-4" /> Take Photo
                </button>
                <button type="button" id="upload-image-btn"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={images.length >= 5}
                  className="flex-1 flex items-center justify-center gap-2 border-2 border-dashed border-slate-300 hover:border-orange-400 hover:bg-orange-50 text-slate-600 hover:text-orange-600 font-semibold text-sm py-3 rounded-xl transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Upload className="w-4 h-4" /> Upload
                </button>
              </div>

              {images.length > 0 && (
                <div className="grid grid-cols-3 gap-2">
                  {images.map((img, i) => (
                    <div key={i} className="relative group aspect-square rounded-xl overflow-hidden border border-slate-200">
                      <img src={img.url} alt={img.name} className="w-full h-full object-cover" />
                      <button
                        type="button"
                        onClick={() => removeImage(i)}
                        className="absolute top-1 right-1 w-5 h-5 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                      >
                        <X className="w-3 h-3 text-white" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ── Submit Error ── */}
            {errors.submit && (
              <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs font-semibold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                <span>{errors.submit}</span>
              </div>
            )}

            {/* ── Submit Button ── */}
            <button
              id="submit-report-btn"
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 bg-linear-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 disabled:opacity-60 text-white font-bold text-base py-4 rounded-2xl shadow-lg shadow-orange-200 transition-all duration-200 cursor-pointer"
            >
              {submitting ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Submitting Report…</>
              ) : (
                <><AlertTriangle className="w-5 h-5" /> Submit Incident Report</>
              )}
            </button>
            <p className="text-center text-xs text-slate-400 pb-6">
              False reports are punishable under applicable law. Report only genuine emergencies.
            </p>
          </form>
        )}
      </div>
    </div>
  );
};
