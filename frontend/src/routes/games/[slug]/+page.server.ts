import type { EntryGenerator, PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { latestPublishedWeek, loadWeekRankings } from '$lib/staticRankings';
import {
	findTeamBySlug,
	impliedSpread,
	matchupSlug,
	parseMatchupSlug,
	teamSlug,
} from '$lib/brand';

export const prerender = true;

export const entries: EntryGenerator = () => {
	const latest = latestPublishedWeek();
	if (!latest) return [];
	const data = loadWeekRankings(latest.year, latest.week);
	if (!data) return [];
	const top = data.teams.slice(0, 10);
	const slugs: Array<{ slug: string }> = [];
	for (let i = 0; i < top.length; i++) {
		for (let j = i + 1; j < Math.min(top.length, i + 3); j++) {
			slugs.push({ slug: matchupSlug(top[i].team_name, top[j].team_name) });
		}
	}
	return slugs;
};

export const load: PageServerLoad = async ({ params }) => {
	const parsed = parseMatchupSlug(params.slug);
	if (!parsed) throw error(404, 'Matchup not found');

	// Prerender forbids url.searchParams — use latest published week.
	const latest = latestPublishedWeek();
	if (!latest) throw error(404, 'Week not found');

	const data = loadWeekRankings(latest.year, latest.week);
	if (!data) throw error(404, 'Week not found');

	const teamA = findTeamBySlug(data.teams, parsed.a);
	const teamB = findTeamBySlug(data.teams, parsed.b);
	if (!teamA || !teamB) throw error(404, 'Team not found');

	const rankA = data.teams.findIndex((t) => t.team_name === teamA.team_name) + 1;
	const rankB = data.teams.findIndex((t) => t.team_name === teamB.team_name) + 1;

	const aFav = teamA.final_ranking_score >= teamB.final_ranking_score;
	const favorite = aFav ? teamA : teamB;
	const underdog = aFav ? teamB : teamA;
	const spread = impliedSpread(favorite.final_ranking_score, underdog.final_ranking_score);

	const marketSpread: number | null = null;
	const delta = marketSpread == null ? null : spread - Math.abs(marketSpread);

	return {
		year: latest.year,
		week: latest.week,
		teamA: { ...teamA, rank: rankA },
		teamB: { ...teamB, rank: rankB },
		favoriteName: favorite.team_name,
		impliedSpread: spread,
		marketSpread,
		delta,
		canonicalSlug: matchupSlug(teamA.team_name, teamB.team_name),
		altSlug: `${teamSlug(teamB.team_name)}-vs-${teamSlug(teamA.team_name)}`,
	};
};
