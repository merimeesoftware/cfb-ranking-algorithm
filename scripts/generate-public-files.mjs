#!/usr/bin/env node
/**
 * Write robots.txt, llms.txt, llms-full.txt, and (only when PUBLIC_SITE_URL
 * is set) sitemap.xml. No default host. Unset keeps same-origin paths and
 * skips sitemap.xml plus the robots Sitemap line.
 */
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(scriptDir, '..');
const rankingsRoot = join(repoRoot, 'frontend', 'static');

export function readSiteOrigin(raw = process.env.PUBLIC_SITE_URL) {
	if (typeof raw !== 'string') return '';
	const trimmed = raw.trim().replace(/\/$/, '');
	if (!trimmed) return '';
	if (!/^https?:\/\//i.test(trimmed)) {
		console.warn('PUBLIC_SITE_URL must be an absolute http(s) origin. Treating it as unset.');
		return '';
	}
	return trimmed;
}

function outputDir() {
	const flag = process.argv.indexOf('--out');
	if (flag !== -1 && process.argv[flag + 1]) return process.argv[flag + 1];
	return rankingsRoot;
}

function slug(name) {
	return name
		.toLowerCase()
		.replace(/&/g, 'and')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

function escapeXml(value) {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

function render(name, origin) {
	const raw = readFileSync(join(scriptDir, 'public-files', name), 'utf8');
	return raw.replaceAll('{ORIGIN}', origin);
}

function sitemapXml(origin) {
	const urls = [
		{ loc: `${origin}/`, priority: '1.0', changefreq: 'daily' },
		{ loc: `${origin}/methodology`, priority: '0.6', changefreq: 'monthly' },
		{ loc: `${origin}/llms.txt`, priority: '0.3', changefreq: 'monthly' },
	];
	const manifestPath = join(rankingsRoot, 'rankings', 'manifest.json');
	if (existsSync(manifestPath)) {
		const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
		const years = Object.keys(manifest.years || {})
			.map(Number)
			.sort((a, b) => a - b);
		let latest = null;
		for (const year of years) {
			const weeks = [...manifest.years[String(year)]].sort((a, b) => a - b);
			for (const week of weeks) {
				urls.push({
					loc: `${origin}/${year}/week/${week}`,
					priority: '0.9',
					changefreq: 'weekly',
				});
				latest = { year, week };
			}
		}
		if (latest) {
			const weekPath = join(
				rankingsRoot,
				'rankings',
				String(latest.year),
				`week-${latest.week}.json`
			);
			if (existsSync(weekPath)) {
				const data = JSON.parse(readFileSync(weekPath, 'utf8'));
				const teams = data.team_rankings || data.teams || [];
				for (const team of teams.slice(0, 50)) {
					const name = team.team_name || team.team;
					if (!name) continue;
					urls.push({
						loc: `${origin}/teams/${slug(name)}`,
						priority: '0.7',
						changefreq: 'weekly',
					});
				}
				const top = teams.slice(0, 10);
				for (let i = 0; i < top.length; i++) {
					for (let j = i + 1; j < Math.min(top.length, i + 3); j++) {
						urls.push({
							loc: `${origin}/games/${slug(top[i].team_name)}-vs-${slug(top[j].team_name)}`,
							priority: '0.5',
							changefreq: 'weekly',
						});
					}
				}
			}
		}
	}
	const today = new Date().toISOString().slice(0, 10);
	const body = urls
		.map(
			(url) => `  <url>
    <loc>${escapeXml(url.loc)}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${url.changefreq}</changefreq>
    <priority>${url.priority}</priority>
  </url>`
		)
		.join('\n');
	return {
		count: urls.length,
		xml: `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</urlset>
`,
	};
}

function robots(origin) {
	let text = readFileSync(join(scriptDir, 'public-files', 'robots.txt'), 'utf8');
	if (!text.endsWith('\n')) text += '\n';
	if (origin) text += `Sitemap: ${origin}/sitemap.xml\n`;
	return text;
}

function main() {
	const origin = readSiteOrigin();
	const out = outputDir();
	mkdirSync(out, { recursive: true });
	writeFileSync(join(out, 'robots.txt'), robots(origin));
	writeFileSync(join(out, 'llms.txt'), render('llms.txt', origin));
	writeFileSync(join(out, 'llms-full.txt'), render('llms-full.txt', origin));
	const sitemapPath = join(out, 'sitemap.xml');
	if (!origin) {
		if (existsSync(sitemapPath)) unlinkSync(sitemapPath);
		console.log('PUBLIC_SITE_URL unset. Wrote relative robots and llms files. Skipped sitemap.xml.');
		return;
	}
	const sitemap = sitemapXml(origin);
	writeFileSync(sitemapPath, sitemap.xml);
	console.log(`Wrote sitemap.xml with ${sitemap.count} URLs, plus robots and llms files.`);
}

main();
