#!/usr/bin/env node
/**
 * Generate frontend/static/sitemap.xml from rankings manifest (+ team pages for latest week).
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const staticRoot = join(root, 'frontend', 'static');
const manifestPath = join(staticRoot, 'rankings', 'manifest.json');
const site = (process.env.PUBLIC_SITE_URL || 'https://truerankings.com').replace(/\/$/, '');

function slug(name) {
	return name
		.toLowerCase()
		.replace(/&/g, 'and')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

function escapeXml(s) {
	return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

const urls = [
	{ loc: `${site}/`, priority: '1.0', changefreq: 'daily' },
	{ loc: `${site}/methodology`, priority: '0.6', changefreq: 'monthly' },
	{ loc: `${site}/llms.txt`, priority: '0.3', changefreq: 'monthly' },
];

if (existsSync(manifestPath)) {
	const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
	const years = Object.keys(manifest.years || {}).map(Number).sort((a, b) => a - b);
	let latest = null;
	for (const year of years) {
		const weeks = [...manifest.years[String(year)]].sort((a, b) => a - b);
		for (const week of weeks) {
			urls.push({
				loc: `${site}/${year}/week/${week}`,
				priority: '0.9',
				changefreq: 'weekly',
			});
			latest = { year, week };
		}
	}
	if (latest) {
		const weekPath = join(
			staticRoot,
			'rankings',
			String(latest.year),
			`week-${latest.week}.json`
		);
		if (existsSync(weekPath)) {
			const data = JSON.parse(readFileSync(weekPath, 'utf-8'));
			const teams = data.team_rankings || data.teams || [];
			for (const t of teams.slice(0, 50)) {
				const name = t.team_name || t.team;
				if (!name) continue;
				urls.push({
					loc: `${site}/teams/${slug(name)}`,
					priority: '0.7',
					changefreq: 'weekly',
				});
			}
			// Sample Top-10 round-robin matchups for discoverability
			const top = teams.slice(0, 10);
			for (let i = 0; i < top.length; i++) {
				for (let j = i + 1; j < Math.min(top.length, i + 3); j++) {
					const a = top[i].team_name;
					const b = top[j].team_name;
					urls.push({
						loc: `${site}/games/${slug(a)}-vs-${slug(b)}`,
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
		(u) => `  <url>
    <loc>${escapeXml(u.loc)}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`
	)
	.join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</urlset>
`;

writeFileSync(join(staticRoot, 'sitemap.xml'), xml);
console.log(`Wrote sitemap.xml with ${urls.length} URLs → ${site}`);
