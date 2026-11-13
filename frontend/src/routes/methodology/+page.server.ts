import type { PageServerLoad } from './$types';
import { latestPublishedWeek, loadWeekRankings } from '$lib/staticRankings';
import type { Team } from '$lib/types';

type Part = {
	name: string;
	look: number;
	resume: number;
	league: number;
};

function topFive(parts: Part[], look: number, resume: number, league: number): string[] {
	return parts
		.map((row, index) => ({
			name: row.name,
			index,
			score: (look / 100) * row.look + (resume / 100) * row.resume + (league / 100) * row.league,
		}))
		.sort((a, b) => b.score - a.score || a.index - b.index)
		.slice(0, 5)
		.map((row) => row.name);
}

export const load: PageServerLoad = async () => {
	const latest = latestPublishedWeek();
	if (!latest) {
		return {
			year: 0,
			week: 0,
			official: [] as string[],
			oldBlend: [] as string[],
			whatIf: [] as string[],
			parts: [] as Part[],
			teamCount: 0,
			moved: 0,
			meanGap: '0.00',
			officialLeader: '',
		};
	}
	const week = loadWeekRankings(latest.year, latest.week);
	const parts: Part[] = (week?.teams || []).map((team: Team) => ({
		name: team.team_name,
		look: team.team_quality_score,
		resume: team.record_score,
		league: team.conference_quality_score,
	}));
	const blendOrder = parts
		.map((row, index) => ({
			index,
			score: 0.8 * row.look + 0.15 * row.resume + 0.05 * row.league,
		}))
		.sort((a, b) => b.score - a.score || a.index - b.index);
	const blendRank = new Map(blendOrder.map((row, rank) => [row.index, rank + 1]));
	let moved = 0;
	let gapSum = 0;
	parts.forEach((_, index) => {
		const gap = Math.abs(index + 1 - (blendRank.get(index) ?? index + 1));
		gapSum += gap;
		if (gap !== 0) moved += 1;
	});
	const mean = parts.length ? gapSum / parts.length : 0;
	return {
		year: latest.year,
		week: latest.week,
		official: parts.slice(0, 5).map((row) => row.name),
		oldBlend: topFive(parts, 80, 15, 5),
		whatIf: topFive(parts, 70, 30, 0),
		parts,
		teamCount: parts.length,
		moved,
		meanGap: (Math.round(mean * 100) / 100).toFixed(2),
		officialLeader: parts[0]?.name ?? '',
	};
};
