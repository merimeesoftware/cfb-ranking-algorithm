import type { PageServerLoad } from './$types';
import { latestPublishedWeek, loadPrevRanks, loadWeekRankings, loadWeekStory } from '$lib/staticRankings';

export const load: PageServerLoad = async () => {
	const latest = latestPublishedWeek();
	if (!latest) {
		return {
			seed: null as null,
			story: null as null,
			prevRanks: {} as Record<string, number>,
		};
	}
	const weekData = loadWeekRankings(latest.year, latest.week);
	const prev = loadPrevRanks(latest.year, latest.week);
	const prevRanks: Record<string, number> = {};
	prev.forEach((rank, name) => {
		prevRanks[name] = rank;
	});
	return {
		seed: weekData
			? {
					year: weekData.year,
					week: weekData.week,
					teams: weekData.teams.slice(0, 25),
					teamCount: weekData.teams.length,
				}
			: null,
		story: loadWeekStory(latest.year, latest.week),
		prevRanks,
	};
};
