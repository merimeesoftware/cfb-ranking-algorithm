/** True Rankings public brand constants and helpers. */

export const BRAND_NAME = 'True Rankings';
export const BRAND_SHORT = 'TR';
export const RATING_NAME = 'TR+';
export const TAGLINE = 'How good they actually are.';
export const HANDLE = '@TrueCFB';
export const DROP_NAME = 'The Drop';

/** Canonical public origin. Override via PUBLIC_SITE_URL at build time when custom domain is live. */
export const SITE_ORIGIN =
	(typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.PUBLIC_SITE_URL) ||
	'https://truerankings.com';

export function teamSlug(name: string): string {
	return name
		.toLowerCase()
		.replace(/&/g, 'and')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

export function slugToTeamLookup(slug: string): string {
	return slug.replace(/-/g, ' ').toLowerCase();
}

export function findTeamBySlug<T extends { team_name: string }>(
	teams: T[],
	slug: string
): T | undefined {
	const needle = slug.toLowerCase();
	const exact = teams.find((t) => teamSlug(t.team_name) === needle);
	if (exact) return exact;
	const loose = slugToTeamLookup(slug);
	return teams.find((t) => t.team_name.toLowerCase() === loose);
}

export function matchupSlug(teamA: string, teamB: string): string {
	return `${teamSlug(teamA)}-vs-${teamSlug(teamB)}`;
}

export function parseMatchupSlug(slug: string): { a: string; b: string } | null {
	const parts = slug.toLowerCase().split('-vs-');
	if (parts.length !== 2 || !parts[0] || !parts[1]) return null;
	return { a: parts[0], b: parts[1] };
}

export function weekPath(year: number, week: number): string {
	return `/${year}/week/${week}`;
}

export function teamPath(name: string, year?: number, week?: number): string {
	const base = `/teams/${teamSlug(name)}`;
	if (year != null && week != null) {
		return `${base}?year=${year}&week=${week}`;
	}
	return base;
}

export function gamePath(teamA: string, teamB: string, year?: number, week?: number): string {
	const base = `/games/${matchupSlug(teamA, teamB)}`;
	if (year != null && week != null) {
		return `${base}?year=${year}&week=${week}`;
	}
	return base;
}

export function citationText(year: number, week: number, url?: string): string {
	const link = url || `${SITE_ORIGIN}${weekPath(year, week)}`;
	return `${BRAND_NAME}, ${year} Week ${week}, ${link}`;
}

export function pageTitle(parts: string[]): string {
	return [...parts, BRAND_NAME].join(' | ');
}

/**
 * Convert TR+ (FRS) differential into an implied point spread.
 * ~25 TR+ points ≈ 1 spread point (Elo-scale scores ~900–1900).
 */
export const TR_PLUS_PER_POINT = 25;

export function impliedSpread(favoriteTrPlus: number, underdogTrPlus: number): number {
	const raw = (favoriteTrPlus - underdogTrPlus) / TR_PLUS_PER_POINT;
	return Math.round(raw * 2) / 2; // nearest half-point
}

export function formatSpread(points: number, favoriteName: string): string {
	if (points === 0) return 'Pick\'em';
	return `${favoriteName} -${points.toFixed(1)}`;
}
