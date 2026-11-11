/**
 * Re-rank a published week with exploratory weights.
 * Every team is eligible. The return value is only the top slice.
 *
 * @param {Array<{
 *   team_name: string,
 *   team_quality_score: number,
 *   record_score: number,
 *   conference_quality_score: number,
 *   final_ranking_score?: number,
 *   officialRank?: number
 * }>} teams
 * @param {{ look: number, resume: number, league: number }} weights fractions of the board score
 * @param {number} limit
 */
export function whatIfTop(teams, weights, limit = 8) {
	const ranked = teams.some((team) => team.officialRank)
		? teams
		: teams
				.slice()
				.sort((a, b) => (b.final_ranking_score || 0) - (a.final_ranking_score || 0))
				.map((team, index) => ({ ...team, officialRank: index + 1 }));
	return ranked
		.map((team) => ({
			...team,
			whatIf:
				team.team_quality_score * weights.look +
				team.record_score * weights.resume +
				team.conference_quality_score * weights.league,
		}))
		.sort((a, b) => b.whatIf - a.whatIf || (a.officialRank || 0) - (b.officialRank || 0))
		.slice(0, limit);
}
