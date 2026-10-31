import React, { useState, useEffect } from 'react';
import { Smartphone, Download, Loader2, ExternalLink } from 'lucide-react';
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
        // Try version-manifest.json first, then GitHub Releases API
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

  // ─── Navbar Variant ────────────────────────────────────────────────────────
  if (variant === 'navbar') {
    return (
      <button
        id="navbar-download-apk-btn"
        onClick={handleDownload}
        title={releaseInfo ? `Download DISHA Android APK (v${releaseInfo.versionName})` : 'DISHA Android Release'}
        className={`group relative flex items-center gap-1.5 px-3 py-1.5 lg:py-2 rounded-full text-xs font-semibold bg-white/10 hover:bg-white/15 text-slate-100 hover:text-white border border-white/20 transition-all cursor-pointer whitespace-nowrap shadow-xs hover:border-orange-500/40 ${className}`}
      >
        <Smartphone className="w-3.5 h-3.5 text-orange-400 group-hover:scale-110 transition-transform" />
        <span>Android App</span>
        {loading ? (
          <Loader2 className="w-3 h-3 animate-spin text-orange-400" />
        ) : releaseInfo?.versionName ? (
          <span className="text-[10px] bg-orange-500/20 text-orange-300 px-1.5 py-0.2 rounded-full font-mono border border-orange-500/30">
            v{releaseInfo.versionName}
          </span>
        ) : (
          <span className="text-[9px] bg-slate-700/60 text-slate-300 px-1.5 py-0.2 rounded-full font-mono">
            APK
          </span>
        )}
      </button>
    );
  }

  // ─── Hero Section Variant ──────────────────────────────────────────────────
  return (
    <div className={`relative inline-flex flex-col items-center ${className}`}>
      <button
        id="hero-download-apk-btn"
        onClick={handleDownload}
        disabled={downloading}
        className="group relative flex items-center gap-2.5 bg-linear-to-r from-slate-900 to-slate-950 hover:from-slate-800 hover:to-slate-900 text-white font-semibold text-xs sm:text-sm py-2.5 sm:py-3 px-5 sm:px-6 rounded-full border border-orange-500/40 hover:border-orange-500 shadow-md shadow-orange-950/30 hover:shadow-orange-500/20 active:scale-95 transition-all duration-200 cursor-pointer backdrop-blur-md"
      >
        {downloading ? (
          <Loader2 className="w-4 h-4 text-orange-400 animate-spin" />
        ) : (
          <Smartphone className="w-4 h-4 text-orange-400 group-hover:scale-110 transition-transform" />
        )}
        <span className="flex items-center gap-1.5">
          <span>{downloading ? 'Downloading APK…' : 'Download Android App'}</span>
          {releaseInfo?.versionName ? (
            <span className="text-[10px] bg-orange-500/20 text-orange-300 border border-orange-500/40 px-2 py-0.5 rounded-full font-mono">
              v{releaseInfo.versionName}
            </span>
          ) : (
            <span className="text-[10px] bg-white/10 text-slate-300 border border-white/20 px-2 py-0.5 rounded-full font-mono">
              APK
            </span>
          )}
        </span>
        <Download className="w-3.5 h-3.5 text-slate-400 group-hover:text-white transition-colors" />
      </button>

      {statusMsg && (
        <span className="absolute -bottom-5 text-[10px] text-orange-400 animate-fade-in font-medium">
          {statusMsg}
        </span>
      )}
    </div>
  );
};
