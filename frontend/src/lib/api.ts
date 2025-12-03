import type { RankingsResponse, Team, Conference } from '$lib/types';

// API configuration
// In production, this would point to your Python backend hosted on Render, Fly.io, etc.
// For development, proxy to local Flask app
const API_BASE = import.meta.env.DEV 
	? 'http://localhost:5000' 
	: (import.meta.env.VITE_API_URL || '');

/**
 * Fetch rankings from the backend API
 */
export async function fetchRankings(year: number, week: number): Promise<RankingsResponse> {
	const response = await fetch(`${API_BASE}/api/rankings?year=${year}&week=${week}`);
	
	if (!response.ok) {
		const error = await response.json().catch(() => ({ message: 'Unknown error' }));
		throw new Error(error.message || `HTTP ${response.status}`);
	}
	
	const data = await response.json();
	
	// Transform backend response to frontend types
	return transformRankingsResponse(data, year, week);
}

/**
 * Fetch available weeks for a given year
 */
export async function fetchAvailableWeeks(year: number): Promise<number[]> {
	try {
		const response = await fetch(`${API_BASE}/api/weeks?year=${year}`);
		if (!response.ok) {
			return Array.from({ length: 15 }, (_, i) => i + 1);
		}
		const data = await response.json();
		return data.weeks || Array.from({ length: 15 }, (_, i) => i + 1);
	} catch {
		return Array.from({ length: 15 }, (_, i) => i + 1);
	}
}

/**
 * Transform backend response to frontend format
 */
function transformRankingsResponse(data: any, year: number, week: number): RankingsResponse {
	const teams: Team[] = (data.team_rankings || data.teams || []).map((t: any) => ({
		team_name: t.team_name || t.team,
		conference: t.conference || '',
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

	const conferences: Conference[] = (data.conference_rankings || data.conferences || []).map((c: any) => ({
		conference: c.conference_name || c.conference || '',
		avg_ranking: c.average_team_quality || c.avg_ranking || 0,
		team_count: c.number_of_teams || c.team_count || 0,
		ranked_teams: c.ranked_teams ?? 0,
		power_win_pct: parseWinPct(c.record_vs_p4 || c.power_win_pct),
		g5_win_pct: parseWinPct(c.record_vs_g5 || c.g5_win_pct)
	}));

	return {
		teams,
		conferences,
		year,
		week,
		generated_at: data.generated_at || new Date().toISOString()
	};
}

/**
 * Parse win percentage from various formats
 */
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
 * Check if backend API is available
 */
export async function checkApiHealth(): Promise<boolean> {
	try {
		const response = await fetch(`${API_BASE}/api/health`, { 
			method: 'GET',
			signal: AbortSignal.timeout(5000)
		});
		return response.ok;
	} catch {
		return false;
	}
}
