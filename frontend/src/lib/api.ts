import type { Team, Conference, FilterState, RankingsResponse } from '$lib/types';

function parseWinPct(value: unknown): number {
	if (typeof value === 'number') return value;
	if (typeof value === 'string' && value.includes('-')) {
		const [wins, losses] = value.split('-').map(Number);
		const total = wins + losses;
		return total > 0 ? wins / total : 0;
	}
	return 0;
}

function resolveApiBase(): string {
	// Dev: Vite proxies /api → localhost:5001 (see vite.config.ts)
	if (import.meta.env.DEV) {
		return '/api';
	}
	// Prod override only if explicitly set (e.g. cross-origin API during migration)
	if (import.meta.env.VITE_API_URL) {
		const envUrl = import.meta.env.VITE_API_URL;
		return envUrl.startsWith('http') ? envUrl : `https://${envUrl}`;
	}
	// Default: same-origin /api proxy via Cloudflare Pages _redirects
	return '/api';
}

export const API_BASE = resolveApiBase();

export function mapTeamFromApi(t: Record<string, unknown>): Team {
	return {
		team_name: (t.team_name || t.team || '') as string,
		conference: (t.conference || '') as string,
		conference_type: (t.conference_type || '') as string,
		final_ranking_score: (t.final_ranking_score || t.score || 0) as number,
		team_quality_score: (t.team_quality_score || 0) as number,
		record_score: (t.record_score || 0) as number,
		conference_quality_score: (t.conference_quality_score || 0) as number,
		sos: (t.sos ?? null) as number | null,
		sov: (t.sov ?? null) as number | null,
		sos_rank: (t.sos_rank ?? undefined) as number | undefined,
		sov_rank: (t.sov_rank ?? undefined) as number | undefined,
		logo: (t.logo ?? null) as string | null,
		logo_dark: (t.logo_dark ?? null) as string | null,
		color: (t.color ?? null) as string | null,
		alt_color: (t.alt_color ?? null) as string | null,
		records: {
			total_wins: (t.records as Record<string, number>)?.total_wins ?? 0,
			total_losses: (t.records as Record<string, number>)?.total_losses ?? 0,
			conf_wins: (t.records as Record<string, number>)?.conf_wins ?? 0,
			conf_losses: (t.records as Record<string, number>)?.conf_losses ?? 0,
			power_wins: (t.records as Record<string, number>)?.power_wins ?? 0,
			power_losses: (t.records as Record<string, number>)?.power_losses ?? 0,
			group_five_wins: (t.records as Record<string, number>)?.group_five_wins ?? 0,
			group_five_losses: (t.records as Record<string, number>)?.group_five_losses ?? 0,
		},
		quality_wins: (t.quality_wins ?? 0) as number,
		quality_losses: (t.quality_losses ?? 0) as number,
		bad_losses: (t.bad_losses ?? 0) as number,
		bad_wins: (t.bad_wins ?? 0) as number,
		top_10_wins: (t.top_10_wins ?? 0) as number,
		top_25_wins: (t.top_25_wins ?? 0) as number,
		cross_tier_wins: (t.cross_tier_wins ?? 0) as number,
		h2h_bonus: (t.h2h_bonus ?? 0) as number,
		quality_loss_bonus: (t.quality_loss_bonus ?? 0) as number,
		bad_loss_penalty: (t.bad_loss_penalty ?? 0) as number,
		quality_win_bonus: (t.quality_win_bonus ?? 0) as number,
		bad_win_penalty: (t.bad_win_penalty ?? 0) as number,
		wins_details: (t.wins_details || []) as Team['wins_details'],
		losses_details: (t.losses_details || []) as Team['losses_details'],
	};
}

export function mapConferenceFromApi(c: Record<string, unknown>): Conference {
	return {
		conference: (c.conference_name || c.conference || '') as string,
		conference_type: (c.conference_type || '') as string,
		avg_ranking: (c.average_team_quality || c.avg_ranking || 0) as number,
		team_count: (c.number_of_teams || c.team_count || 0) as number,
		ranked_teams: (c.ranked_teams ?? 0) as number,
		power_win_pct: parseWinPct(c.record_vs_p4 || c.power_win_pct),
		g5_win_pct: parseWinPct(c.record_vs_g5 || c.g5_win_pct),
		fcs_wins: (c.fcs_wins ?? undefined) as number | undefined,
		fcs_losses: (c.fcs_losses ?? undefined) as number | undefined,
	};
}

export function isLikelyArchivedWeek(year: number, week: number, now = new Date()): boolean {
	const month = now.getMonth() + 1;
	const seasonYear = month < 8 ? now.getFullYear() - 1 : now.getFullYear();
	if (year < seasonYear) return true;
	if (year > seasonYear) return false;
	if (month < 8) return true;
	const seasonStart = new Date(seasonYear, 7, 24);
	const days = Math.floor((now.getTime() - seasonStart.getTime()) / (1000 * 60 * 60 * 24));
	const currentWeek = Math.min(Math.max(Math.floor(days / 7) + 1, 1), 16);
	return week < currentWeek;
}

async function fetchStaticRankings(year: number, week: number): Promise<RankingsResponse | null> {
	try {
		const response = await fetch(`/rankings/${year}/week-${week}.json`, {
			signal: AbortSignal.timeout(3000),
		});
		if (!response.ok) return null;
		const data = await response.json();
		return {
			teams: (data.team_rankings || data.teams || []).map(mapTeamFromApi),
			conferences: (data.conference_rankings || data.conferences || []).map(mapConferenceFromApi),
			year: data.year || year,
			week: data.week || week,
			generated_at: data.generated_at || new Date().toISOString(),
		};
	} catch {
		return null;
	}
}

export async function fetchRankingsFromApi(
	year: number,
	week: number,
	view: FilterState['view'] = 'fbs'
): Promise<RankingsResponse> {
	// Prefer static JSON for archived weeks when published to Pages/static
	if (isLikelyArchivedWeek(year, week)) {
		const staticData = await fetchStaticRankings(year, week);
		if (staticData) return staticData;
	}

	const allDivisions = view === 'fcs' ? 'true' : 'false';
	const url = `${API_BASE}/rankings?year=${year}&week=${week}&all_divisions=${allDivisions}`;
	const response = await fetch(url);
	if (!response.ok) {
		const error = await response.json().catch(() => ({ error: 'Unknown error' }));
		throw new Error((error as { error?: string; message?: string }).error ||
			(error as { message?: string }).message ||
			`HTTP ${response.status}`);
	}
	const data = await response.json();
	return {
		teams: (data.team_rankings || data.teams || []).map(mapTeamFromApi),
		conferences: (data.conference_rankings || data.conferences || []).map(mapConferenceFromApi),
		year: data.year || year,
		week: data.week || week,
		generated_at: data.generated_at || new Date().toISOString(),
	};
}

export async function fetchAvailableWeeks(year: number): Promise<number[]> {
	try {
		const response = await fetch(`${API_BASE}/weeks?year=${year}`);
		if (!response.ok) {
			return Array.from({ length: 15 }, (_, i) => i + 1);
		}
		const data = await response.json();
		return data.weeks || Array.from({ length: 15 }, (_, i) => i + 1);
	} catch {
		return Array.from({ length: 15 }, (_, i) => i + 1);
	}
}

export async function checkApiHealth(): Promise<boolean> {
	try {
		const response = await fetch(`${API_BASE}/`, {
			method: 'GET',
			signal: AbortSignal.timeout(5000),
		});
		return response.ok;
	} catch {
		return false;
	}
}

export async function fetchTeamDetail(
	teamName: string,
	year: number,
	week: number
): Promise<
	Partial<Team> & {
		wins_details?: Team['wins_details'];
		losses_details?: Team['losses_details'];
		path_to_climb?: Team['path_to_climb'];
		comparisons_ahead?: Team['comparisons_ahead'];
		comparisons_behind?: Team['comparisons_behind'];
	}
> {
	const url = `${API_BASE}/rankings/team/${encodeURIComponent(teamName)}?year=${year}&week=${week}`;
	const response = await fetch(url);
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error((error as { error?: string }).error || `HTTP ${response.status}`);
	}
	const data = await response.json();
	const t = data.team || {};
	return {
		team_name: t.name || teamName,
		wins_details: data.wins_details || [],
		losses_details: data.losses_details || [],
		quality_wins: data.quality_wins,
		quality_losses: data.quality_losses,
		bad_losses: data.bad_losses,
		top_10_wins: data.top_10_wins,
		top_25_wins: data.top_25_wins,
		path_to_climb: data.path_to_climb,
		comparisons_ahead: data.comparisons_ahead || [],
		comparisons_behind: data.comparisons_behind || [],
	};
}

export async function fetchWeekStory(
	year: number,
	week: number
): Promise<{ headline?: string; paragraphs?: string[]; facts?: Record<string, unknown> } | null> {
	try {
		const response = await fetch(`/rankings/${year}/week-${week}.story.json`, {
			signal: AbortSignal.timeout(3000),
		});
		if (!response.ok) return null;
		return response.json();
	} catch {
		return null;
	}
}

export async function fetchWhyBlurb(
	year: number,
	week: number,
	teamName: string
): Promise<string | null> {
	try {
		const response = await fetch(`/rankings/${year}/week-${week}.why.json`, {
			signal: AbortSignal.timeout(3000),
		});
		if (!response.ok) return null;
		const data = await response.json();
		const blurbs = data.blurbs || data;
		return blurbs[teamName] || null;
	} catch {
		return null;
	}
}

export async function explainRanking(
	teamName: string,
	year: number,
	week: number,
	question?: string
): Promise<{ explanation: string; context: Record<string, unknown> }> {
	const response = await fetch(`${API_BASE}/agent/explain`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ team_name: teamName, year, week, question }),
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error((error as { error?: string }).error || `HTTP ${response.status}`);
	}
	return response.json();
}
