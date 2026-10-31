import React, { useState, useEffect } from 'react';
import { Smartphone, Download, Loader2, CheckCircle2 } from 'lucide-react';
import { isNativePlatform } from '../../services/nativeService';

// Direct, guaranteed same-origin APK path hosted with the application
const LOCAL_APK_URL = '/disha.apk';

/**
 * Triggers an immediate direct file download of the APK file in the browser.
 * Uses same-origin anchor download so the browser directly saves the .apk file
 * without opening any new tab, popup, or external link.
 */
function downloadApkFile(url = LOCAL_APK_URL, fileName = 'disha.apk') {
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', fileName);
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    try {
      document.body.removeChild(link);
    } catch (e) {}
  }, 400);
}

export const DownloadApkButton = ({ variant = 'hero', className = '' }) => {
  // If running inside the native Android app, hide the download button
  if (isNativePlatform()) return null;

  const [downloading, setDownloading] = useState(false);
  const [versionName, setVersionName] = useState('1.0.0');
  const [statusMsg, setStatusMsg] = useState(null);

  useEffect(() => {
    let isMounted = true;

    // Load version info from local manifest if available
    fetch('/version-manifest.json', { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (isMounted && data?.versionName) {
          setVersionName(data.versionName);
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  const handleDownload = (e) => {
    e.preventDefault();
    if (downloading) return;

    setDownloading(true);
    setStatusMsg('Downloading DISHA APK…');

    // Trigger instant native direct download of .apk file
    downloadApkFile(LOCAL_APK_URL, `disha-v${versionName}.apk`);

    setTimeout(() => {
      setStatusMsg('Download started! Check your downloads folder.');
      setDownloading(false);
    }, 1200);

    setTimeout(() => {
      setStatusMsg(null);
    }, 6000);
  };

  // ─── Header Navbar Variant (Compact & Reduced Text for Responsiveness) ─────
  if (variant === 'navbar') {
    return (
      <button
        id="navbar-download-apk-btn"
        onClick={handleDownload}
        title={`Download DISHA Android APK (v${versionName})`}
        className={`group relative flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-semibold bg-white/10 hover:bg-orange-500/20 text-slate-200 hover:text-white border border-white/15 hover:border-orange-500/40 transition-all cursor-pointer whitespace-nowrap shadow-xs shrink-0 active:scale-95 ${className}`}
      >
        <Smartphone className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-orange-400 group-hover:scale-110 transition-transform shrink-0" />
        <span className="font-semibold tracking-wide">{downloading ? 'Downloading…' : 'APK'}</span>
        {downloading && (
          <Loader2 className="w-2.5 h-2.5 sm:w-3 sm:h-3 animate-spin text-orange-400 shrink-0" />
        )}
      </button>
    );
  }

  // ─── Mobile Drawer Variant (Full-width for Mobile Dropdown Menu) ───────────
  if (variant === 'drawer') {
    return (
      <button
        id="drawer-download-apk-btn"
        onClick={handleDownload}
        disabled={downloading}
        className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 active:bg-white/15 text-slate-200 hover:text-white border border-white/10 transition-all cursor-pointer text-xs sm:text-sm font-medium ${className}`}
      >
        <div className="flex items-center gap-2.5">
          <Smartphone className="w-4 h-4 text-orange-400 shrink-0" />
          <span>{downloading ? 'Starting APK download…' : 'Download Android App (APK)'}</span>
        </div>
        {downloading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-orange-400 shrink-0" />
        ) : (
          <span className="text-[10px] bg-orange-500/20 text-orange-300 px-2 py-0.5 rounded-full font-mono border border-orange-500/30 shrink-0">
            v{versionName}
          </span>
        )}
      </button>
    );
  }

  // ─── Hero Section Variant (App Brand Theme: Orange/Amber Gradient, Medium Text) ─
  return (
    <div className={`relative inline-flex flex-col items-center ${className}`}>
      <button
        id="hero-download-apk-btn"
        onClick={handleDownload}
        disabled={downloading}
        className="group relative flex items-center gap-2.5 bg-linear-to-r from-[#f26522] to-[#ea580c] hover:from-[#ea580c] hover:to-[#c2410c] text-white font-semibold text-xs sm:text-sm py-2.5 sm:py-3 px-6 sm:px-7 rounded-full border border-orange-400/40 hover:border-orange-300 shadow-lg shadow-orange-950/25 hover:shadow-orange-500/30 hover:-translate-y-0.5 active:scale-95 transition-all duration-200 cursor-pointer"
      >
        {downloading ? (
          <Loader2 className="w-4 h-4 text-white animate-spin shrink-0" />
        ) : (
          <Smartphone className="w-4 h-4 text-white group-hover:scale-110 transition-transform shrink-0" />
        )}
        <span className="flex items-center gap-2">
          <span>{downloading ? 'Downloading APK…' : 'Download APK'}</span>
          <span className="text-[10px] bg-white/20 text-white border border-white/30 px-2 py-0.5 rounded-full font-mono font-medium">
            v{versionName}
          </span>
        </span>
        <Download className="w-3.5 h-3.5 text-orange-100 group-hover:text-white group-hover:translate-y-0.5 transition-all shrink-0" />
      </button>

      {statusMsg && (
        <span className="absolute -bottom-6 text-[10.5px] font-medium whitespace-nowrap flex items-center gap-1 text-emerald-400 animate-fade-in">
          <CheckCircle2 className="w-3 h-3 text-emerald-400 inline" />
          {statusMsg}
        </span>
      )}
    </div>
  );
};
