import { writable, derived } from 'svelte/store';
import type { Team, Conference, FilterState } from '$lib/types';

// Helper function to parse win percentage from various formats
function parseWinPct(value: any): number {
	if (typeof value === 'number') return value;
	if (typeof value === 'string' && value.includes('-')) {
		const [wins, losses] = value.split('-').map(Number);
		const total = wins + losses;
		return total > 0 ? wins / total : 0;
	}
	return 0;
}

/**
 * Calculate the current CFB season and week based on today's date
 * CFB season typically starts late August / early September
 */
function getCurrentSeasonWeek(): { year: number; week: number } {
	const now = new Date();
	let year = now.getFullYear();
	const month = now.getMonth() + 1; // JavaScript months are 0-indexed
	
	// If we're in Jan-July, we're in the offseason of the previous year's season
	if (month < 8) {
		year = year - 1;
		// Return postseason/final week for completed seasons
		return { year, week: 15 };
	}
	
	// Season starts around August 24 (Week 0)
	const seasonStart = new Date(year, 7, 24); // August 24
	
	if (now < seasonStart) {
		// Before season starts, default to week 1
		return { year, week: 1 };
	}
	
	// Calculate weeks since season start
	const delta = now.getTime() - seasonStart.getTime();
	const daysSinceStart = Math.floor(delta / (1000 * 60 * 60 * 24));
	let weekNum = Math.floor(daysSinceStart / 7) + 1;
	
	// Cap at 15 (postseason)
	if (weekNum > 15) {
		weekNum = 15;
	}
	
	return { year, week: weekNum };
}

// Get current season/week
const currentSeasonWeek = getCurrentSeasonWeek();

// State stores
export const teams = writable<Team[]>([]);
export const conferences = writable<Conference[]>([]);
export const loading = writable<boolean>(false);
export const error = writable<string | null>(null);

// Filter state - defaults to current season and week
export const filterState = writable<FilterState>({
	year: currentSeasonWeek.year,
	week: currentSeasonWeek.week,
	conferenceFilter: null,
	searchQuery: ''
});

// Available years (last 5 years)
export const availableYears = writable<number[]>(
	Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i)
);

// Max week for current season
export const maxWeek = writable<number>(15);

// Derived store for filtered teams
export const filteredTeams = derived(
	[teams, filterState],
	([$teams, $filterState]) => {
		let result = [...$teams];

		// Filter by conference
		if ($filterState.conferenceFilter) {
			result = result.filter(t => t.conference === $filterState.conferenceFilter);
		}

		// Filter by search query
		if ($filterState.searchQuery) {
			const query = $filterState.searchQuery.toLowerCase();
			result = result.filter(t => 
				t.team_name.toLowerCase().includes(query) ||
				t.conference.toLowerCase().includes(query)
			);
		}

		return result;
	}
);

// API base URL - uses relative path for same-origin requests
const API_BASE = '/api';

// Custom weights interface
interface AlgorithmWeights {
	teamQuality: number;
	recordScore: number;
	conferenceQuality: number;
	priorStrength: number;
}

/**
 * Fetch rankings from the API
 */
export async function fetchRankings(year: number, week: number, weights?: AlgorithmWeights): Promise<void> {
	loading.set(true);
	error.set(null);

	try {
		let url = `${API_BASE}/rankings?year=${year}&week=${week}`;
		
		// Add weights if provided
		if (weights) {
			url += `&team_quality_weight=${weights.teamQuality}`;
			url += `&record_score_weight=${weights.recordScore}`;
			url += `&conference_quality_weight=${weights.conferenceQuality}`;
			url += `&prior_strength=${weights.priorStrength}`;
		}
		
		const response = await fetch(url);
		
		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.message || errorData.error || `HTTP error: ${response.status}`);
		}

		const data = await response.json();
		
		// Map API response to frontend types
		// API returns: team_rankings, conference_rankings
		// Frontend expects: teams, conferences
		const teamData: Team[] = (data.team_rankings || data.teams || []).map((t: any) => ({
			team_name: t.team_name || t.team || '',
			conference: t.conference || '',
			conference_type: t.conference_type || '',
			final_ranking_score: t.final_ranking_score || t.score || 0,
			team_quality_score: t.team_quality_score || 0,
			record_score: t.record_score || 0,
			conference_quality_score: t.conference_quality_score || 0,
			sos: t.sos ?? null,
			sov: t.sov ?? null,
			records: {
				total_wins: t.records?.total_wins ?? 0,
				total_losses: t.records?.total_losses ?? 0,
				conf_wins: t.records?.conf_wins ?? 0,
				conf_losses: t.records?.conf_losses ?? 0,
				power_wins: t.records?.power_wins ?? 0,
				power_losses: t.records?.power_losses ?? 0,
				group_five_wins: t.records?.group_five_wins ?? 0,
				group_five_losses: t.records?.group_five_losses ?? 0
			}
		}));

		const conferenceData: Conference[] = (data.conference_rankings || data.conferences || []).map((c: any) => ({
			conference: c.conference_name || c.conference || '',
			avg_ranking: c.average_team_quality || c.avg_ranking || 0,
			team_count: c.number_of_teams || c.team_count || 0,
			ranked_teams: c.ranked_teams ?? 0,
			power_win_pct: parseWinPct(c.record_vs_p4 || c.power_win_pct),
			g5_win_pct: parseWinPct(c.record_vs_g5 || c.g5_win_pct),
			fcs_wins: c.fcs_wins ?? c.record_vs_fcs?.split('-')[0] ?? undefined,
			fcs_losses: c.fcs_losses ?? c.record_vs_fcs?.split('-')[1] ?? undefined
		}));
		
		teams.set(teamData);
		conferences.set(conferenceData);
		
		// Update filter state with actual values
		filterState.update(state => ({
			...state,
			year: data.year || year,
			week: data.week || week
		}));

	} catch (e) {
		const message = e instanceof Error ? e.message : 'Failed to fetch rankings';
		error.set(message);
		teams.set([]);
		conferences.set([]);
	} finally {
		loading.set(false);
	}
}

/**
 * Set year filter
 */
export function setYear(year: number): void {
	filterState.update(state => ({ ...state, year }));
}

/**
 * Set week filter
 */
export function setWeek(week: number): void {
	filterState.update(state => ({ ...state, week }));
}

/**
 * Set conference filter
 */
export function setConferenceFilter(conference: string | null): void {
	filterState.update(state => ({ ...state, conferenceFilter: conference }));
}

/**
 * Set search query
 */
export function setSearchQuery(query: string): void {
	filterState.update(state => ({ ...state, searchQuery: query }));
}

/**
 * Clear all filters
 */
export function clearFilters(): void {
	filterState.update(state => ({
		...state,
		conferenceFilter: null,
		searchQuery: ''
	}));
}
