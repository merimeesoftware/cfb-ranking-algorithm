#!/usr/bin/env node
/**
 * Build the Worker bundle, test that file, scan it, and refuse a deploy
 * dry-run whose worker bytes differ.
 *
 * The bundle command is wrangler deploy --dry-run. wrangler.toml points main
 * at the result with no_bundle, so this step uses wrangler.bundle.toml.
 * --containers-rollout=none keeps the dry-run off the Dockerfile image.
 * The deploy command still builds that image when it uploads.
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const testedDir = join(repoRoot, '.wrangler/tested');
const uploadDir = join(repoRoot, '.wrangler/upload');
const testedBundle = join(testedDir, 'index.js');

function fail(message) {
	console.error(message);
	process.exit(1);
}

function sha256(path) {
	return createHash('sha256').update(readFileSync(path)).digest('hex');
}

function run(args, cwd) {
	const env = {
		...process.env,
		CI: 'true',
		WRANGLER_SEND_METRICS: 'false',
	};
	for (const key of [
		'CLOUDFLARE_API_TOKEN',
		'CLOUDFLARE_API_KEY',
		'CLOUDFLARE_ACCOUNT_ID',
		'CFBD_API_KEY',
		'XAI_API_KEY',
	]) {
		delete env[key];
	}
	const result = spawnSync(args[0], args.slice(1), { cwd, env, stdio: 'inherit' });
	if (result.error) fail(result.error.message);
	if (result.status !== 0) process.exit(result.status ?? 1);
}

function compatibilityDate(path) {
	const match = readFileSync(path, 'utf8').match(/^compatibility_date\s*=\s*"([^"]+)"/m);
	if (!match) fail(`${path} is missing compatibility_date`);
	return match[1];
}

function workerFiles(dir) {
	return readdirSync(dir).filter((name) => name !== 'README.md').sort();
}

function compareUpload(testedDirPath, uploadDirPath) {
	const testedNames = workerFiles(testedDirPath);
	const uploadNames = workerFiles(uploadDirPath);
	const testedHash = existsSync(join(testedDirPath, 'index.js')) ? sha256(join(testedDirPath, 'index.js')) : '';
	const uploadHash = existsSync(join(uploadDirPath, 'index.js')) ? sha256(join(uploadDirPath, 'index.js')) : '';
	if (testedNames.join('\n') !== 'index.js' || uploadNames.join('\n') !== testedNames.join('\n')) {
		return {
			ok: false,
			testedHash,
			reason: `upload files [${uploadNames.join(', ')}] do not match tested bundle files [${testedNames.join(', ')}]`,
		};
	}
	if (uploadHash !== testedHash) {
		return {
			ok: false,
			testedHash,
			reason: `upload sha256 ${uploadHash} does not match tested worker bundle ${testedHash}`,
		};
	}
	return { ok: true, testedHash };
}

function assertCheckerFailsClosed() {
	const root = mkdtempSync(join(tmpdir(), 'bundle-check-'));
	const tested = join(root, 'tested');
	const upload = join(root, 'upload');
	mkdirSync(tested);
	mkdirSync(upload);
	writeFileSync(join(tested, 'index.js'), 'same');
	writeFileSync(join(tested, 'README.md'), 'built');
	writeFileSync(join(upload, 'index.js'), 'same');
	writeFileSync(join(upload, 'README.md'), 'later');
	if (!compareUpload(tested, upload).ok) fail('checker rejected identical worker bytes');
	writeFileSync(join(upload, 'index.js'), 'different');
	if (compareUpload(tested, upload).ok) fail('checker accepted a different worker file');
	writeFileSync(join(upload, 'index.js'), 'same');
	writeFileSync(join(upload, 'extra.js'), 'x');
	if (compareUpload(tested, upload).ok) fail('checker accepted an extra upload file');
	rmSync(root, { recursive: true, force: true });
}

assertCheckerFailsClosed();

const deployDate = compatibilityDate(join(repoRoot, 'wrangler.toml'));
const bundleDate = compatibilityDate(join(repoRoot, 'wrangler.bundle.toml'));
if (deployDate !== bundleDate) {
	fail(`compatibility_date ${bundleDate} in wrangler.bundle.toml does not match ${deployDate} in wrangler.toml`);
}

if (!existsSync(join(repoRoot, 'frontend/build'))) {
	fail('frontend/build is missing. Build the frontend before the Worker bundle.');
}

rmSync(testedDir, { recursive: true, force: true });
rmSync(uploadDir, { recursive: true, force: true });

run(['npm', 'ci', '--prefix', 'worker'], repoRoot);

run([
	'npx', 'wrangler', 'deploy',
	'--config', 'wrangler.bundle.toml',
	'--dry-run',
	'--outdir', '.wrangler/tested',
	'--containers-rollout=none',
	'--env=',
], repoRoot);

if (!existsSync(testedBundle)) fail(`missing ${testedBundle}`);

run([
	process.execPath,
	'--experimental-strip-types',
	'--disable-warning=MODULE_TYPELESS_PACKAGE_JSON',
	'--import', './test/register-cf-loader.mjs',
	'--test',
	'test/bundle-smoke.test.ts',
	'test/caps.test.ts',
], join(repoRoot, 'worker'));

run([process.execPath, 'scripts/check-public-host.mjs', '--self-test'], repoRoot);
run([
	process.execPath,
	'scripts/check-public-host.mjs',
	'frontend/build',
	'.wrangler/tested/index.js',
	'worker/src',
	'--python',
	'--public-docs',
], repoRoot);

const testedHash = sha256(testedBundle);
console.log(`tested worker bundle sha256: ${testedHash}`);

run([
	'npx', 'wrangler', 'deploy',
	'--dry-run',
	'--outdir', '.wrangler/upload',
	'--containers-rollout=none',
	'--env=',
], repoRoot);

const compared = compareUpload(testedDir, uploadDir);
if (!compared.ok) fail(compared.reason);
if (compared.testedHash !== testedHash) fail('tested bundle changed during the upload dry-run');
