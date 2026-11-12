#!/usr/bin/env node
/**
 * Build the Worker bundle, test that file, scan it, and refuse a deploy
 * packaging whose modules differ from the tested bundle.
 *
 * The bundle command is wrangler deploy --dry-run. wrangler.toml points main
 * at the result with no_bundle, so this step uses wrangler.bundle.toml.
 * --containers-rollout=none keeps the dry-run off the Dockerfile image.
 * The deploy command still builds that image when it uploads.
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync, rmSync, statSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const testedDir = join(repoRoot, '.wrangler/tested');
const deployCheckDir = join(repoRoot, '.wrangler/deploy-check');
const testedBundle = join(testedDir, 'index.js');
const fixtureRoot = join(repoRoot, 'tests/fixtures/deploy-packaging');

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

function moduleFiles(dir) {
	const names = [];
	function walk(current) {
		for (const name of readdirSync(current)) {
			if (current === dir && name === 'README.md') continue;
			const path = join(current, name);
			if (statSync(path).isDirectory()) {
				walk(path);
				continue;
			}
			names.push(relative(dir, path).split(sep).join('/'));
		}
	}
	walk(dir);
	return names.sort();
}

function compareDeployModules(testedDirPath, deployDirPath) {
	const testedNames = moduleFiles(testedDirPath);
	const deployNames = moduleFiles(deployDirPath);
	const testedHash = existsSync(join(testedDirPath, 'index.js')) ? sha256(join(testedDirPath, 'index.js')) : '';
	const extra = deployNames.filter((name) => !testedNames.includes(name));
	const missing = testedNames.filter((name) => !deployNames.includes(name));
	if (extra.length || missing.length) {
		return {
			ok: false,
			testedHash,
			reason: `deploy modules [${deployNames.join(', ')}] do not match tested modules [${testedNames.join(', ')}]`,
		};
	}
	for (const name of testedNames) {
		const testedFile = sha256(join(testedDirPath, name));
		const deployFile = sha256(join(deployDirPath, name));
		if (deployFile !== testedFile) {
			return {
				ok: false,
				testedHash,
				reason: `${name} sha256 ${deployFile} does not match tested ${testedFile}`,
			};
		}
	}
	return { ok: true, testedHash };
}

function assertPlantedMismatchTrips() {
	const mismatchTested = join(fixtureRoot, 'planted-mismatch/tested');
	const mismatchDeploy = join(fixtureRoot, 'planted-mismatch/deploy-check');
	const same = compareDeployModules(mismatchTested, mismatchTested);
	if (!same.ok) fail(`checker rejected a bundle compared with itself: ${same.reason}`);
	const mismatch = compareDeployModules(mismatchTested, mismatchDeploy);
	if (mismatch.ok) fail('planted deploy-packaging mismatch did not trip');
	const extra = compareDeployModules(
		join(fixtureRoot, 'planted-extra/tested'),
		join(fixtureRoot, 'planted-extra/deploy-check'),
	);
	if (extra.ok) fail('planted extra deploy file did not trip');
	console.log('planted deploy-packaging mismatch tripped');
}

assertPlantedMismatchTrips();

const deployDate = compatibilityDate(join(repoRoot, 'wrangler.toml'));
const bundleDate = compatibilityDate(join(repoRoot, 'wrangler.bundle.toml'));
if (deployDate !== bundleDate) {
	fail(`compatibility_date ${bundleDate} in wrangler.bundle.toml does not match ${deployDate} in wrangler.toml`);
}

if (!existsSync(join(repoRoot, 'frontend/build'))) {
	fail('frontend/build is missing. Build the frontend before the Worker bundle.');
}

rmSync(testedDir, { recursive: true, force: true });
rmSync(deployCheckDir, { recursive: true, force: true });

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
	'--env=',
	'--dry-run',
	'--outdir', '.wrangler/deploy-check',
	'--containers-rollout=none',
], repoRoot);

const compared = compareDeployModules(testedDir, deployCheckDir);
if (!compared.ok) fail(compared.reason);
if (compared.testedHash !== testedHash) fail('tested bundle changed during the deploy packaging check');
