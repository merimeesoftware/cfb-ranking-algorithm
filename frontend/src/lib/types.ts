/**
 * TypeScript interfaces for CFB Rankings App
 */

export interface TeamRecords {
	total_wins: number;
	total_losses: number;
	conf_wins: number;
	conf_losses: number;
	power_wins: number;
	power_losses: number;
	group_five_wins: number;
	group_five_losses: number;
}

export interface Team {
	team_name: string;
	conference: string;
	conference_type?: string;
	final_ranking_score: number;
	team_quality_score: number;
	record_score: number;
	conference_quality_score: number;
	sos: number | null;
	sov: number | null;
	records: TeamRecords;
	logo?: string | null;
	logo_dark?: string | null;
	color?: string | null;
	alt_color?: string | null;
}

export interface Conference {
	conference: string;
	avg_ranking: number;
	team_count: number;
	ranked_teams: number;
	power_win_pct: number;
	g5_win_pct: number;
	fcs_wins?: number;
	fcs_losses?: number;
}

export interface RankingsResponse {
	teams: Team[];
	conferences: Conference[];
	year: number;
	week: number;
	generated_at: string;
}

export interface ApiError {
	error: string;
	message: string;
	status: number;
}

export type Theme = 'light' | 'dark' | 'system';

export interface FilterState {
	year: number;
	week: number;
	conferenceFilter: string | null;
	searchQuery: string;
}
