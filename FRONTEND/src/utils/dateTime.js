/**
 * DISHA Platform - Centralized Date & Time Utility
 * Standardizes all timestamps across DISHA to Indian Standard Time (Asia/Kolkata, UTC+05:30).
 * 
 * Rules:
 * - Accepts ISO 8601 UTC strings, timestamps, or date/time strings.
 * - Converts UTC -> IST (Asia/Kolkata).
 * - If exact time exists: "21 Aug 2026, 4:00 PM IST" or "21 Aug 2026 • 4:00 PM IST"
 * - If only date exists (or time is missing / '00:00' / 'Live'): "21 Aug 2026"
 * - NEVER displays "00:00 UTC" or "00:00 IST" unless the event explicitly occurred at midnight.
 */

const MONTHS_SHORT = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

/**
 * Checks if a string or date contains a meaningful time component (not midnight 00:00:00).
 */
function hasExplicitTime(rawDate, rawTime) {
  if (rawTime && typeof rawTime === 'string') {
    const t = rawTime.trim().toLowerCase();
    if (t === 'live' || t === 'verified' || t === 'feed' || t === '' || t === 'null' || t === 'undefined') {
      return false;
    }
    // Check if time is explicitly 00:00 or 00:00:00
    if (/^00:00(:00)?(\s*(utc|ist|gmt|z))?$/i.test(t)) {
      return false;
    }
    if (/\d{1,2}:\d{2}/.test(t)) {
      return true;
    }
  }

  if (typeof rawDate === 'string') {
    // If ISO format with T and non-midnight time: e.g. 2026-08-21T10:30:00Z
    if (rawDate.includes('T')) {
      const timePart = rawDate.split('T')[1];
      if (timePart && !/^00:00:00(\.0+)?(Z|\+00:00)?$/i.test(timePart.trim())) {
        return true;
      }
    }
  }

  if (rawDate instanceof Date && !isNaN(rawDate.getTime())) {
    return rawDate.getUTCHours() !== 0 || rawDate.getUTCMinutes() !== 0 || rawDate.getUTCSeconds() !== 0;
  }

  return false;
}

/**
 * Formats any raw date/timestamp input to IST display format.
 * 
 * @param {string|number|Date|Object} input - ISO string, timestamp number, Date object, or { date, time, datetime, timestamp }
 * @param {Object} options - { separator: '•' | ',', includeTime: boolean }
 * @returns {string} - Formatted IST date string (e.g. "21 Aug 2026 • 4:00 PM IST" or "21 Aug 2026")
 */
export function formatDateTimeIST(input, options = {}) {
  if (!input) return 'Recent';

  const separator = options.separator || '•';

  // If input is an object with existing fields (e.g. event or news item)
  let dateVal = input;
  let explicitTimeStr = null;

  if (typeof input === 'object' && !(input instanceof Date)) {
    dateVal = input.datetime || input.timestamp || input.processed_at || input.published_at || input.origin_time || input.event_time || input.date;
    explicitTimeStr = input.time || null;
  }

  if (!dateVal) return 'Recent';

  let dateObj = null;

  // Try parsing timestamp / ISO
  if (typeof dateVal === 'number') {
    // Epoch in seconds vs ms
    dateObj = new Date(dateVal > 1e11 ? dateVal : dateVal * 1000);
  } else if (typeof dateVal === 'string') {
    const trimmed = dateVal.trim();
    // If format is YYYY-MM-DD only
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      const [y, m, d] = trimmed.split('-').map(Number);
      return `${d} ${MONTHS_SHORT[m - 1]} ${y}`;
    }
    dateObj = new Date(trimmed);
  } else if (dateVal instanceof Date) {
    dateObj = dateVal;
  }

  if (!dateObj || isNaN(dateObj.getTime())) {
    // Fallback if string cannot be parsed as Date
    if (typeof dateVal === 'string') return dateVal;
    return 'Recent';
  }

  // Format date parts in Asia/Kolkata
  try {
    const isTimePresent = options.includeTime !== undefined
      ? options.includeTime
      : hasExplicitTime(dateVal, explicitTimeStr);

    const dtfDate = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });

    const formattedDate = dtfDate.format(dateObj); // e.g. "21 Aug 2026"

    if (!isTimePresent) {
      return formattedDate;
    }

    const dtfTime = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });

    const formattedTime = dtfTime.format(dateObj); // e.g. "4:00 pm"
    const uppercaseTime = formattedTime.toUpperCase();

    return `${formattedDate} ${separator} ${uppercaseTime} IST`;
  } catch (e) {
    return dateObj.toLocaleDateString('en-IN');
  }
}

/**
 * Formats date only in IST (e.g. "21 Aug 2026").
 */
export function formatDateIST(input) {
  return formatDateTimeIST(input, { includeTime: false });
}

/**
 * Formats time only in IST (e.g. "4:00 PM IST").
 */
export function formatTimeIST(input) {
  if (!input) return '';
  let dateObj = null;
  if (typeof input === 'number') {
    dateObj = new Date(input > 1e11 ? input : input * 1000);
  } else if (typeof input === 'string') {
    dateObj = new Date(input);
  } else if (input instanceof Date) {
    dateObj = input;
  }

  if (!dateObj || isNaN(dateObj.getTime())) return '';

  try {
    const dtfTime = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    return `${dtfTime.format(dateObj).toUpperCase()} IST`;
  } catch (e) {
    return '';
  }
}
