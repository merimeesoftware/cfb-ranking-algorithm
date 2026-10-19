/**
 * Preview-stills rules. The pixel gate and the request guard live here so a
 * selector check cannot be swapped in without this file changing.
 */

export const WIDTHS = [
  { name: '390', width: 390, height: 844 },
  { name: '1440', width: 1440, height: 900 },
];

/**
 * Installed Google Chrome. The check refuses any other major.
 * CHROME_VERSION is the deb the workflow installs (…_VERSION-1_amd64.deb).
 */
export const CHROME_MAJOR = 154;
export const CHROME_VERSION = '154.0.8037.92';

/**
 * pixelmatch channel threshold (0–1). 0.1 lets antialiased edges through.
 * Capped so a manifest cannot set 1 and ignore every difference.
 */
export const PIXELMATCH_THRESHOLD = 0.1;
export const PIXELMATCH_THRESHOLD_CAP = 0.2;

/**
 * Fraction of viewport pixels that may differ. A recolored or shifted block
 * is far above this; a check that only looks for elements never consults it.
 */
export const MAX_DIFF_RATIO = 0.002;
export const MAX_DIFF_RATIO_CAP = 0.02;

/**
 * Optional Workers preview hosts. CI does not pass --url. Preview versions
 * of this Worker use prod AI_MODE, so the request guard still applies.
 */
export const PREVIEW_HOST_RE =
  /^(?:[a-z0-9-]+-true-rankings-cfb|[a-z0-9-]+\.true-rankings-cfb)\.merimeesoftware\.workers\.dev$/;

export function chromeMajorOf(version) {
  const match = String(version).match(/(\d+)\./);
  return match ? Number(match[1]) : NaN;
}

export function assertChromeMajor(version, expected = CHROME_MAJOR) {
  const major = chromeMajorOf(version);
  if (major !== expected) {
    const error = new Error(
      `Chrome major ${major || 'unknown'} does not match pinned major ${expected} (${version})`
    );
    error.exitCode = 2;
    throw error;
  }
  return major;
}

/**
 * @returns {'ok' | 'agent' | 'offsite'}
 */
export function classifyRequest(rawUrl, allowedOrigin) {
  let url;
  try {
    url = typeof rawUrl === 'string' ? new URL(rawUrl) : rawUrl;
  } catch {
    return 'offsite';
  }
  if (url.protocol === 'data:' || url.protocol === 'blob:' || url.protocol === 'about:') {
    return 'ok';
  }
  let path = url.pathname;
  try {
    path = decodeURIComponent(path);
  } catch {
    return 'offsite';
  }
  path = path.toLowerCase().replace(/\/+$/, '') || '/';
  if (path === '/api/agent' || path.startsWith('/api/agent/')) return 'agent';
  if (!allowedOrigin || url.origin !== allowedOrigin) return 'offsite';
  return 'ok';
}

export function resolveThresholds(manifest = {}) {
  const pixelmatchThreshold = numberOr(
    manifest.pixelmatchThreshold,
    PIXELMATCH_THRESHOLD
  );
  const maxDiffRatio = numberOr(manifest.maxDiffRatio, MAX_DIFF_RATIO);
  if (
    pixelmatchThreshold < 0 ||
    pixelmatchThreshold > PIXELMATCH_THRESHOLD_CAP ||
    maxDiffRatio < 0 ||
    maxDiffRatio > MAX_DIFF_RATIO_CAP
  ) {
    const error = new Error(
      `threshold out of range (pixelmatch 0–${PIXELMATCH_THRESHOLD_CAP}, maxDiffRatio 0–${MAX_DIFF_RATIO_CAP})`
    );
    error.exitCode = 2;
    throw error;
  }
  return { pixelmatchThreshold, maxDiffRatio };
}

function numberOr(value, fallback) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}
