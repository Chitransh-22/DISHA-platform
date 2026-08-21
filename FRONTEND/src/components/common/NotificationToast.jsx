import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const NotificationToast = ({ notification, onClose }) => {
  useEffect(() => {
    if (!notification) return;
    const timer = setTimeout(() => {
      onClose();
    }, 4500);

    return () => clearTimeout(timer);
  }, [notification, onClose]);

  if (!notification) return null;

  const isSuccess = notification.type === 'success';
  const isError = notification.type === 'error';

  return (
    <AnimatePresence>
      <div className="fixed top-20 right-4 sm:right-6 z-[9999] max-w-sm w-full pointer-events-none">
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className={`
            pointer-events-auto
            flex items-center gap-3 p-4 rounded-2xl
            bg-[#101318]/95 backdrop-blur-xl
            border shadow-2xl
            ${
              isSuccess
                ? 'border-emerald-500/40 shadow-emerald-950/40 text-emerald-100'
                : isError
                ? 'border-red-500/40 shadow-red-950/40 text-red-100'
                : 'border-orange-500/40 shadow-orange-950/40 text-orange-100'
            }
          `}
        >
          {/* Icon */}
          <div
            className={`
              w-9 h-9 rounded-xl flex items-center justify-center shrink-0
              ${
                isSuccess
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : isError
                  ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                  : 'bg-orange-500/15 text-orange-400 border border-orange-500/30'
              }
            `}
          >
            {isSuccess ? (
              <CheckCircle2 className="w-5 h-5" />
            ) : isError ? (
              <AlertCircle className="w-5 h-5" />
            ) : (
              <Info className="w-5 h-5" />
            )}
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0 pr-1">
            <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              {isSuccess ? 'Authentication' : isError ? 'Error' : 'Notification'}
            </p>
            <p className="text-sm font-bold text-white tracking-tight truncate">
              {notification.message || (isSuccess ? 'Sign in successful' : 'Action completed')}
            </p>
          </div>

          {/* Dismiss Button */}
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            aria-label="Dismiss notification"
          >
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
