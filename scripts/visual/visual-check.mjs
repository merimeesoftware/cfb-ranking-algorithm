import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  WIDTHS,
  MAX_MASK_AREA_RATIO,
  EXIT_FAIL,
  EXIT_NO_COMPS,
  maskAreaRatio,
  resolveThresholds,
  exitCodeForReport,
} from './lib/visual-rules.mjs';
import { countSignedComps, evaluateComp, findCompEntry } from './lib/comps.mjs';
import { comparePngBuffers, sideBySidePng } from './lib/compare-stills.mjs';
import { startFixtureServer } from './lib/fixture-server.mjs';
import { launchChrome, captureViewport } from './lib/capture.mjs';
import { assertPreviewTarget } from './lib/preview-url.mjs';
import { buildSummary } from './lib/summary.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, '../..');

function fail(code, message) {
  console.error(message);
  process.exit(code);
}

function parseArgs(argv) {
  const args = {
    build: null,
    fixtureDir: null,
    manifest: null,
    base: null,
    out: path.join(REPO_ROOT, 'preview-stills-out'),
    url: null,
    sha: null,
    captureOnly: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    const next = () => {
      const value = argv[i + 1];
      if (!value || value.startsWith('--')) fail(2, `missing value for ${token}`);
      i += 1;
      return value;
    };
    if (token === '--build') args.build = next();
    else if (token === '--fixture-dir') args.fixtureDir = next();
    else if (token === '--manifest') args.manifest = next();
    else if (token === '--base') args.base = next();
    else if (token === '--out') args.out = next();
    else if (token === '--url') args.url = next();
    else if (token === '--sha') args.sha = next();
    else if (token === '--capture-only') args.captureOnly = true;
    else if (token === '--help' || token === '-h') args.help = true;
    else fail(2, `unknown argument ${token}`);
  }
  return args;
}

function help() {
  console.log(`usage: node visual-check.mjs --build frontend/build --base <repo-at-base-sha> [--out preview-stills-out]
       node visual-check.mjs --fixture-dir design/comps/planted --manifest <manifest.json> --out <dir>

CI passes --base, a checkout of the PR base SHA. The manifest and renders
are read only from that tree. A --manifest path is a local preview.

Exit 0 pass, 1 fail, 2 bad input, 3 no comps.
A mask covering more than 10% of the viewport fails.
A comp whose realpath leaves design/comps/renders fails.`);
}

function loadManifest(file) {
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(file, 'utf8'));
  } catch (error) {
    fail(2, `could not read manifest ${file}: ${error.message}`);
  }
  if (!parsed || !Array.isArray(parsed.routes) || parsed.routes.length === 0) {
    fail(2, `manifest ${file} needs a non-empty routes array`);
  }
  return parsed;
}

function slug(route, width) {
  const name = route.replace(/^\//, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '');
  return `${name || 'home'}-${width}`;
}

function writeOutputs(outDir, report) {
  mkdirSync(outDir, { recursive: true });
  const summary = buildSummary(report);
  writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
  writeFileSync(path.join(outDir, 'summary.md'), summary);
  return summary;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    help();
    return;
  }
  if (args.url && (args.build || args.fixtureDir)) fail(2, 'pass either --url or a local root, not both');
  if (!args.url && !args.build && !args.fixtureDir) {
    fail(2, 'pass --build frontend/build or --fixture-dir <dir>');
  }
  if (args.build && args.fixtureDir) fail(2, 'pass only one of --build and --fixture-dir');
  if (args.base && args.manifest) fail(2, 'pass only one of --base and --manifest');
  if (!args.base && !args.manifest) {
    args.manifest = path.join(REPO_ROOT, 'design/comps/manifest.json');
  }

  const manifestPath = args.base
    ? path.join(path.resolve(args.base), 'design/comps/manifest.json')
    : path.resolve(args.manifest);
  const manifest = loadManifest(manifestPath);
  const manifestDir = path.dirname(manifestPath);
  const signedCompCount = countSignedComps(manifest, manifestDir);
  const thresholds = resolveThresholds(manifest);
  const outDir = path.resolve(args.out);
  mkdirSync(outDir, { recursive: true });

  let origin;
  let server = null;
  if (args.url) {
    const preview = await assertPreviewTarget(args.url, args.sha);
    origin = preview.origin;
  } else {
    const apiFixture = args.build
      ? JSON.parse(readFileSync(path.join(REPO_ROOT, 'design/comps/api/rankings.json'), 'utf8'))
      : null;
    server = await startFixtureServer({
      buildDir: args.build ? path.resolve(args.build) : null,
      fixtureDir: args.fixtureDir ? path.resolve(args.fixtureDir) : null,
      apiFixture,
      logoPath: path.join(REPO_ROOT, 'design/comps/planted/logo.svg'),
    });
    origin = server.origin;
  }

  const violations = [];
  const results = [];
  let chromeVersion = '';
  let browser;
  try {
    const launched = await launchChrome();
    browser = launched.browser;
    chromeVersion = launched.version;
    for (const route of manifest.routes) {
      if (!route || typeof route.path !== 'string' || !route.path.startsWith('/')) {
        const error = new Error('each route path must start with /');
        error.exitCode = 2;
        throw error;
      }
      for (const viewport of WIDTHS) {
        const target = new URL(route.path, origin).href;
        const routeViolations = [];
        let shot;
        try {
          shot = await captureViewport(browser, {
            url: target,
            width: viewport.width,
            height: viewport.height,
            allowedOrigin: origin,
            violations: routeViolations,
          });
        } catch (error) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'fail',
            reason: `capture error: ${error.message}`,
          });
          violations.push(...routeViolations);
          continue;
        }
        violations.push(...routeViolations);
        const fileStem = slug(route.path, viewport.name);
        const actualName = `${fileStem}.png`;
        writeFileSync(path.join(outDir, actualName), shot.png);

        if (shot.status >= 400) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'fail',
            reason: `HTTP ${shot.status}`,
            actual: actualName,
            flags: shot.flags,
          });
          continue;
        }
        if (routeViolations.length > 0) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'fail',
            reason: `request guard: ${routeViolations.map((hit) => hit.kind).join(', ')}`,
            actual: actualName,
            flags: shot.flags,
          });
          continue;
        }
        if (args.captureOnly) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'no comps',
            reason: 'capture only; comp not signed',
            actual: actualName,
          });
          continue;
        }

        const entry = findCompEntry(manifest, route.path, viewport.name);
        const verdict = evaluateComp(entry, manifestDir);
        if (verdict.hardFail) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'fail',
            reason: verdict.reason,
            actual: actualName,
          });
          continue;
        }
        if (!verdict.signed) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'no comps',
            reason: verdict.reason,
            actual: actualName,
          });
          continue;
        }

        const maskRatio = maskAreaRatio(entry.masks, viewport.width, viewport.height);
        if (maskRatio > MAX_MASK_AREA_RATIO) {
          results.push({
            route: route.path,
            width: viewport.name,
            status: 'fail',
            reason: `mask area ${(maskRatio * 100).toFixed(1)}% exceeds 10%`,
            actual: actualName,
          });
          continue;
        }

        const diff = comparePngBuffers(shot.png, verdict.bytes, {
          pixelmatchThreshold: thresholds.pixelmatchThreshold,
          maxDiffRatio: thresholds.maxDiffRatio,
          masks: entry.masks || [],
        });
        const row = {
          route: route.path,
          width: viewport.name,
          status: diff.status,
          reason: diff.reason,
          diffPixels: diff.diffPixels,
          ratio: diff.ratio,
          actual: actualName,
          comp: path.relative(manifestDir, verdict.file),
        };
        if (diff.diffPng) {
          const diffName = `${fileStem}.diff.png`;
          const sideName = `${fileStem}.side-by-side.png`;
          writeFileSync(path.join(outDir, diffName), diff.diffPng);
          writeFileSync(
            path.join(outDir, sideName),
            sideBySidePng(verdict.bytes, diff.diffPng, shot.png)
          );
          row.diff = diffName;
          row.sideBySide = sideName;
        }
        results.push(row);
      }
    }
  } finally {
    if (browser) await browser.close();
    if (server) await server.close();
  }

  const report = {
    chrome: chromeVersion,
    pixelmatchThreshold: thresholds.pixelmatchThreshold,
    maxDiffRatio: thresholds.maxDiffRatio,
    captureOnly: args.captureOnly,
    manifestSource: args.base ? 'base' : 'manifest',
    manifestPath,
    signedCompCount,
    agentHits: server ? server.agentHits.length : 0,
    violations,
    results,
  };
  report.exitCode = exitCodeForReport(report);
  const summary = writeOutputs(outDir, report);
  console.log(summary);
  if (report.exitCode === EXIT_FAIL) process.exit(EXIT_FAIL);
  if (report.exitCode === EXIT_NO_COMPS) process.exit(EXIT_NO_COMPS);
}

main().catch((error) => {
  const code = error.exitCode || 1;
  console.error(error.stack || error.message);
  process.exit(code);
});
