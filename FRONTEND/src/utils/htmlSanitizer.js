/**
 * DISHA Platform - Centralized HTML Sanitizer Utility
 * Sanitizes and strips raw/escaped HTML tags, unescapes entities, and preserves readable text.
 * 
 * Prevents XSS and ensures clean typography for news previews, descriptions, and briefings.
 */

const HTML_ENTITIES = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#39;': "'",
  '&apos;': "'",
  '&nbsp;': ' ',
  '&#160;': ' ',
  '&bull;': '•',
  '&mdash;': '—',
  '&ndash;': '–',
};

/**
 * Unescapes standard and numeric HTML entities.
 */
export function unescapeHtml(text) {
  if (!text || typeof text !== 'string') return '';
  
  let str = text;
  // Replace named entities
  for (const [entity, replacement] of Object.entries(HTML_ENTITIES)) {
    str = str.replaceAll(entity, replacement);
  }
  // Replace numeric entities e.g. &#8217;
  str = str.replace(/&#(\d+);/g, (match, dec) => String.fromCharCode(dec));
  str = str.replace(/&#x([0-9a-fA-F]+);/g, (match, hex) => String.fromCharCode(parseInt(hex, 16)));
  
  return str;
}

/**
 * Converts raw/escaped HTML text into safe, readable plain text.
 * E.g. `<a href="https://example.com">Read more</a>` -> `Read more`
 * 
 * @param {string} rawText - Raw input string containing possible HTML
 * @returns {string} - Cleaned, safe plain text
 */
export function sanitizeNewsDescription(rawText) {
  if (!rawText || typeof rawText !== 'string') return '';

  // 1. Unescape HTML entities first so escaped tags like &lt;p&gt; are exposed
  let cleaned = unescapeHtml(rawText);

  // 2. Remove script / style tags and their inner content
  cleaned = cleaned.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ');
  cleaned = cleaned.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ');

  // 3. Convert anchor tags to inner text: <a ...>text</a> -> text
  cleaned = cleaned.replace(/<a\b[^>]*>(.*?)<\/a>/gi, '$1');

  // 4. Strip all remaining HTML tags
  cleaned = cleaned.replace(/<[^>]+>/g, ' ');

  // 5. Unescape again in case double-escaped entities existed
  cleaned = unescapeHtml(cleaned);

  // 6. Collapse consecutive whitespace and trim
  cleaned = cleaned.replace(/\s+/g, ' ').trim();

  return cleaned;
}

/**
 * Alias for sanitizeNewsDescription
 */
export const cleanHtmlText = sanitizeNewsDescription;
