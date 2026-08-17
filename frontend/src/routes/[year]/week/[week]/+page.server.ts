import type { EntryGenerator, PageServerLoad } from './$types';
import {
	listPublishedWeeks,
	loadPrevRanks,
	loadWeekRankings,
	loadWeekStory,
} from '$lib/staticRankings';
import { error } from '@sveltejs/kit';

export const entries: EntryGenerator = () =>
	listPublishedWeeks().map(({ year, week }) => ({
		year: String(year),
		week: String(week),
	}));

export const prerender = true;

export const load: PageServerLoad = async ({ params }) => {
	const year = Number(params.year);
	const week = Number(params.week);
	if (!Number.isFinite(year) || !Number.isFinite(week)) {
		throw error(404, 'Week not found');
	}
	const data = loadWeekRankings(year, week);
	if (!data) throw error(404, 'Week not found');
	const prev = loadPrevRanks(year, week);
	const prevRanks: Record<string, number> = {};
	prev.forEach((rank, name) => {
		prevRanks[name] = rank;
	});
	return {
		year: data.year,
		week: data.week,
		teams: data.teams,
		conferences: data.conferences,
		story: loadWeekStory(year, week),
		prevRanks,
	};
};
