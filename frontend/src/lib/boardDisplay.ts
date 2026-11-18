import type { Team } from '$lib/types';

export type BoardRow = {
	rank: number;
	name: string;
	conference: string;
	color: string;
	tr: string;
	overall: string;
	record: string;
	quality: string;
	games: number;
	early: boolean;
	ahead: string;
	soft: string;
	qualityWins: number;
	qualityLosses: number;
	badLosses: number;
	powerLine: string;
	scheduleRank: number | null;
	teamCount: number;
	blendRank: number | null;
};

function halfUp(value: number, digits: number): number {
	const factor = 10 ** digits;
	return Math.round(value * factor) / factor;
}

export function formatTr(value: number): string {
	return halfUp(value, 1).toLocaleString('en-US', {
		minimumFractionDigits: 1,
		maximumFractionDigits: 1,
	});
}

function formatAhead(value: number): string {
	return halfUp(value, 2).toLocaleString('en-US', {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
}

function formatSoft(value: number): string {
	return String(Math.round(value * 100));
}

export function recordLine(team: Team): string {
	const wins = team.records?.total_wins ?? 0;
	const losses = team.records?.total_losses ?? 0;
	const confWins = team.records?.conf_wins ?? 0;
	const confLosses = team.records?.conf_losses ?? 0;
	const overall = `${wins}-${losses}`;
	if (confWins + confLosses === 0) return overall;
	return `${overall}, ${confWins}-${confLosses} in the ${team.conference}`;
}

export function toBoardRows(teams: Team[]): BoardRow[] {
	const blendOrder = [...teams].sort(
		(a, b) => (b.final_ranking_score || 0) - (a.final_ranking_score || 0)
	);
	const blendRank = new Map(blendOrder.map((team, index) => [team.team_name, index + 1]));
	return teams.map((team, index) => {
		const wins = team.records?.total_wins ?? 0;
		const losses = team.records?.total_losses ?? 0;
		const games = wins + losses;
		const ahead = formatAhead(team.record_ahead ?? 0);
		const soft = formatSoft(team.soft_win_share ?? 0);
		const powerWins = team.records?.power_wins ?? 0;
		const powerLosses = team.records?.power_losses ?? 0;
		return {
			rank: index + 1,
			name: team.team_name,
			conference: team.conference,
			color: team.color || '#14241c',
			tr: formatTr(team.ordering_score ?? team.team_quality_score),
			overall: `${wins}-${losses}`,
			record: recordLine(team),
			quality: `${ahead} wins ahead, ${soft}% soft`,
			games,
			early: games < 3,
			ahead,
			soft,
			qualityWins: team.quality_wins ?? 0,
			qualityLosses: team.quality_losses ?? 0,
			badLosses: team.bad_losses ?? 0,
			powerLine: `${powerWins}-${powerLosses}`,
			scheduleRank: team.sos_rank ?? null,
			teamCount: teams.length,
			blendRank: blendRank.get(team.team_name) ?? null,
		};
	});
}

export function shownGap(higher: string, lower: string): string {
	const left = Number(higher.replace(/,/g, ''));
	const right = Number(lower.replace(/,/g, ''));
	return halfUp(left - right, 1).toLocaleString('en-US', {
		minimumFractionDigits: 1,
		maximumFractionDigits: 1,
	});
}
