/**
 * Proves every check-comps guard in both directions: each planted fixture must
 * fail exactly its guard (and nothing else), base.html must pass every guard,
 * and the real package must pass. Exit 0 only when all proofs hold.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { sourceGuard, GAMBLING_RE } from './check-comps.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const P = (f) => path.join(HERE, 'planted', f);
const tmp = mkdtempSync(path.join(tmpdir(), 'why-here-'));
const cases = [
  ['base.html', null],
  ['parts-sum.html', 'parts-sum'],
  ['part-label.html', 'part-label'],
  ['overflow-390.html', 'overflow-390'],
  ['tap-44.html', 'tap-44'],
  ['focus-visible.html', 'focus-visible'],
  ['no-gambling.html', 'no-gambling'],
  ['copy-slots-unlocked.html', 'copy-slots'],
  ['copy-slots-placeholder.html', 'copy-slots'],
  ['tokens.html', 'tokens'],
  ['structure.html', 'structure'],
  ['share-card-wrong-size.html', 'share-card'],
];
const failures = [];
const rows = [];
for (const [file, guard] of cases) {
  const out = path.join(tmp, file + '.json');
  const r = spawnSync(process.execPath, [path.join(HERE, 'check-comps.mjs'), '--json', out, P(file)], { encoding: 'utf8' });
  const report = JSON.parse(readFileSync(out, 'utf8'));
  const failed = [...new Set(report.failures.map((f) => f.guard))].sort();
  const want = guard ? [guard] : [];
  const ok = (guard ? r.status === 1 : r.status === 0) && JSON.stringify(failed) === JSON.stringify(want);
  rows.push(`${ok ? 'ok  ' : 'BAD '} ${file.padEnd(30)} exit ${r.status} failed [${failed.join(', ')}] expected [${want.join(', ')}]`);
  if (!ok) failures.push(file);
}
const hits = sourceGuard([P('hardcoded-weight.mjs')]);
const okSrc = hits.length >= 1;
rows.push(`${okSrc ? 'ok  ' : 'BAD '} ${'hardcoded-weight.mjs'.padEnd(30)} data-driven hits ${hits.join(', ') || 'none'} expected ≥1`);
if (!okSrc) failures.push('hardcoded-weight.mjs');
const words = ['bet', 'odds', 'market', 'spread', 'line', 'pick', 'lock-of-the-week', 'lock of the week', 'Betting', 'PICKS'];
const missed = words.filter((w) => !GAMBLING_RE.test(`x ${w} x`));
const falsePos = ['headline', 'online', 'outline', 'betterment', 'Alphabet', 'how they look', 'who they beat', 'league strength', 'How good they actually are.'].filter((w) => GAMBLING_RE.test(w));
rows.push(`${missed.length + falsePos.length === 0 ? 'ok  ' : 'BAD '} ${'gambling word list'.padEnd(30)} ${words.length} words caught, ${falsePos.length} false positives${missed.length ? ' missed ' + missed.join(',') : ''}`);
if (missed.length || falsePos.length) failures.push('gambling words');
const clean = sourceGuard([path.join(HERE, 'render.mjs'), path.join(HERE, 'comp.css')]);
rows.push(`${clean.length === 0 ? 'ok  ' : 'BAD '} ${'render.mjs + comp.css'.padEnd(30)} data-driven hits ${clean.length} expected 0`);
if (clean.length) failures.push('renderer');
const pkg = spawnSync(process.execPath, [path.join(HERE, 'check-comps.mjs')], { encoding: 'utf8' });
rows.push(`${pkg.status === 0 ? 'ok  ' : 'BAD '} ${'package (states/*.html)'.padEnd(30)} exit ${pkg.status} — ${pkg.stdout.trim().split('\n').pop()}`);
if (pkg.status !== 0) failures.push('package');
console.log(rows.join('\n'));
console.log(failures.length ? `${failures.length} proof(s) failed: ${failures.join(', ')}` : `all ${rows.length} proofs hold`);
process.exit(failures.length ? 1 : 0);
