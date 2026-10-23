/**
 * Proves the stills gate in both directions.
 * A planted page with the same elements and the same title text, but a
 * different colour and block position, must exit 1. A matching still must
 * pass. A route with no signed comp must exit 3, never 0.
 * A page that calls /api/agent, an off-site origin, or a websocket must
 * trip the guard without the fixture server receiving /api/agent.
 * A signature that exists only on a side tree is ignored when --base
 * points at an empty manifest. An oversized mask and a path-escape
 * comp exit 1.
 *
 * --fail-job-on-planted-mismatch exits with the gate's status (1) after the
 * proof, so a CI job can show the red run. The default run exits 0 when
 * every proof holds.
 */
import { spawn } from 'node:child_process';
import { copyFileSync, mkdtempSync, mkdirSync, readFileSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  EXIT_FAIL,
  EXIT_NO_COMPS,
  EXIT_PASS,
  classifyRequest,
  decideCiExit,
  maskAreaRatio,
  resolveThresholds,
} from './lib/visual-rules.mjs';
import { assertPreviewTarget } from './lib/preview-url.mjs';
import { evaluateComp, sha256, signoffOk } from './lib/comps.mjs';
import { comparePngBuffers, solidPng } from './lib/compare-stills.mjs';
import { rewriteCaptureText } from './lib/rewrite.mjs';
import { buildSummary } from './lib/summary.mjs';
import { launchChrome, captureViewport } from './lib/capture.mjs';
import { startFixtureServer } from './lib/fixture-server.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../..');
const PLANTED = path.join(REPO, 'design/comps/planted');
const SIGNOFF =
  'https://github.com/merimeesoftware/cfb-ranking-algorithm/issues/94#issuecomment-planted-match';
const PROPAGATE = process.argv.includes('--fail-job-on-planted-mismatch');
const failures = [];

function assert(condition, message) {
  if (!condition) failures.push(message);
}

function runNode(script, args) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [path.join(HERE, script), ...args], {
      cwd: HERE,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });
    child.on('close', (code) => resolve({ code, stdout, stderr }));
  });
}

function runCli(args) {
  return runNode('visual-check.mjs', args);
}

function runCi(args) {
  return runNode('ci-stills.mjs', args);
}

function readReport(dir) {
  return JSON.parse(readFileSync(path.join(dir, 'report.json'), 'utf8'));
}

function row(report, route, width) {
  return report.results.find((item) => item.route === route && String(item.width) === String(width));
}

async function previewHostTests() {
  let message = '';
  let code = 0;
  try {
    await assertPreviewTarget(`https://example.com/rankings`, 'a'.repeat(40));
  } catch (error) {
    message = error.message;
    code = error.exitCode;
  }
  assert(code === 2, 'a preview host outside the allowlist exits 2');
  assert(message.includes('not allowlisted'), 'a preview host outside the allowlist is rejected before capture');
}

function unitTests() {
  assert(classifyRequest('http://127.0.0.1:9/api/rankings', 'http://127.0.0.1:9') === 'ok', 'same-origin /api/rankings is allowed');
  assert(classifyRequest('http://127.0.0.1:9/api/agent/explain', 'http://127.0.0.1:9') === 'agent', '/api/agent is blocked');
  assert(classifyRequest('http://127.0.0.1:9/api/agent', 'http://127.0.0.1:9') === 'agent', '/api/agent with no suffix is blocked');
  assert(
    classifyRequest('https://api.collegefootballdata.com/games', 'http://127.0.0.1:9') === 'offsite',
    'CFBD origin is offsite'
  );
  assert(classifyRequest('https://fonts.googleapis.com/css?family=Oswald', 'http://127.0.0.1:9') === 'offsite', 'Google Fonts is offsite');
  assert(classifyRequest('data:image/png;base64,aaaa', 'http://127.0.0.1:9') === 'ok', 'data URLs are not network');

  const rewritten = rewriteCaptureText(
    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n<link href="https://fonts.googleapis.com/css2?family=Oswald&display=swap" rel="stylesheet" />\n<img src="https://cdn.collegefootballdata.com/logos/500/1.png" />'
  );
  assert(!rewritten.includes('fonts.googleapis.com'), 'font links are removed');
  assert(!rewritten.includes('collegefootballdata.com'), 'CFBD logo URLs are rewritten');
  assert(rewritten.includes('/__visual/logo.svg'), 'logos point at the capture server');

  assert(signoffOk(SIGNOFF), 'issue sign-off URL is accepted');
  assert(!signoffOk('https://example.com/signed'), 'off-repo sign-off is rejected');
  assert(!signoffOk(''), 'empty sign-off is rejected');

  let threw = false;
  try {
    resolveThresholds({ pixelmatchThreshold: 1, maxDiffRatio: 0.5 });
  } catch (error) {
    threw = error.exitCode === 2;
  }
  assert(threw, 'a threshold that would silent-pass is rejected');

  const same = solidPng(20, 10, [26, 61, 46, 255]);
  const shifted = solidPng(20, 10, [139, 30, 63, 255]);
  const identical = comparePngBuffers(same, same, { pixelmatchThreshold: 0.1, maxDiffRatio: 0.002 });
  const different = comparePngBuffers(shifted, same, { pixelmatchThreshold: 0.1, maxDiffRatio: 0.002 });
  assert(identical.status === 'pass' && identical.diffPixels === 0, 'identical pixels pass');
  assert(different.status === 'fail' && different.ratio > 0.5, 'recolored pixels fail even though the canvas is the same size');

  const unsignedDir = mkdtempSync(path.join(tmpdir(), 'unsigned-'));
  mkdirSync(path.join(unsignedDir, 'renders'));
  writeFileSync(path.join(unsignedDir, 'renders', 'comp.png'), same);
  const badHash = evaluateComp(
    {
      file: 'renders/comp.png',
      sha256: '0'.repeat(64),
      signed_by: 'owner:dean-cfb',
      signoff: SIGNOFF,
    },
    unsignedDir
  );
  assert(!badHash.signed && !badHash.hardFail && badHash.reason === 'sha256 mismatch', 'sha256 mismatch is not signed');
  const noBy = evaluateComp(
    { file: 'renders/comp.png', sha256: sha256(same), signed_by: '', signoff: SIGNOFF },
    unsignedDir
  );
  assert(!noBy.signed && noBy.reason === 'missing signed_by', 'missing signed_by is not signed');
  assert(evaluateComp(null, unsignedDir).reason === 'no signed comp', 'missing entry is no signed comp');
  const escaped = evaluateComp(
    { file: '../comp.png', sha256: sha256(same), signed_by: 'owner:dean-cfb', signoff: SIGNOFF },
    unsignedDir
  );
  assert(escaped.hardFail && escaped.reason === 'comp path escapes renders', 'a .. comp path is a hard failure');
  const outside = path.join(unsignedDir, 'outside.png');
  writeFileSync(outside, same);
  symlinkSync(outside, path.join(unsignedDir, 'renders', 'linked.png'));
  const linked = evaluateComp(
    {
      file: 'renders/linked.png',
      sha256: sha256(same),
      signed_by: 'owner:dean-cfb',
      signoff: SIGNOFF,
    },
    unsignedDir
  );
  assert(linked.hardFail && !linked.signed, 'a symlink out of renders is not signed');
  assert(maskAreaRatio([{ x: 0, y: 0, width: 390, height: 844 }], 390, 844) > 0.1, 'a full-viewport mask exceeds 10%');
  assert(maskAreaRatio([{ x: 0, y: 0, width: 20, height: 10 }], 390, 844) < 0.1, 'a small mask is under the cap');
  assert(decideCiExit(EXIT_NO_COMPS, 0) === EXIT_PASS, 'exit 3 is allowed only with zero signed comps');
  assert(decideCiExit(EXIT_NO_COMPS, 1) === EXIT_NO_COMPS, 'exit 3 fails once a comp is signed');
  assert(decideCiExit(EXIT_FAIL, 0) === EXIT_FAIL, 'a pixel or guard failure is never turned into a pass');

  const noCompsSummary = buildSummary({
    chrome: 'test',
    pixelmatchThreshold: 0.1,
    maxDiffRatio: 0.002,
    agentHits: 0,
    violations: [],
    results: [
      { route: '/methodology', width: '390', status: 'no comps', reason: 'no signed comp' },
      { route: '/methodology', width: '1440', status: 'no comps', reason: 'no signed comp' },
    ],
  });
  assert(noCompsSummary.includes('This run is not a pass.'), 'all-no-comps summary is not a pass');
  assert(!/\| pass \|/.test(noCompsSummary), 'no-comps summary has no pass row');
}

async function signedManifest(server) {
  const dir = mkdtempSync(path.join(tmpdir(), 'stills-comps-'));
  const { browser } = await launchChrome();
  try {
    for (const viewport of [
      { name: '390', width: 390, height: 844 },
      { name: '1440', width: 1440, height: 900 },
    ]) {
      const shot = await captureViewport(browser, {
        url: `${server.origin}/match`,
        width: viewport.width,
        height: viewport.height,
        allowedOrigin: server.origin,
        violations: [],
      });
      const filename = `match-${viewport.name}.png`;
      mkdirSync(path.join(dir, 'renders'), { recursive: true });
      writeFileSync(path.join(dir, 'renders', filename), shot.png);
    }
  } finally {
    await browser.close();
  }
  const comps = [];
  for (const width of ['390', '1440']) {
    const filename = `match-${width}.png`;
    const bytes = readFileSync(path.join(dir, 'renders', filename));
    for (const route of ['/match', '/mismatch']) {
      comps.push({
        route,
        width,
        file: `renders/${filename}`,
        sha256: sha256(bytes),
        signed_by: 'owner:dean-cfb',
        signoff: SIGNOFF,
      });
    }
  }
  const manifest = {
    version: 1,
    routes: [
      { path: '/match', name: 'match' },
      { path: '/mismatch', name: 'mismatch' },
      { path: '/nocomp', name: 'nocomp' },
    ],
    comps,
  };
  writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest));
  writeFileSync(path.join(dir, 'stray-390.png'), solidPng(4, 4, [1, 2, 3, 255]));
  return dir;
}

async function integrationTests() {
  const matchHtml = readFileSync(path.join(PLANTED, 'match.html'), 'utf8');
  const mismatchHtml = readFileSync(path.join(PLANTED, 'mismatch.html'), 'utf8');
  for (const marker of ['data-check="board"', 'data-check="title"', 'data-check="block"', '>True Rankings<']) {
    assert(matchHtml.includes(marker) && mismatchHtml.includes(marker), `both planted pages contain ${marker}`);
  }
  assert(matchHtml !== mismatchHtml, 'planted pages are not the same file');

  const server = await startFixtureServer({ fixtureDir: PLANTED });
  let compDir;
  try {
    compDir = await signedManifest(server);
  } finally {
    await server.close();
  }

  const outDir = (name) => {
    const dir = process.env.VISUAL_SELF_TEST_OUT
      ? path.join(process.env.VISUAL_SELF_TEST_OUT, name)
      : path.join(compDir, `out-${name}`);
    mkdirSync(dir, { recursive: true });
    return dir;
  };

  const diffOut = outDir('mismatch');
  const mismatchRun = await runCli([
    '--fixture-dir',
    PLANTED,
    '--manifest',
    path.join(compDir, 'manifest.json'),
    '--out',
    diffOut,
  ]);
  const mismatchReport = mismatchRun.code === null ? null : safeReport(diffOut);
  console.log('--- planted mismatch gate ---');
  console.log(mismatchRun.stdout);
  if (mismatchRun.stderr) console.error(mismatchRun.stderr);
  assert(mismatchRun.code === 1, `mismatch run should exit 1, got ${mismatchRun.code}`);
  if (mismatchReport) {
    for (const width of ['390', '1440']) {
      const ok = row(mismatchReport, '/match', width);
      const bad = row(mismatchReport, '/mismatch', width);
      const bare = row(mismatchReport, '/nocomp', width);
      assert(ok && ok.status === 'pass', `matching ${width} should pass`);
      assert(bad && bad.status === 'fail' && bad.reason === 'pixels differ', `mismatch ${width} should fail on pixels`);
      assert(bad && bad.ratio > 0.02, `mismatch ${width} diff ratio should be obvious`);
      assert(bare && bare.status === 'no comps', `nocomp ${width} should be no comps`);
      assert(!bare || bare.status !== 'pass', `nocomp ${width} must not pass`);
    }
    const stray = mismatchReport.results.find((item) => String(item.comp || '').includes('stray'));
    assert(!stray, 'a comp file that is not in the manifest must not be scored');
  }

  const bareOut = process.env.VISUAL_SELF_TEST_OUT
    ? path.join(process.env.VISUAL_SELF_TEST_OUT, 'nocomp')
    : path.join(compDir, 'out-nocomp');
  const bareManifest = {
    routes: [{ path: '/nocomp', name: 'nocomp' }],
    comps: [],
  };
  const bareManifestPath = path.join(compDir, 'nocomp-manifest.json');
  writeFileSync(bareManifestPath, JSON.stringify(bareManifest));
  const bareRun = await runCli(['--fixture-dir', PLANTED, '--manifest', bareManifestPath, '--out', bareOut]);
  console.log('--- no comps ---');
  console.log(bareRun.stdout);
  assert(bareRun.code === 3, `no-comps run should exit 3, got ${bareRun.code}`);
  const bareReport = safeReport(bareOut);
  assert(
    bareReport && bareReport.results.every((item) => item.status === 'no comps'),
    'every unsigned route is no comps'
  );
  assert(bareRun.stdout.includes('This run is not a pass.'), 'no-comps stdout says this run is not a pass');

  const hashManifest = {
    routes: [{ path: '/match', name: 'match' }],
    comps: [
      {
        route: '/match',
        width: '390',
        file: 'renders/match-390.png',
        sha256: 'ab'.repeat(32),
        signed_by: 'owner:dean-cfb',
        signoff: SIGNOFF,
      },
      {
        route: '/match',
        width: '1440',
        file: 'renders/match-1440.png',
        sha256: 'ab'.repeat(32),
        signed_by: 'owner:dean-cfb',
        signoff: SIGNOFF,
      },
    ],
  };
  const hashManifestPath = path.join(compDir, 'bad-hash.json');
  writeFileSync(hashManifestPath, JSON.stringify(hashManifest));
  const hashOut = path.join(compDir, 'out-hash');
  const hashRun = await runCli(['--fixture-dir', PLANTED, '--manifest', hashManifestPath, '--out', hashOut]);
  const hashReport = safeReport(hashOut);
  assert(hashRun.code === 3, `sha256 mismatch should exit 3, got ${hashRun.code}`);
  assert(
    hashReport && hashReport.results.every((item) => item.status === 'no comps' && item.reason === 'sha256 mismatch'),
    'sha256 mismatch is no comps'
  );

  const guardManifest = {
    routes: [{ path: '/offsite', name: 'offsite' }],
    comps: [],
  };
  const guardManifestPath = path.join(compDir, 'guard.json');
  writeFileSync(guardManifestPath, JSON.stringify(guardManifest));
  const guardOut = process.env.VISUAL_SELF_TEST_OUT
    ? path.join(process.env.VISUAL_SELF_TEST_OUT, 'guard')
    : path.join(compDir, 'out-guard');
  const guardRun = await runCli(['--fixture-dir', PLANTED, '--manifest', guardManifestPath, '--out', guardOut]);
  console.log('--- planted request guard ---');
  console.log(guardRun.stdout);
  if (guardRun.stderr) console.error(guardRun.stderr);
  const guardReport = safeReport(guardOut);
  assert(guardRun.code === 1, `guard run should exit 1, got ${guardRun.code}`);
  assert(guardReport && guardReport.agentHits === 0, 'fixture server must not receive /api/agent');
  const kinds = new Set((guardReport?.violations || []).map((hit) => hit.kind));
  assert(kinds.has('agent'), 'guard records /api/agent');
  assert(kinds.has('offsite'), 'guard records the off-site origin');
  const agentUrl = (guardReport?.violations || []).some((hit) => hit.url.includes('/api/agent/explain'));
  const offUrl = (guardReport?.violations || []).some((hit) =>
    hit.url.startsWith('https://api.collegefootballdata.com/')
  );
  assert(agentUrl, 'agent violation URL is /api/agent/explain');
  assert(offUrl, 'offsite violation URL is the CFBD API');
  const flags = guardReport?.results?.[0]?.flags;
  assert(flags && flags.agent === 'blocked', `page saw /api/agent blocked, got ${flags && flags.agent}`);
  assert(flags && flags.offsite === 'blocked', `page saw off-site fetch blocked, got ${flags && flags.offsite}`);
  assert(kinds.has('websocket'), 'guard records a websocket and does not connect it');

  const exits = {};
  exits.PLANTED_MISMATCH_EXIT = mismatchRun.code;
  exits.PLANTED_NOCOMP_EXIT = bareRun.code;
  exits.PLANTED_BAD_HASH_EXIT = hashRun.code;
  exits.PLANTED_GUARD_EXIT = guardRun.code;

  const baseRoot = path.join(compDir, 'base-repo');
  const baseManifestDir = path.join(baseRoot, 'design/comps');
  mkdirSync(baseManifestDir, { recursive: true });
  writeFileSync(
    path.join(baseManifestDir, 'manifest.json'),
    JSON.stringify({
      routes: [{ path: '/match', name: 'match' }],
      comps: [],
    })
  );
  const prRoot = path.join(compDir, 'pr-repo');
  const prManifestDir = path.join(prRoot, 'design/comps');
  mkdirSync(path.join(prManifestDir, 'renders'), { recursive: true });
  const prComps = [];
  for (const width of ['390', '1440']) {
    const filename = `match-${width}.png`;
    copyFileSync(path.join(compDir, 'renders', filename), path.join(prManifestDir, 'renders', filename));
    prComps.push({
      route: '/match',
      width,
      file: `renders/${filename}`,
      sha256: sha256(readFileSync(path.join(prManifestDir, 'renders', filename))),
      signed_by: 'owner:dean-cfb',
      signoff: SIGNOFF,
    });
  }
  writeFileSync(
    path.join(prManifestDir, 'manifest.json'),
    JSON.stringify({
      routes: [{ path: '/match', name: 'match' }],
      comps: prComps,
    })
  );
  const prVerdict = evaluateComp(prComps[0], prManifestDir);
  assert(prVerdict.signed, 'the PR tree signature is well formed and would count if the head were trusted');
  const prOut = outDir('pr-signature');
  const prRun = await runCli(['--fixture-dir', PLANTED, '--base', baseRoot, '--out', prOut]);
  console.log('--- PR-added signature ignored ---');
  console.log(prRun.stdout);
  if (prRun.stderr) console.error(prRun.stderr);
  exits.PLANTED_PR_SIGNATURE_EXIT = prRun.code;
  const prReport = safeReport(prOut);
  assert(prRun.code === 3, `a PR-added signature must exit 3, got ${prRun.code}`);
  assert(prReport && prReport.manifestSource === 'base', 'CI manifest source is the base tree');
  assert(
    prReport && prReport.manifestPath === path.join(baseManifestDir, 'manifest.json'),
    'the checker read the base manifest, not the PR manifest'
  );
  assert(prReport && prReport.signedCompCount === 0, 'the base manifest contributes zero signed comps');
  assert(
    prReport && prReport.results.every((item) => item.status === 'no comps') && !prReport.results.some((item) => item.status === 'pass'),
    'a signature that exists only on the PR head does not pass'
  );

  const bootstrapOut = outDir('bootstrap-ci');
  const bootstrapRun = await runCi(['--fixture-dir', PLANTED, '--base', baseRoot, '--out', bootstrapOut]);
  console.log('--- bootstrap CI (zero signed comps) ---');
  console.log(bootstrapRun.stdout);
  exits.PLANTED_BOOTSTRAP_CI_EXIT = bootstrapRun.code;
  assert(bootstrapRun.code === 0, `exit 3 is allowed while the base has zero signed comps, got ${bootstrapRun.code}`);
  assert(bootstrapRun.stdout.includes('Bootstrap:'), 'bootstrap CI prints why exit 3 was allowed');
  const bootstrapReport = safeReport(bootstrapOut);
  assert(bootstrapReport && bootstrapReport.exitCode === 3, 'the checker still exits 3 during bootstrap');

  const maskManifest = {
    routes: [{ path: '/match', name: 'match' }],
    comps: ['390', '1440'].map((width) => {
      const viewport = width === '390' ? { width: 390, height: 844 } : { width: 1440, height: 900 };
      return {
        route: '/match',
        width,
        file: `renders/match-${width}.png`,
        sha256: sha256(readFileSync(path.join(compDir, 'renders', `match-${width}.png`))),
        signed_by: 'owner:dean-cfb',
        signoff: SIGNOFF,
        masks: [{ x: 0, y: 0, width: viewport.width, height: viewport.height }],
      };
    }),
  };
  const maskManifestPath = path.join(compDir, 'mask-manifest.json');
  writeFileSync(maskManifestPath, JSON.stringify(maskManifest));
  const maskOut = outDir('mask');
  const maskRun = await runCli(['--fixture-dir', PLANTED, '--manifest', maskManifestPath, '--out', maskOut]);
  console.log('--- oversized mask ---');
  console.log(maskRun.stdout);
  if (maskRun.stderr) console.error(maskRun.stderr);
  exits.PLANTED_MASK_EXIT = maskRun.code;
  const maskReport = safeReport(maskOut);
  assert(maskRun.code === 1, `an oversized mask must exit 1, got ${maskRun.code}`);
  assert(maskReport && maskReport.signedCompCount === 2, 'an oversized mask is still a signed comp');
  assert(
    maskReport &&
      maskReport.results.every(
        (item) => item.status === 'fail' && String(item.reason).includes('mask area') && item.reason !== 'pixels differ'
      ),
    'an oversized mask fails before the pixel diff'
  );

  const outside = path.join(compDir, 'outside.png');
  writeFileSync(outside, readFileSync(path.join(compDir, 'renders', 'match-1440.png')));
  symlinkSync(outside, path.join(compDir, 'renders', 'escaped.png'));
  const escapeManifest = {
    routes: [{ path: '/match', name: 'match' }],
    comps: [
      {
        route: '/match',
        width: '390',
        file: 'renders/../../outside.png',
        sha256: sha256(readFileSync(path.join(compDir, 'renders', 'match-390.png'))),
        signed_by: 'owner:dean-cfb',
        signoff: SIGNOFF,
      },
      {
        route: '/match',
        width: '1440',
        file: 'renders/escaped.png',
        sha256: sha256(readFileSync(outside)),
        signed_by: 'owner:dean-cfb',
        signoff: SIGNOFF,
      },
    ],
  };
  const escapeManifestPath = path.join(compDir, 'escape-manifest.json');
  writeFileSync(escapeManifestPath, JSON.stringify(escapeManifest));
  const escapeOut = outDir('path-escape');
  const escapeRun = await runCli(['--fixture-dir', PLANTED, '--manifest', escapeManifestPath, '--out', escapeOut]);
  console.log('--- path-escape comp ---');
  console.log(escapeRun.stdout);
  if (escapeRun.stderr) console.error(escapeRun.stderr);
  exits.PLANTED_PATH_ESCAPE_EXIT = escapeRun.code;
  const escapeReport = safeReport(escapeOut);
  assert(escapeRun.code === 1, `a path-escape comp must exit 1, got ${escapeRun.code}`);
  assert(
    escapeReport &&
      escapeReport.results.every((item) => item.status === 'fail' && item.reason === 'comp path escapes renders'),
    'a lexical .. path and a symlink out of renders both fail'
  );
  assert(escapeReport && escapeReport.signedCompCount === 0, 'a path-escape comp is not signed');

  const mixedManifest = {
    routes: [
      { path: '/match', name: 'match' },
      { path: '/nocomp', name: 'nocomp' },
    ],
    comps: ['390', '1440'].map((width) => ({
      route: '/match',
      width,
      file: `renders/match-${width}.png`,
      sha256: sha256(readFileSync(path.join(compDir, 'renders', `match-${width}.png`))),
      signed_by: 'owner:dean-cfb',
      signoff: SIGNOFF,
    })),
  };
  const mixedManifestPath = path.join(compDir, 'mixed-manifest.json');
  writeFileSync(mixedManifestPath, JSON.stringify(mixedManifest));
  const mixedOut = outDir('signed-nocomp');
  const mixedRun = await runCi(['--fixture-dir', PLANTED, '--manifest', mixedManifestPath, '--out', mixedOut]);
  console.log('--- signed manifest with a no-comps route ---');
  console.log(mixedRun.stdout);
  if (mixedRun.stderr) console.error(mixedRun.stderr);
  exits.PLANTED_SIGNED_NOCOMP_CI_EXIT = mixedRun.code;
  const mixedReport = safeReport(mixedOut);
  assert(mixedRun.code === 3, `exit 3 fails CI once any comp is signed, got ${mixedRun.code}`);
  assert(mixedReport && mixedReport.exitCode === 3, 'the checker exit stays 3 when a signed manifest has a no-comps route');
  assert((mixedReport?.signedCompCount || 0) > 0, 'the mixed manifest has a signed comp');
  assert(
    mixedReport && mixedReport.results.some((item) => item.status === 'pass') && mixedReport.results.some((item) => item.status === 'no comps'),
    'the mixed run both matches a signed comp and reports no comps'
  );

  return { mismatchCode: mismatchRun.code, exits };
}

function safeReport(dir) {
  try {
    return readReport(dir);
  } catch {
    failures.push(`missing report in ${dir}`);
    return null;
  }
}

async function cspHeadersTest() {
  const dir = mkdtempSync(path.join(tmpdir(), 'stills-headers-'));
  copyFileSync(path.join(REPO, 'frontend/static/_headers'), path.join(dir, '_headers'));
  writeFileSync(path.join(dir, 'index.html'), '<!doctype html><title>x</title>');
  const server = await startFixtureServer({ buildDir: dir });
  try {
    const response = await fetch(`${server.origin}/`);
    const csp = response.headers.get('content-security-policy');
    assert(csp && csp.includes("default-src 'self'"), 'stills server applies the page CSP');
    assert(csp.includes('challenges.cloudflare.com'), 'page CSP allows the Turnstile host');
    assert(
      response.headers.get('strict-transport-security')?.includes('max-age=31536000'),
      'stills server applies HSTS'
    );
    assert(response.headers.get('x-content-type-options') === 'nosniff', 'stills server applies nosniff');
  } finally {
    await server.close();
  }
}

const planted = { exits: {} };
try {
  unitTests();
  await cspHeadersTest();
  await previewHostTests();
  const result = await integrationTests();
  planted.exits = result.exits;
  planted.mismatchCode = result.mismatchCode;
} finally {
  for (const [key, value] of Object.entries(planted.exits)) {
    console.log(`${key}=${value}`);
  }
}

if (failures.length > 0) {
  console.error(`visual self-test failed (${failures.length})`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(
  'visual self-test: mismatch failed, match passed, missing comp and bad hash exited 3, PR signature ignored, oversized mask and path escape failed, guard tripped'
);
if (PROPAGATE) {
  console.log(`Propagating planted mismatch exit ${planted.mismatchCode} so the job fails.`);
  process.exit(planted.mismatchCode);
}
