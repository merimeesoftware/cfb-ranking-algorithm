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
