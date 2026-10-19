import { createHash } from 'node:crypto';
import { existsSync, readFileSync, realpathSync } from 'node:fs';
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

function insideDir(child, parent) {
  const relative = path.relative(parent, child);
  return relative !== '' && !relative.startsWith('..') && !path.isAbsolute(relative);
}

/**
 * A comp file must realpath inside `<manifest>/renders`. A symlink or `..`
 * that lands anywhere else is a hard failure, not an unsigned comp.
 */
export function compPathVerdict(entry, manifestDir) {
  if (!entry || typeof entry.file !== 'string' || entry.file.length === 0) {
    return { ok: false, hardFail: false, reason: 'comp file missing' };
  }
  if (path.isAbsolute(entry.file)) {
    return { ok: false, hardFail: true, reason: 'comp path escapes renders' };
  }
  const lexicalRenders = path.resolve(manifestDir, 'renders');
  const lexical = path.resolve(manifestDir, entry.file);
  if (!insideDir(lexical, lexicalRenders)) {
    return { ok: false, hardFail: true, reason: 'comp path escapes renders' };
  }
  if (!existsSync(lexical)) {
    return { ok: false, hardFail: false, reason: 'comp file missing' };
  }
  let manifestReal;
  let fileReal;
  try {
    manifestReal = realpathSync(manifestDir);
    fileReal = realpathSync(lexical);
  } catch {
    return { ok: false, hardFail: true, reason: 'comp path escapes renders' };
  }
  const rendersReal = path.join(manifestReal, 'renders');
  if (!insideDir(fileReal, rendersReal)) {
    return { ok: false, hardFail: true, reason: 'comp path escapes renders' };
  }
  return { ok: true, hardFail: false, file: fileReal, bytes: readFileSync(fileReal) };
}

/**
 * Signed only with a manifest entry, matching sha256, signed_by, and a
 * GitHub sign-off on this repo. Path escapes are hard failures. Anything
 * else unsigned is "no comps".
 */
export function evaluateComp(entry, manifestDir) {
  if (!entry) return { signed: false, hardFail: false, reason: 'no signed comp' };
  const located = compPathVerdict(entry, manifestDir);
  if (!located.ok) {
    return { signed: false, hardFail: located.hardFail, reason: located.reason };
  }
  const digest = sha256(located.bytes);
  if (typeof entry.sha256 !== 'string' || digest !== entry.sha256.toLowerCase()) {
    return { signed: false, hardFail: false, reason: 'sha256 mismatch', file: located.file };
  }
  if (typeof entry.signed_by !== 'string' || entry.signed_by.trim() === '') {
    return { signed: false, hardFail: false, reason: 'missing signed_by', file: located.file };
  }
  if (!signoffOk(entry.signoff)) {
    return { signed: false, hardFail: false, reason: 'missing sign-off', file: located.file };
  }
  return { signed: true, hardFail: false, reason: 'signed', file: located.file, bytes: located.bytes };
}

export function countSignedComps(manifest, manifestDir) {
  const comps = Array.isArray(manifest?.comps) ? manifest.comps : [];
  return comps.filter((entry) => evaluateComp(entry, manifestDir).signed).length;
}

export function findCompEntry(manifest, route, widthName) {
  const comps = Array.isArray(manifest.comps) ? manifest.comps : [];
  return (
    comps.find(
      (entry) => entry.route === route && String(entry.width) === String(widthName)
    ) || null
  );
}
