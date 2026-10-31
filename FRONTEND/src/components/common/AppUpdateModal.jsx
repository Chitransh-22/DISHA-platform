import React, { useState } from 'react';
import { Download, RefreshCw, X, AlertTriangle, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { downloadAndInstallApk, dismissUpdate } from '../../services/appUpdateService';

export const AppUpdateModal = ({ updateInfo, onClose }) => {
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState('');
  const [errorMessage, setErrorMessage] = useState(null);

  if (!updateInfo) return null;

  const {
    versionName,
    currentVersionName,
    releaseNotes,
    isMandatory,
    versionCode,
    publishedAt,
  } = updateInfo;

  const handleUpdate = async () => {
    setDownloading(true);
    setErrorMessage(null);

    try {
      await downloadAndInstallApk(updateInfo, (pct, msg) => {
        setProgress(pct);
        setProgressText(msg);
      });
    } catch (err) {
      setErrorMessage(err.message || 'Download failed. Please try again.');
      setDownloading(false);
    }
  };

  const handleDismiss = () => {
    if (isMandatory) return;
    dismissUpdate(versionCode);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-9999 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-[#101318] text-white border border-orange-500/30 rounded-3xl p-6 sm:p-7 shadow-2xl shadow-orange-950/40 overflow-hidden">
        {/* Ambient Top Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-24 bg-orange-500/15 blur-2xl pointer-events-none" />

        {/* Close button (if not mandatory) */}
        {!isMandatory && !downloading && (
          <button
            onClick={handleDismiss}
            className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-full bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        {/* Header with Icon */}
        <div className="flex items-start gap-4 mb-5">
          <div className="w-12 h-12 rounded-2xl bg-linear-to-br from-orange-500 to-amber-600 flex items-center justify-center shrink-0 shadow-lg shadow-orange-500/25">
            <RefreshCw className={`w-6 h-6 text-white ${downloading ? 'animate-spin' : ''}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-orange-400">
                Official Release
              </span>
              {isMandatory && (
                <span className="text-[10px] bg-red-500/20 text-red-400 border border-red-500/40 px-2 py-0.5 rounded-full font-semibold">
                  Required
                </span>
              )}
            </div>
            <h3 className="text-lg font-bold text-slate-100 mt-0.5">
              DISHA Update Available
            </h3>
            <p className="text-xs text-slate-400">
              Installed: <span className="text-slate-300 font-mono">v{currentVersionName}</span> → Latest:{' '}
              <span className="text-orange-400 font-bold font-mono">v{versionName}</span>
            </p>
          </div>
        </div>

        {/* Release Notes */}
        <div className="mb-5 bg-white/5 border border-white/10 rounded-2xl p-4 text-xs text-slate-300 max-h-44 overflow-y-auto space-y-2">
          <p className="font-semibold text-slate-200 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Release Notes:</span>
          </p>
          <div className="text-slate-300 whitespace-pre-wrap leading-relaxed pl-1 text-[11px] sm:text-xs">
            {releaseNotes || 'Includes security, performance, and map stability updates.'}
          </div>
          {publishedAt && (
            <p className="text-[10px] text-slate-500 pt-1 border-t border-white/5">
              Published on: {new Date(publishedAt).toLocaleDateString()}
            </p>
          )}
        </div>

        {/* Progress Bar (during download) */}
        {downloading && (
          <div className="mb-5 space-y-2">
            <div className="flex justify-between text-xs text-slate-300 font-medium">
              <span>{progressText || 'Downloading...'}</span>
              <span className="text-orange-400 font-mono font-bold">{progress}%</span>
            </div>
            <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden p-0.5">
              <div
                className="h-full bg-linear-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-1">
              <span>🔒 Download verified via SHA-256 integrity hash.</span>
            </p>
          </div>
        )}

        {/* Error message if download failed */}
        {errorMessage && (
          <div className="mb-5 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2 text-xs text-red-300">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleUpdate}
            disabled={downloading}
            className="flex-1 flex items-center justify-center gap-2 bg-linear-to-r from-[#f26522] to-[#ea580c] hover:from-[#ea580c] hover:to-[#c2410c] disabled:opacity-60 text-white font-bold py-3 px-4 rounded-xl text-xs sm:text-sm shadow-md shadow-orange-950/40 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>{downloading ? 'Downloading...' : 'Update & Install'}</span>
          </button>

          {!isMandatory && !downloading && (
            <button
              onClick={handleDismiss}
              className="px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 text-xs sm:text-sm font-semibold transition-colors cursor-pointer border border-white/10"
            >
              Later
            </button>
          )}
        </div>

        {/* Android Permissions Advisory */}
        <p className="text-[10px] text-slate-400 text-center mt-3">
          If Android prompts for "Install unknown apps", grant permission to DISHA to complete update.
        </p>
      </div>
    </div>
  );
};
