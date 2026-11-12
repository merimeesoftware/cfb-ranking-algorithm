import type { Team } from '$lib/types';

/** Elo used for place and for the number shown beside it. Missing Elo is 0. */
export function shownScore(team: Pick<Team, 'ordering_score' | 'team_quality_score'>): number {
	const raw = team.ordering_score ?? team.team_quality_score;
	const value = typeof raw === 'number' ? raw : Number(raw);
	return Number.isFinite(value) ? value : 0;
}

/** Published order is Elo. Heat weight is 0. Equal Elo keeps the previous order. */
export function orderTeamsByElo(teams: Team[]): Team[] {
	return teams
		.map((team, index) => ({ team, index }))
		.sort((a, b) => {
			const byElo = shownScore(b.team) - shownScore(a.team);
			if (byElo !== 0) return byElo;
			return a.index - b.index;
		})
		.map((row) => row.team);
}
