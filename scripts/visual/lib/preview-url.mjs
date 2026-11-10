import { PREVIEW_HOST_RE } from './visual-rules.mjs';

/**
 * Optional Workers preview mode. CI never calls this. The host must match
 * the allowlist, and the page must prove it was built from --sha. The nav
 * guard still runs afterwards, so a preview that calls /api/agent or any
 * other origin fails the run.
 */
export async function assertPreviewTarget(rawUrl, sha) {
  let url;
  try {
    url = new URL(rawUrl);
  } catch {
    const error = new Error(`invalid --url ${rawUrl}`);
    error.exitCode = 2;
    throw error;
  }
  if (url.protocol !== 'https:' || !PREVIEW_HOST_RE.test(url.hostname)) {
    const error = new Error(
      `preview host is not allowlisted (${url.hostname}). CI serves the PR build locally instead.`
    );
    error.exitCode = 2;
    throw error;
  }
  if (!/^[\da-f]{40}$/.test(sha || '')) {
    const error = new Error('--sha must be the 40-character commit that built the preview');
    error.exitCode = 2;
    throw error;
  }
  const buildUrl = new URL('/build.json', url);
  const response = await fetch(buildUrl, { redirect: 'error' });
  if (!response.ok) {
    const error = new Error(`preview build sha was not proven (${buildUrl} → ${response.status})`);
    error.exitCode = 2;
    throw error;
  }
  const body = await response.json();
  const built = typeof body.sha === 'string' ? body.sha : '';
  if (built !== sha) {
    const error = new Error(`preview /build.json sha ${built || 'missing'} !== ${sha}`);
    error.exitCode = 2;
    throw error;
  }
  return url;
}
