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
		return { year: 0, week: 0, official: [] as string[], oldBlend: [] as string[], whatIf: [] as string[], parts: [] as Part[] };
	}
	const week = loadWeekRankings(latest.year, latest.week);
	const parts: Part[] = (week?.teams || []).map((team: Team) => ({
		name: team.team_name,
		look: team.team_quality_score,
		resume: team.record_score,
		league: team.conference_quality_score,
	}));
	return {
		year: latest.year,
		week: latest.week,
		official: parts.slice(0, 5).map((row) => row.name),
		oldBlend: topFive(parts, 80, 15, 5),
		whatIf: topFive(parts, 70, 30, 0),
		parts,
	};
};
