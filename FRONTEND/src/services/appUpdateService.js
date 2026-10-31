import { Capacitor } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { openExternalUrl } from './nativeService';

/**
 * Current DISHA Application Version
 */
export const APP_VERSION = {
  versionCode: 1,
  versionName: '1.0.0',
  buildDate: '2026-10-31',
};

const GITHUB_OWNER = 'Chitransh-22';
const GITHUB_REPO = 'DISHA-platform';
const DISMISSED_UPDATE_KEY = 'disha_dismissed_update_version';

/**
 * Computes SHA-256 hex digest of an ArrayBuffer using Web Crypto API.
 */
export const computeSha256 = async (arrayBuffer) => {
  if (!window.crypto?.subtle) {
    console.warn('[DISHA Update] Web Crypto subtle unavailable');
    return null;
  }
  const hashBuffer = await window.crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
};

/**
 * Checks GitHub Releases and version-manifest.json for newer published releases.
 * @param {boolean} isManual - true if initiated by user click
 * @returns {Promise<{ hasUpdate: boolean, updateInfo: Object|null, error: string|null }>}
 */
export const checkForAppUpdate = async (isManual = false) => {
  try {
    let manifestData = null;

    // 1. Primary: Fetch published version-manifest.json from GitHub Releases asset or raw repository
    const manifestUrls = [
      `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/version-manifest.json`,
      `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`,
    ];

    for (const url of manifestUrls) {
      try {
        const res = await fetch(url, {
          headers: { 'Accept': 'application/json' },
          cache: 'no-cache',
        });
        if (res.ok) {
          const json = await res.json();
          if (json.versionCode || json.tag_name) {
            manifestData = json;
            break;
          }
        }
      } catch (fetchErr) {
        // try next fallback
      }
    }

    if (!manifestData) {
      return {
        hasUpdate: false,
        updateInfo: null,
        error: isManual ? 'No published releases found yet on GitHub.' : null,
      };
    }

    // 2. Normalize metadata whether fetched from manifest or GitHub release API
    let remoteVersionCode = 1;
    let remoteVersionName = '1.0.0';
    let apkDownloadUrl = null;
    let sha256 = null;
    let releaseNotes = '';
    let isMandatory = false;
    let publishedAt = '';

    if (manifestData.versionCode) {
      // Direct version-manifest.json format
      remoteVersionCode = parseInt(manifestData.versionCode, 10);
      remoteVersionName = manifestData.versionName || `v${manifestData.versionCode}`;
      apkDownloadUrl = manifestData.apkUrl;
      sha256 = manifestData.sha256 || null;
      releaseNotes = manifestData.releaseNotes || manifestData.notes || 'Performance enhancements and stability updates.';
      isMandatory = !!manifestData.isMandatory;
      publishedAt = manifestData.publishedAt || manifestData.releaseDate || '';
    } else if (manifestData.tag_name) {
      // GitHub Releases API response format
      const tag = manifestData.tag_name.replace(/^v/, '');
      remoteVersionName = tag;
      remoteVersionCode = manifestData.id || 1;
      releaseNotes = manifestData.body || 'New official DISHA release.';
      publishedAt = manifestData.published_at || '';

      // Find APK asset
      const apkAsset = (manifestData.assets || []).find(
        (a) => a.name && a.name.endsWith('.apk')
      );
      if (apkAsset) {
        apkDownloadUrl = apkAsset.browser_download_url;
      }
    }

    // If no valid APK download URL found, cannot update
    if (!apkDownloadUrl) {
      return {
        hasUpdate: false,
        updateInfo: null,
        error: isManual ? 'Latest release does not have a downloadable APK asset.' : null,
      };
    }

    // 3. Compare with installed application version
    const hasUpdate = remoteVersionCode > APP_VERSION.versionCode;

    // Check if dismissed before (only for automatic checks; manual always shows)
    if (!isManual && hasUpdate) {
      try {
        const dismissed = localStorage.getItem(DISMISSED_UPDATE_KEY);
        if (dismissed && parseInt(dismissed, 10) === remoteVersionCode && !isMandatory) {
          return { hasUpdate: false, updateInfo: null, error: null };
        }
      } catch (e) {}
    }

    return {
      hasUpdate,
      updateInfo: hasUpdate
        ? {
            versionCode: remoteVersionCode,
            versionName: remoteVersionName,
            currentVersionName: APP_VERSION.versionName,
            currentVersionCode: APP_VERSION.versionCode,
            apkUrl: apkDownloadUrl,
            sha256,
            releaseNotes,
            isMandatory,
            publishedAt,
          }
        : null,
      error: null,
    };
  } catch (err) {
    console.warn('[DISHA Update] Update check error:', err);
    return {
      hasUpdate: false,
      updateInfo: null,
      error: isManual ? 'Unable to check for updates. Please verify your internet connection.' : null,
    };
  }
};

/**
 * Saves a version code as dismissed so the user is not repeatedly prompted.
 */
export const dismissUpdate = (versionCode) => {
  try {
    localStorage.setItem(DISMISSED_UPDATE_KEY, String(versionCode));
  } catch (e) {}
};

/**
 * Downloads and triggers installation of an APK update.
 * Reports progress (0 to 100) via onProgress callback.
 */
export const downloadAndInstallApk = async (updateInfo, onProgress = () => {}) => {
  const { apkUrl, sha256, versionName } = updateInfo;

  if (!apkUrl) {
    throw new Error('Invalid APK download URL.');
  }

  onProgress(5, 'Initiating secure download...');

  // If running on web, directly trigger browser download
  if (!Capacitor.isNativePlatform()) {
    window.location.href = apkUrl;
    onProgress(100, 'Download started in browser.');
    return;
  }

  try {
    // 1. Download APK with fetch
    onProgress(15, 'Connecting to release server...');
    const response = await fetch(apkUrl);
    if (!response.ok) {
      throw new Error(`Failed to download APK: ${response.status} ${response.statusText}`);
    }

    const contentLength = response.headers.get('content-length');
    const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;

    let receivedBytes = 0;
    const reader = response.body.getReader();
    const chunks = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      receivedBytes += value.length;

      if (totalBytes > 0) {
        const percent = Math.min(85, Math.round(15 + (receivedBytes / totalBytes) * 70));
        onProgress(percent, `Downloading ${Math.round(receivedBytes / 1024 / 1024)}MB of ${Math.round(totalBytes / 1024 / 1024)}MB...`);
      } else {
        onProgress(50, `Downloading (${Math.round(receivedBytes / 1024 / 1024)}MB)...`);
      }
    }

    // 2. Concatenate chunks into single Uint8Array
    onProgress(88, 'Validating package integrity...');
    const fullBuffer = new Uint8Array(receivedBytes);
    let offset = 0;
    for (const chunk of chunks) {
      fullBuffer.set(chunk, offset);
      offset += chunk.length;
    }

    // 3. Verify SHA-256 checksum if provided
    if (sha256) {
      onProgress(92, 'Verifying SHA-256 checksum...');
      const actualHash = await computeSha256(fullBuffer.buffer);
      if (actualHash && actualHash.toLowerCase() !== sha256.toLowerCase()) {
        throw new Error('Checksum validation failed. Downloaded APK may be corrupt or tampered.');
      }
    }

    // 4. Save APK file to Cache directory
    onProgress(95, 'Preparing installer...');
    const fileName = `disha-update-${versionName || 'latest'}.apk`;

    // Convert to Base64 for Capacitor Filesystem write
    let binary = '';
    const bytes = new Uint8Array(fullBuffer);
    const len = bytes.byteLength;
    const chunkSize = 8192;
    for (let i = 0; i < len; i += chunkSize) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
    }
    const base64Data = btoa(binary);

    await Filesystem.writeFile({
      path: fileName,
      data: base64Data,
      directory: Directory.Cache,
    });

    const fileUri = await Filesystem.getUri({
      path: fileName,
      directory: Directory.Cache,
    });

    onProgress(100, 'Opening Android Package Installer...');

    // 5. Open Android package installer via system intent or browser
    if (fileUri?.uri) {
      await openExternalUrl(fileUri.uri);
    } else {
      // Fallback: open direct release link
      await openExternalUrl(apkUrl);
    }
  } catch (err) {
    console.warn('[DISHA Update] Download/install error:', err);
    // Fallback: open release page in browser
    await openExternalUrl(apkUrl);
    throw err;
  }
};
