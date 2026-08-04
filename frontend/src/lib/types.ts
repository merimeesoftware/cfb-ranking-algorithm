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

export interface WinDetail {
	opponent: string;
	opponent_rank: number;
	opponent_elo: number;
	is_road: boolean;
	mov: number;
	is_quality_win?: boolean;
	is_cupcake_win?: boolean;
}

export interface LossDetail {
	opponent: string;
	opponent_rank: number;
	opponent_elo: number;
	is_home: boolean;
	mov: number;
	is_quality_loss?: boolean;
	is_bad_loss?: boolean;
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
	sos_rank?: number;
	sov_rank?: number;
	records: TeamRecords;
	logo?: string | null;
	logo_dark?: string | null;
	color?: string | null;
	alt_color?: string | null;
	
	// V4.2 Resume Metrics
	quality_wins?: number;
	quality_losses?: number;
	bad_losses?: number;
	bad_wins?: number;
	top_10_wins?: number;
	top_25_wins?: number;
	cross_tier_wins?: number;
	h2h_bonus?: number;
	quality_loss_bonus?: number;
	bad_loss_penalty?: number;
	quality_win_bonus?: number;
	bad_win_penalty?: number;

	// V4.5 Game Details
	wins_details?: WinDetail[];
	losses_details?: LossDetail[];

	/** Populated from /rankings/team detail fetch */
	path_to_climb?: PathToClimb;
	comparisons_ahead?: TeamComparison[];
	comparisons_behind?: TeamComparison[];
	why_blurb?: string;
}

export interface PathToClimb {
	at_top: boolean;
	team_above: string | null;
	score_gap: number;
	gaps: { tq: number; resume: number; cq: number };
	primary_lever: string | null;
	summary: string;
}

export interface TeamComparison {
	other_team: string;
	other_rank: number;
	other_conference?: string;
	other_record?: string;
	score_diff: number;
	direction?: 'ahead' | 'behind';
	factors?: Array<{
		factor: string;
		advantage: string;
		diff: number;
		contribution: number;
		explanation: string;
	}>;
}

export interface Conference {
	conference: string;
	conference_type?: string;
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
	view: 'fbs' | 'p4' | 'g5' | 'fcs';
}
