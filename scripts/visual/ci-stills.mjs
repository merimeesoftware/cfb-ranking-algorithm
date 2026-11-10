/**
 * CI wrapper. visual-check.mjs stays the gate (exit 3 = no comps).
 * This process turns exit 3 into 0 only while the trusted manifest has
 * zero signed comps. A signed comp on that manifest makes exit 3 fail the job.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { EXIT_NO_COMPS, decideCiExit } from './lib/visual-rules.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const forwarded = process.argv.slice(2);
const outFlag = forwarded.indexOf('--out');
if (outFlag === -1 || !forwarded[outFlag + 1]) {
  console.error('ci-stills.mjs requires --out');
  process.exit(2);
}
const outDir = path.resolve(forwarded[outFlag + 1]);

const child = spawnSync(process.execPath, [path.join(here, 'visual-check.mjs'), ...forwarded], {
  stdio: 'inherit',
});
const checkerExit = child.status ?? 1;

let signedCompCount = null;
try {
  const report = JSON.parse(readFileSync(path.join(outDir, 'report.json'), 'utf8'));
  signedCompCount = report.signedCompCount;
} catch {
  signedCompCount = null;
}

const decided = decideCiExit(checkerExit, signedCompCount ?? -1);
if (checkerExit === EXIT_NO_COMPS && signedCompCount === 0) {
  console.log(
    'Bootstrap: trusted manifest has zero signed comps. Checker exit 3 is allowed.'
  );
} else if (checkerExit === EXIT_NO_COMPS && (signedCompCount || 0) > 0) {
  console.error(
    'Checker exit 3 fails the job: the trusted manifest has signed comps and a route is no comps.'
  );
}
if (decided !== checkerExit) {
  console.log(`CI policy: checker exit ${checkerExit} -> ${decided}`);
}
process.exit(decided);
