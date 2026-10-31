import React, { useState, useEffect } from 'react';
import { Smartphone, Download, Loader2 } from 'lucide-react';
import { isNativePlatform, openExternalUrl } from '../../services/nativeService';

const GITHUB_OWNER = 'Chitransh-22';
const GITHUB_REPO = 'DISHA-platform';
const RELEASES_PAGE_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases`;

export const DownloadApkButton = ({ variant = 'hero', className = '' }) => {
  // If running inside the native Android app, hide the download button
  if (isNativePlatform()) return null;

  const [loading, setLoading] = useState(true);
  const [releaseInfo, setReleaseInfo] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchLatestRelease = async () => {
      try {
        const manifestUrls = [
          `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/version-manifest.json`,
          `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`,
        ];

        let found = null;
        for (const url of manifestUrls) {
          try {
            const res = await fetch(url, { cache: 'no-cache' });
            if (res.ok) {
              const data = await res.json();
              if (data.apkUrl) {
                found = {
                  versionName: data.versionName || '1.0.0',
                  apkUrl: data.apkUrl,
                };
                break;
              } else if (data.tag_name) {
                const apk = (data.assets || []).find((a) => a.name && a.name.endsWith('.apk'));
                if (apk) {
                  found = {
                    versionName: data.tag_name.replace(/^v/, ''),
                    apkUrl: apk.browser_download_url,
                  };
                  break;
                }
              }
            }
          } catch (e) {}
        }

        if (isMounted) {
          setReleaseInfo(found);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) setLoading(false);
      }
    };

    fetchLatestRelease();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleDownload = (e) => {
    e.preventDefault();
    if (releaseInfo?.apkUrl) {
      setDownloading(true);
      setStatusMsg('Starting download…');
      window.location.href = releaseInfo.apkUrl;
      setTimeout(() => {
        setDownloading(false);
        setStatusMsg(null);
      }, 4000);
    } else {
      // If release APK not yet published, open official GitHub Releases page
      openExternalUrl(RELEASES_PAGE_URL);
    }
  };

  // ─── Header Navbar Variant (Compact & Reduced Text for Responsiveness) ─────
  if (variant === 'navbar') {
    return (
      <button
        id="navbar-download-apk-btn"
        onClick={handleDownload}
        title={releaseInfo ? `Download DISHA Android APK (v${releaseInfo.versionName})` : 'Download DISHA Android APK'}
        className={`group relative flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-semibold bg-white/10 hover:bg-orange-500/20 text-slate-200 hover:text-white border border-white/15 hover:border-orange-500/40 transition-all cursor-pointer whitespace-nowrap shadow-xs shrink-0 active:scale-95 ${className}`}
      >
        <Smartphone className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-orange-400 group-hover:scale-110 transition-transform shrink-0" />
        <span className="font-semibold tracking-wide">APK</span>
        {loading && (
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
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-orange-400 shrink-0" />
        ) : releaseInfo?.versionName ? (
          <span className="text-[10px] bg-orange-500/20 text-orange-300 px-2 py-0.5 rounded-full font-mono border border-orange-500/30 shrink-0">
            v{releaseInfo.versionName}
          </span>
        ) : (
          <span className="text-[10px] bg-white/10 text-slate-400 px-2 py-0.5 rounded-full font-mono shrink-0">
            APK
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
          {releaseInfo?.versionName && (
            <span className="text-[10px] bg-white/20 text-white border border-white/30 px-2 py-0.5 rounded-full font-mono font-medium">
              v{releaseInfo.versionName}
            </span>
          )}
        </span>
        <Download className="w-3.5 h-3.5 text-orange-100 group-hover:text-white group-hover:translate-y-0.5 transition-all shrink-0" />
      </button>

      {statusMsg && (
        <span className="absolute -bottom-5 text-[10px] text-orange-400 animate-fade-in font-medium">
          {statusMsg}
        </span>
      )}
    </div>
  );
};
