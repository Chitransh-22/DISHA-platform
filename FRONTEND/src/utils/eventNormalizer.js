/**
 * DISHA Platform - Centralized Event Normalizer & Description Sanitizer
 * Disaster Intelligence and Situational Hazard Awareness Platform
 * 
 * Provides unified, security-hardened normalization for all event sources (NCS, SACHET, GNEWS, Citizen Reports):
 * 1. Sanitizes raw/escaped HTML tags (<a>, <p>, <br>, <strong>, <em>, etc.) into clean readable text.
 * 2. Extracts valid source hyperlinks from HTML anchor tags without displaying raw URLs/tags in the UI.
 * 3. Normalizes geospatial coordinates into clean notation (e.g. "28.70°N, 77.10°E").
 * 4. Normalizes source authority labels.
 * 5. Formats all timestamps to Indian Standard Time (IST: Asia/Kolkata).
 */

import { unescapeHtml } from './htmlSanitizer.js';
import { formatDateTimeIST } from './dateTime.js';
import { getCategoryConfig } from '../config/eventConfig.js';

/**
 * Clean and extract plain readable text and hyperlink URLs from raw/escaped HTML description.
 * 
 * @param {string} rawText - Raw text or HTML string (e.g. '<a href="https://news.google.com/..." target="_blank">3 Killed...</a>')
 * @param {string} [fallbackUrl] - Existing source or article URL if available
 * @returns {{ cleanDescription: string, extractedUrls: string[], primarySourceUrl: string|null }}
 */
export function cleanAndExtractDescription(rawText, fallbackUrl = null) {
  if (!rawText || typeof rawText !== 'string') {
    return {
      cleanDescription: '',
      extractedUrls: fallbackUrl ? [fallbackUrl] : [],
      primarySourceUrl: fallbackUrl || null,
    };
  }

  // 1. Unescape HTML entities first so escaped markup like &lt;a href="..."&gt; is decoded
  let str = unescapeHtml(rawText);

  const extractedUrls = [];

  // 2. Extract URLs and inner anchor text from <a ...href="...">...</a>
  const anchorRegex = /<a\b[^>]*\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))[^>]*>([\s\S]*?)<\/a>/gi;
  str = str.replace(anchorRegex, (match, url1, url2, url3, innerText) => {
    const rawUrl = (url1 || url2 || url3 || '').trim();
    if (rawUrl && /^https?:\/\//i.test(rawUrl)) {
      try {
        // Validate URL
        const parsed = new URL(rawUrl);
        if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
          extractedUrls.push(rawUrl);
        }
      } catch (e) {
        // Ignore invalid URL
      }
    }
    return innerText || '';
  });

  // 3. Remove script, style, iframe, object, embed tags completely
  str = str.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ');
  str = str.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ');
  str = str.replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, ' ');

  // 4. Convert block elements & line breaks to whitespace
  str = str.replace(/<br\s*\/?>/gi, ' ');
  str = str.replace(/<\/p>/gi, ' ');
  str = str.replace(/<\/div>/gi, ' ');
  str = str.replace(/<\/li>/gi, ' ');

  // 5. Strip all remaining HTML tags
  str = str.replace(/<[^>]+>/g, '');

  // 6. Final unescape pass for any nested entities
  str = unescapeHtml(str);

  // 7. Normalize whitespace & remove extraneous spaces before punctuation
  str = str
    .replace(/[ \t\r\f\n]+/g, ' ')
    .replace(/\s+([.,;:!?])/g, '$1')
    .trim();

  // If fallbackUrl provided and valid, add to list if not already present
  if (fallbackUrl && typeof fallbackUrl === 'string' && /^https?:\/\//i.test(fallbackUrl.trim())) {
    const trimmedFallback = fallbackUrl.trim();
    if (!extractedUrls.includes(trimmedFallback)) {
      extractedUrls.unshift(trimmedFallback);
    }
  }

  const primarySourceUrl = extractedUrls.length > 0 ? extractedUrls[0] : null;

  return {
    cleanDescription: str,
    extractedUrls,
    primarySourceUrl,
  };
}

/**
 * Normalizes latitude and longitude coordinates and provides a clean human-readable notation.
 * 
 * @param {number|string} rawLat 
 * @param {number|string} rawLon 
 * @returns {{ latitude: number|null, longitude: number|null, formatted: string, hasCoords: boolean }}
 */
export function normalizeCoordinates(rawLat, rawLon) {
  let lat = rawLat;
  let lon = rawLon;

  if (typeof lat === 'string') lat = parseFloat(lat);
  if (typeof lon === 'string') lon = parseFloat(lon);

  const isValidLat = typeof lat === 'number' && !isNaN(lat) && lat >= -90 && lat <= 90;
  const isValidLon = typeof lon === 'number' && !isNaN(lon) && lon >= -180 && lon <= 180;

  if (isValidLat && isValidLon) {
    const latDir = lat >= 0 ? 'N' : 'S';
    const lonDir = lon >= 0 ? 'E' : 'W';
    const absLat = Math.abs(lat).toFixed(2);
    const absLon = Math.abs(lon).toFixed(2);
    return {
      latitude: lat,
      longitude: lon,
      formatted: `${absLat}°${latDir}, ${absLon}°${lonDir}`,
      hasCoords: true,
    };
  }

  return {
    latitude: null,
    longitude: null,
    formatted: 'Regional Coordinates Pending',
    hasCoords: false,
  };
}

/**
 * Standardizes source labels for known disaster intelligence agencies.
 */
export function normalizeSourceLabel(rawSource, rawSourceLabel = null) {
  if (rawSourceLabel && typeof rawSourceLabel === 'string' && rawSourceLabel.trim()) {
    return rawSourceLabel.trim();
  }

  const src = (rawSource || '').toString().trim().toUpperCase();

  if (src === 'NCS_RISEQ' || src === 'NCS' || src === 'RISEQ') {
    return 'National Center for Seismology (NCS)';
  }
  if (src === 'NDMA_SACHET' || src === 'SACHET' || src === 'NDMA') {
    return 'NDMA Sachet Alert Network';
  }
  if (src === 'GNEWS' || src === 'NEWS') {
    return 'Verified Disaster Intelligence';
  }
  if (src === 'CITIZEN' || src === 'CITIZEN_REPORT') {
    return 'Citizen Ground Observation';
  }

  return rawSource || 'Verified Disaster Intelligence';
}

/**
 * Sanitizes title text (unescapes entities, removes tags).
 */
export function cleanTitle(rawTitle) {
  if (!rawTitle || typeof rawTitle !== 'string') return 'Incident Report';
  let str = unescapeHtml(rawTitle);
  str = str.replace(/<[^>]+>/g, ' ');
  str = unescapeHtml(str);
  return str.replace(/\s+/g, ' ').trim() || 'Incident Report';
}

/**
 * Normalizes any raw event object from backend routes (/api/events, /api/earthquakes, etc.)
 * into a consistent, sanitized, and structured event model.
 * 
 * @param {Object} event - Raw event object
 * @returns {Object} Normalized event object
 */
export function normalizeEvent(event) {
  if (!event || typeof event !== 'object') {
    return null;
  }

  const rawTitle = event.title || event.headline || event.name || 'Incident Alert';
  const title = cleanTitle(rawTitle);

  const rawDesc = event.description || event.summary || event.details || event.full_content || '';
  const rawUrl = event.source_url || event.url || event.link || event.article_url || event.web_url || null;

  const { cleanDescription, extractedUrls, primarySourceUrl } = cleanAndExtractDescription(rawDesc, rawUrl);

  const coords = normalizeCoordinates(
    event.latitude ?? event.lat,
    event.longitude ?? event.lon ?? event.lng
  );

  const category = event.category || event.disaster_type || event.type || 'Other';
  const categoryConfig = getCategoryConfig(category);

  let severity = (event.severity || 'Moderate').toString().trim();
  const validSeverities = ['Critical', 'Severe', 'Moderate', 'Low'];
  const matchedSev = validSeverities.find((s) => s.toLowerCase() === severity.toLowerCase());
  severity = matchedSev || 'Moderate';

  const sourceLabel = normalizeSourceLabel(event.source, event.source_label);

  const location = (event.location || event.state || event.region || event.district || 'India').toString().trim();

  const istFormattedTime = formatDateTimeIST(event);

  return {
    ...event,
    id: String(event.id || event._id || event.event_id || `ev_${Date.now()}`),
    title,
    description: cleanDescription,
    source_url: primarySourceUrl,
    extracted_urls: extractedUrls,
    source_label: sourceLabel,
    category: categoryConfig.label,
    raw_category: category,
    severity,
    latitude: coords.latitude,
    longitude: coords.longitude,
    coordinates_formatted: coords.formatted,
    has_coordinates: coords.hasCoords,
    location,
    state: event.state || null,
    district: event.district || null,
    formatted_time_ist: istFormattedTime,
    timestamp: event.timestamp || event.datetime || event.processed_at || event.origin_time || null,
  };
}
