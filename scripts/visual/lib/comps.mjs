import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';

export function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

const SIGNOFF_PREFIX = '/merimeesoftware/cfb-ranking-algorithm/';

export function signoffOk(value) {
  if (typeof value !== 'string' || !value.startsWith('https://')) return false;
  let url;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  return url.hostname === 'github.com' && url.pathname.startsWith(SIGNOFF_PREFIX);
}

/**
 * A comp counts as signed only with a manifest entry, a matching sha256,
 * a signed_by, and a GitHub sign-off URL on this repo. Anything else is
 * "no comps" — never a pass.
 */
export function evaluateComp(entry, manifestDir) {
  if (!entry) return { signed: false, reason: 'no signed comp' };
  if (typeof entry.file !== 'string' || entry.file.length === 0) {
    return { signed: false, reason: 'comp file missing' };
  }
  if (path.isAbsolute(entry.file) || entry.file.split(/[\\/]/).includes('..')) {
    return { signed: false, reason: 'comp path rejected' };
  }
  const abs = path.resolve(manifestDir, entry.file);
  const root = path.resolve(manifestDir);
  if (abs !== root && !abs.startsWith(root + path.sep)) {
    return { signed: false, reason: 'comp path rejected' };
  }
  if (!existsSync(abs)) return { signed: false, reason: 'comp file missing' };
  const bytes = readFileSync(abs);
  const digest = sha256(bytes);
  if (typeof entry.sha256 !== 'string' || digest !== entry.sha256.toLowerCase()) {
    return { signed: false, reason: 'sha256 mismatch', file: abs };
  }
  if (typeof entry.signed_by !== 'string' || entry.signed_by.trim() === '') {
    return { signed: false, reason: 'missing signed_by', file: abs };
  }
  if (!signoffOk(entry.signoff)) {
    return { signed: false, reason: 'missing sign-off', file: abs };
  }
  return { signed: true, reason: 'signed', file: abs, bytes };
}

export function findCompEntry(manifest, route, widthName) {
  const comps = Array.isArray(manifest.comps) ? manifest.comps : [];
  return (
    comps.find(
      (entry) => entry.route === route && String(entry.width) === String(widthName)
    ) || null
  );
}
