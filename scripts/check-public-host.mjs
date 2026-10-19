#!/usr/bin/env node
/**
 * Fail when a built site, worker, Python source, or public doc names
 * truerankings.com or workers.dev.
 *
 * Allowlist: this guard's fixtures (tests/fixtures/public-host) and dummy
 * hosts such as example.test. Signature canon (PURPOSE.md, IDENTITY.md,
 * MISSION.md) is not a public doc and is not scanned.
 *
 * Usage:
 *   node scripts/check-public-host.mjs --self-test
 *   node scripts/check-public-host.mjs frontend/build worker/src --python --public-docs
 *   node scripts/check-public-host.mjs --assert-set https://example.test frontend/build
 */
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(scriptDir, '..');
const fixtureRoot = join(repoRoot, 'tests', 'fixtures', 'public-host');
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
	'.ts',
	'.py',
	'.md',
]);
const SKIP_DIRS = new Set([
	'node_modules',
	'.git',
	'venv',
	'.venv',
	'__pycache__',
	'.cache',
	'frontend',
	'design',
	'.cursor',
]);
const SECRET_SKIP_DIRS = new Set([
	'node_modules',
	'.git',
	'venv',
	'.venv',
	'__pycache__',
	'.cache',
	'build',
	'.svelte-kit',
	'design',
	'.cursor',
]);
const SECRET_EXT = new Set([
	...TEXT_EXT,
	'.toml',
	'.yml',
	'.yaml',
	'.env',
	'.example',
]);
const PUBLIC_DOCS = [
	'README.md',
	'PRODUCT.md',
	'DESIGN.md',
	'TECH_STACK.md',
	'ALGORITHM_BREAKDOWN.md',
	'docs',
];
const RULES = [
	{ name: 'truerankings.com', re: /truerankings\.com/i },
	{ name: 'workers.dev', re: /workers\.dev/i },
];
/**
 * Reviewed false positives. Each entry is one file and one rule.
 * A different file, or a different rule in the same file, still fails.
 */
const COUNTER_LIST = ['PUBLIC', 'COUNTER_KEYS'].join('_');
const REVIEWED_ALLOWLIST = [
	{
		file: 'worker/src/caps.ts',
		rule: 'workers.dev',
		reason: 'preview-host suffix check, not a published URL',
	},
	{
		file: 'worker/src/caps.ts',
		token: COUNTER_LIST,
		reason: 'counter fields stripped from public JSON, not a credential',
	},
];
const DUMMY_HOST = /https?:\/\/(?:[a-z0-9-]+\.)*example\.test\b/gi;
const SECRET_PUBLIC = /PUBLIC_[A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)/;

export function findForbiddenHosts(root, { honorAllowlist = true, extensions = null } = {}) {
	const hits = [];
	function consider(path) {
		if (honorAllowlist && isAllowlisted(path)) return;
		const dot = path.lastIndexOf('.');
		const ext = dot === -1 ? '' : path.slice(dot).toLowerCase();
		if (extensions && !extensions.has(ext)) return;
		if (!extensions && ext && !TEXT_EXT.has(ext)) return;
		const text = readFileSync(path);
		if (text.includes(0)) return;
		const source = text.toString('utf8').replace(DUMMY_HOST, '');
		for (const rule of RULES) {
			rule.re.lastIndex = 0;
			if (rule.re.test(source) && !isReviewed(path, rule.name)) hits.push({ path, host: rule.name });
		}
	}
	function walk(dir) {
		for (const name of readdirSync(dir)) {
			const path = join(dir, name);
			const info = statSync(path);
			if (info.isDirectory()) {
				if (SKIP_DIRS.has(name)) continue;
				if (honorAllowlist && isAllowlisted(path)) continue;
				walk(path);
				continue;
			}
			consider(path);
		}
	}
	const info = statSync(root);
	if (info.isDirectory()) walk(root);
	else consider(root);
	return hits;
}

function isAllowlisted(path) {
	const rel = relative(fixtureRoot, path);
	return rel === '' || (!rel.startsWith('..') && !rel.startsWith(`..${sep}`));
}

function repoRel(path) {
	return relative(repoRoot, path).split(sep).join('/');
}

export function isReviewed(path, rule) {
	const rel = path.includes(sep) || path.includes('/') ? repoRel(path) : path;
	return REVIEWED_ALLOWLIST.some((entry) => entry.file === rel && entry.rule === rule);
}

function reviewedSecretTokens(path) {
	const rel = repoRel(path);
	return new Set(
		REVIEWED_ALLOWLIST
			.filter((entry) => entry.file === rel && entry.token)
			.map((entry) => entry.token),
	);
}

export function unexpectedSecretNames(path, source) {
	const allowed = reviewedSecretTokens(path);
	const hits = [];
	for (const match of source.matchAll(/PUBLIC_[A-Z0-9_]+/g)) {
		SECRET_PUBLIC.lastIndex = 0;
		if (!SECRET_PUBLIC.test(match[0])) continue;
		if (!allowed.has(match[0])) hits.push(match[0]);
	}
	return hits;
}

function findSecretPublicNames(root) {
	const hits = [];
	function walk(dir) {
		for (const name of readdirSync(dir)) {
			const path = join(dir, name);
			const info = statSync(path);
			if (info.isDirectory()) {
				if (SECRET_SKIP_DIRS.has(name)) continue;
				walk(path);
				continue;
			}
			const dot = name.lastIndexOf('.');
			const ext = dot === -1 ? '' : name.slice(dot).toLowerCase();
			if (ext && !SECRET_EXT.has(ext) && name !== '.env.example') continue;
			const text = readFileSync(path);
			if (text.includes(0)) continue;
			if (unexpectedSecretNames(path, text.toString('utf8')).length) hits.push(path);
		}
	}
	walk(root);
	return hits;
}

function scanPythonSources() {
	return findForbiddenHosts(repoRoot, { extensions: new Set(['.py']) });
}

function scanPublicDocs() {
	const hits = [];
	for (const entry of PUBLIC_DOCS) {
		hits.push(...findForbiddenHosts(join(repoRoot, entry)));
	}
	return hits;
}

export function assertSetSite(dir, origin) {
	const normalized = origin.replace(/\/$/, '');
	const errors = [];
	const htmlHits = { canonical: false, ogUrl: false };
	function walk(current) {
		for (const name of readdirSync(current)) {
			const path = join(current, name);
			const info = statSync(path);
			if (info.isDirectory()) {
				walk(path);
				continue;
			}
			if (!name.endsWith('.html')) continue;
			const html = readFileSync(path, 'utf8');
			if (html.includes(`rel="canonical" href="${normalized}/`) || html.includes(`rel="canonical" href="${normalized}"`)) {
				htmlHits.canonical = true;
			}
			if (html.includes(`property="og:url" content="${normalized}/`) || html.includes(`property="og:url" content="${normalized}"`)) {
				htmlHits.ogUrl = true;
			}
		}
	}
	walk(dir);
	if (!htmlHits.canonical) errors.push(`no absolute canonical for ${normalized}`);
	if (!htmlHits.ogUrl) errors.push(`no og:url for ${normalized}`);
	const sitemapPath = join(dir, 'sitemap.xml');
	let sitemap = '';
	try {
		sitemap = readFileSync(sitemapPath, 'utf8');
	} catch {
		errors.push('sitemap.xml was not generated');
	}
	if (sitemap && !sitemap.includes(`${normalized}/`)) errors.push('sitemap.xml omitted the set host');
	let robots = '';
	try {
		robots = readFileSync(join(dir, 'robots.txt'), 'utf8');
	} catch {
		errors.push('robots.txt was not generated');
	}
	if (robots && !robots.includes(`Sitemap: ${normalized}/sitemap.xml`)) {
		errors.push('robots.txt Sitemap line omitted the set host');
	}
	const forbidden = findForbiddenHosts(dir);
	if (forbidden.length) errors.push(`forbidden host in set build: ${JSON.stringify(forbidden)}`);
	return errors;
}

function fail(message) {
	console.error(message);
	process.exit(1);
}

function selfTest() {
	const fixtures = fixtureRoot;
	const clean = findForbiddenHosts(join(fixtures, 'clean'), { honorAllowlist: false });
	if (clean.length) fail(`clean fixture must pass, found ${JSON.stringify(clean)}`);
	const planted = findForbiddenHosts(join(fixtures, 'planted'), { honorAllowlist: false });
	const names = new Set(planted.map((hit) => hit.host));
	if (!names.has('truerankings.com') || !names.has('workers.dev')) {
		fail(`planted fixture must fail for both hosts, found ${JSON.stringify(planted)}`);
	}
	for (const file of ['worker.ts', 'worker.js', 'source.py', 'public.md']) {
		const hits = findForbiddenHosts(join(fixtures, 'planted', file), { honorAllowlist: false });
		if (!hits.length) fail(`planted ${file} must trip the guard`);
	}
	const allowed = findForbiddenHosts(fixtures);
	if (allowed.length) fail(`allowlisted fixtures must not trip, found ${JSON.stringify(allowed)}`);
	const secrets = findSecretPublicNames(repoRoot);
	if (secrets.length) fail(`secret-bearing PUBLIC_* name: ${secrets.join(', ')}`);
	const capsPath = join(repoRoot, 'worker/src/caps.ts');
	if (!isReviewed(capsPath, 'workers.dev')) fail('caps.ts workers.dev exception missing');
	if (isReviewed(capsPath, 'truerankings.com')) fail('caps.ts exception must not cover other hosts');
	if (isReviewed(join(repoRoot, 'worker/src/index.ts'), 'workers.dev')) {
		fail('workers.dev exception must stay on caps.ts');
	}
	const capsHits = findForbiddenHosts(capsPath);
	if (capsHits.length) fail(`reviewed caps.ts host exception leaked: ${JSON.stringify(capsHits)}`);
	const capsSource = readFileSync(capsPath, 'utf8');
	if (unexpectedSecretNames(capsPath, capsSource).length) {
		fail(`${COUNTER_LIST} must be the only reviewed secret token in caps.ts`);
	}
	const plantedKey = ['PUBLIC', 'API_KEY'].join('_');
	if (!unexpectedSecretNames(capsPath, `${capsSource}\nconst leak = "${plantedKey}";\n`).length) {
		fail('a real public credential name in caps.ts must still trip');
	}
	if (!unexpectedSecretNames(join(repoRoot, 'worker/src/index.ts'), `const name = "${COUNTER_LIST}";\n`).length) {
		fail(`${COUNTER_LIST} is reviewed only in caps.ts`);
	}
	const narrowDir = mkdtempSync(join(tmpdir(), 'public-host-narrow-'));
	try {
		writeFileSync(join(narrowDir, 'other.ts'), 'const host = "preview.workers.dev";\n');
		const otherHits = findForbiddenHosts(narrowDir);
		if (!otherHits.some((hit) => hit.host === 'workers.dev')) {
			fail('workers.dev outside worker/src/caps.ts must trip');
		}
	} finally {
		rmSync(narrowDir, { recursive: true, force: true });
	}
	const secretDir = mkdtempSync(join(tmpdir(), 'public-secret-'));
	try {
		const secretName = `PUBLIC_${'API_KEY'}`;
		writeFileSync(join(secretDir, 'leak.ts'), `export const key = "${secretName}";\n`);
		const leaked = findSecretPublicNames(secretDir);
		if (!leaked.length) fail('a PUBLIC_* key, token, or password must trip the secret scan');
	} finally {
		rmSync(secretDir, { recursive: true, force: true });
	}

	const unsetDir = mkdtempSync(join(tmpdir(), 'public-files-unset-'));
	const setDir = mkdtempSync(join(tmpdir(), 'public-files-set-'));
	const htmlDir = mkdtempSync(join(tmpdir(), 'public-html-set-'));
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
		const lede = 'Weekly college football rankings. How good they actually are. The order you check before you argue — not a poll, not a committee, not the narrative. Rankings, methodology, and weekly JSON stay free and simultaneous.';
		const closer = 'See /llms-full.txt for positioning.';
		const rating = "A computer power rating, like SP+ and FPI, with an open formula and a 'why here' for every team.";
		const order = 'The order you check before you argue';
		const llmsLines = llms.trimEnd().split('\n');
		if (!llmsLines.includes(`> ${lede}`)) fail('llms.txt lede is not the locked sentence');
		if (llmsLines[llmsLines.length - 1] !== closer || llms.includes('Rankings are never paywalled')) {
			fail('llms.txt closer is not the locked sentence');
		}
		if (llms.split(order).length - 1 !== 1) {
			fail('order line is repeated outside the llms.txt lede');
		}
		const full = readFileSync(join(unsetDir, 'llms-full.txt'), 'utf8');
		if (!full.includes(rating) || /Comparable category:/i.test(full)) {
			fail('llms-full.txt is missing the locked power-rating line');
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

		writeFileSync(join(htmlDir, 'week.html'), [
			'<link rel="canonical" href="https://example.test/2024/week/15" />',
			'<meta property="og:url" content="https://example.test/2024/week/15" />',
		].join('\n'));
		writeFileSync(join(htmlDir, 'sitemap.xml'), '<loc>https://example.test/2024/week/15</loc>');
		writeFileSync(join(htmlDir, 'robots.txt'), 'Sitemap: https://example.test/sitemap.xml\n');
		const setErrors = assertSetSite(htmlDir, 'https://example.test');
		if (setErrors.length) fail(`assert-set rejected a good build: ${setErrors.join('; ')}`);
		writeFileSync(join(htmlDir, 'week.html'), '<link rel="canonical" href="/2024/week/15" />');
		const missing = assertSetSite(htmlDir, 'https://example.test');
		if (!missing.some((error) => error.includes('canonical')) || !missing.some((error) => error.includes('og:url'))) {
			fail('assert-set must reject a path-only canonical and a missing og:url');
		}
	} finally {
		rmSync(unsetDir, { recursive: true, force: true });
		rmSync(setDir, { recursive: true, force: true });
		rmSync(htmlDir, { recursive: true, force: true });
	}
	console.log('public host self-test ok');
}

const args = process.argv.slice(2);
const self = args.includes('--self-test');
const python = args.includes('--python');
const publicDocs = args.includes('--public-docs');
const setFlag = args.indexOf('--assert-set');
const setOrigin = setFlag === -1 ? '' : args[setFlag + 1];
const targets = args.filter((arg, index) => {
	if (arg.startsWith('--')) return false;
	if (setFlag !== -1 && index === setFlag + 1) return false;
	return true;
});

if (self) selfTest();
if (setFlag !== -1) {
	if (!setOrigin || !targets.length) fail('--assert-set needs an origin and a build directory');
	const errors = assertSetSite(targets[0], setOrigin);
	if (errors.length) fail(errors.join('\n'));
	console.log(`set site ${setOrigin} is on the canonical, og:url, sitemap, and robots line`);
}
const scanTargets = setFlag === -1 ? targets : targets.slice(1);
const hits = [
	...scanTargets.flatMap((target) => findForbiddenHosts(target)),
	...(python ? scanPythonSources() : []),
	...(publicDocs ? scanPublicDocs() : []),
];
if (!self && !setFlag && !targets.length && !python && !publicDocs) {
	fail('pass a directory to scan, --python, --public-docs, or --self-test');
}
if (hits.length) {
	for (const hit of hits) console.error(`${hit.host} in ${hit.path}`);
	process.exit(1);
}
if (scanTargets.length || python || publicDocs) {
	console.log('no forbidden public host in the scanned sources');
}
