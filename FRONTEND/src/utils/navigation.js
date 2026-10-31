/**
 * DISHA Platform - Device-Adaptive Turn-by-Turn Navigation Utility
 * Provides cross-platform navigation URLs supporting:
 * - Google Maps (Desktop, Android, and universal browser)
 * - Apple Maps (iOS / macOS native fallback)
 * - Geo URI / browser fallbacks
 */

export function getDirectionsUrl(latitude, longitude, destinationName = '') {
  if (latitude == null || longitude == null) return null;

  const lat = typeof latitude === 'number' ? latitude : parseFloat(latitude);
  const lng = typeof longitude === 'number' ? longitude : parseFloat(longitude);

  if (isNaN(lat) || isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return null;
  }

  const isIOS =
    typeof navigator !== 'undefined' &&
    (/iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1));

  const label = encodeURIComponent(destinationName.trim() || 'Incident Destination');

  if (isIOS) {
    // Apple Maps URL scheme on iOS devices
    return `https://maps.apple.com/?daddr=${lat},${lng}&q=${label}`;
  }

  // Universal Google Maps directions URL
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
}

export function openDirections(latitude, longitude, destinationName = '') {
  const url = getDirectionsUrl(latitude, longitude, destinationName);
  if (url && typeof window !== 'undefined') {
    window.open(url, '_blank', 'noopener,noreferrer');
    return true;
  }
  return false;
}
