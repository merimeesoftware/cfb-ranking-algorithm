#!/usr/bin/env node
/**
 * Fail when a built site or a planted fixture names truerankings.com or workers.dev.
 * Usage:
 *   node scripts/check-public-host.mjs --self-test
 *   node scripts/check-public-host.mjs frontend/build
 */
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(scriptDir, '..');
const TEXT_EXT = new Set([
	'.html',
	'.js',
	'.css',
	'.txt',
	'.xml',
	'.json',
	'.svg',
	'.map',
	'.webmanifest',
	'.mjs',
	'.cjs',
]);

const RULES = [
	{ name: 'truerankings.com', re: /truerankings\.com/i },
	{ name: 'workers.dev', re: /workers\.dev/i },
];

export function findForbiddenHosts(root) {
	const hits = [];
	function walk(dir) {
		for (const name of readdirSync(dir)) {
			const path = join(dir, name);
			const info = statSync(path);
			if (info.isDirectory()) {
				if (name === 'node_modules' || name === '.git') continue;
				walk(path);
				continue;
			}
			const dot = name.lastIndexOf('.');
			const ext = dot === -1 ? '' : name.slice(dot).toLowerCase();
			if (ext && !TEXT_EXT.has(ext)) continue;
			const text = readFileSync(path);
			if (text.includes(0)) continue;
			const source = text.toString('utf8');
			for (const rule of RULES) {
				if (rule.re.test(source)) hits.push({ path, host: rule.name });
			}
		}
	}
	walk(root);
	return hits;
}

function fail(message) {
	console.error(message);
	process.exit(1);
}

function selfTest() {
	const fixtures = join(repoRoot, 'tests', 'fixtures', 'public-host');
	const clean = findForbiddenHosts(join(fixtures, 'clean'));
	if (clean.length) fail(`clean fixture must pass, found ${JSON.stringify(clean)}`);
	const planted = findForbiddenHosts(join(fixtures, 'planted'));
	const names = new Set(planted.map((hit) => hit.host));
	if (!names.has('truerankings.com') || !names.has('workers.dev')) {
		fail(`planted fixture must fail for both hosts, found ${JSON.stringify(planted)}`);
	}

	const unsetDir = mkdtempSync(join(tmpdir(), 'public-files-unset-'));
	const setDir = mkdtempSync(join(tmpdir(), 'public-files-set-'));
	try {
		const unset = spawnSync(
			process.execPath,
			[join(scriptDir, 'generate-public-files.mjs'), '--out', unsetDir],
			{ env: { ...process.env, PUBLIC_SITE_URL: '' }, encoding: 'utf8' }
		);
		if (unset.status !== 0) fail(unset.stderr || unset.stdout || 'unset generate failed');
		const unsetHits = findForbiddenHosts(unsetDir);
		if (unsetHits.length) fail(`unset generate named a host: ${JSON.stringify(unsetHits)}`);
		const unsetNames = readdirSync(unsetDir);
		if (unsetNames.includes('sitemap.xml')) fail('unset generate wrote sitemap.xml');
		const robots = readFileSync(join(unsetDir, 'robots.txt'), 'utf8');
		if (/^Sitemap:/m.test(robots)) fail('unset robots.txt includes a Sitemap line');
		const llms = readFileSync(join(unsetDir, 'llms.txt'), 'utf8');
		if (/predictive/i.test(llms) || /market/i.test(llms)) {
			fail('llms.txt still has prediction or market framing');
		}

		const set = spawnSync(
			process.execPath,
			[join(scriptDir, 'generate-public-files.mjs'), '--out', setDir],
			{ env: { ...process.env, PUBLIC_SITE_URL: 'https://example.com/' }, encoding: 'utf8' }
		);
		if (set.status !== 0) fail(set.stderr || set.stdout || 'set generate failed');
		const sitemap = readFileSync(join(setDir, 'sitemap.xml'), 'utf8');
		if (!sitemap.includes('https://example.com/')) fail('sitemap did not use PUBLIC_SITE_URL');
		const setHits = findForbiddenHosts(setDir);
		if (setHits.length) fail(`set generate named a forbidden host: ${JSON.stringify(setHits)}`);
		const setRobots = readFileSync(join(setDir, 'robots.txt'), 'utf8');
		if (!setRobots.includes('Sitemap: https://example.com/sitemap.xml')) {
			fail('robots Sitemap line did not use PUBLIC_SITE_URL');
		}
	} finally {
		rmSync(unsetDir, { recursive: true, force: true });
		rmSync(setDir, { recursive: true, force: true });
	}
	console.log('public host self-test ok');
}

const target = process.argv.slice(2).filter((arg) => arg !== '--self-test');
if (process.argv.includes('--self-test')) selfTest();
if (!target.length) {
	if (!process.argv.includes('--self-test')) fail('pass a directory to scan, or --self-test');
	process.exit(0);
}
const hits = findForbiddenHosts(target[0]);
if (hits.length) {
	for (const hit of hits) console.error(`${hit.host} in ${hit.path}`);
	process.exit(1);
}
console.log(`no forbidden public host in ${target[0]}`);
