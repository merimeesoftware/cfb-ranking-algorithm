import type { Team } from '$lib/types';

/** Published order is Elo. Heat weight is 0. Equal Elo keeps the previous order. */
export function orderTeamsByElo(teams: Team[]): Team[] {
	return teams
		.map((team, index) => ({ team, index }))
		.sort((a, b) => {
			const byElo = b.team.team_quality_score - a.team.team_quality_score;
			if (byElo !== 0) return byElo;
			return a.index - b.index;
		})
		.map((row) => row.team);
}

/** Fewer than 3 decisions. Week 1 still keeps 70% of last year's final score. */
export function isEarlySeason(team: Team): boolean {
	if (typeof team.early_season === 'boolean') return team.early_season;
	const decisions = (team.records?.total_wins ?? 0) + (team.records?.total_losses ?? 0);
	return decisions < 3;
}

export function formatSigned(value: number, digits = 2): string {
	const text = value.toFixed(digits);
	return value > 0 ? `+${text}` : text;
}
