import formula from './publicFormula.json';

/** Published formula. Generated from the ranker defaults. Do not edit by hand. */
export const PUBLIC_FORMULA = formula;

export function weightPercent(weight: number): string {
	return `${Math.round(weight * 100)}%`;
}

export function weightDecimal(weight: number): string {
	return weight.toFixed(2);
}

export interface ScoreParts {
	look: number;
	resume: number;
	league: number;
	total: number;
}

/** Weighted parts of the published board score. They add up to that score. */
export function scoreParts(team: {
	team_quality_score: number;
	record_score: number;
	conference_quality_score: number;
}): ScoreParts {
	const look = team.team_quality_score * formula.team_quality_weight;
	const resume = team.record_score * formula.record_weight;
	const league = team.conference_quality_score * formula.conference_weight;
	return { look, resume, league, total: look + resume + league };
}
