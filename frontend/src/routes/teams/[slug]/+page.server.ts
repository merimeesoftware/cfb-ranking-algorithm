import type { EntryGenerator, PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { latestPublishedWeek, loadWeekRankings } from '$lib/staticRankings';
import { findTeamBySlug, teamSlug } from '$lib/brand';

export const prerender = true;

export const entries: EntryGenerator = () => {
	const latest = latestPublishedWeek();
	if (!latest) return [];
	const data = loadWeekRankings(latest.year, latest.week);
	if (!data) return [];
	return data.teams.map((t) => ({ slug: teamSlug(t.team_name) }));
};

export const load: PageServerLoad = async ({ params }) => {
	// Prerender forbids url.searchParams — always seed from latest published week.
	const latest = latestPublishedWeek();
	if (!latest) throw error(404, 'No rankings published yet');

	const data = loadWeekRankings(latest.year, latest.week);
	if (!data) throw error(404, 'Week not found');

	const team = findTeamBySlug(data.teams, params.slug);
	if (!team) throw error(404, 'Team not found');

	const rank = data.teams.findIndex((t) => t.team_name === team.team_name) + 1;
	const neighbors = data.teams.slice(Math.max(0, rank - 3), Math.min(data.teams.length, rank + 2));

	return {
		year: latest.year,
		week: latest.week,
		team,
		rank,
		neighbors,
		top: data.teams.slice(0, 12).map((t, i) => ({ name: t.team_name, rank: i + 1 })),
	};
};
