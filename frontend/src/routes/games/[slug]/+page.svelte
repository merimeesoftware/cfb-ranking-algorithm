<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import SeoHead from '$lib/components/SeoHead.svelte';
	import MatchupLines from '$lib/components/MatchupLines.svelte';
	import DropSignup from '$lib/components/DropSignup.svelte';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
		teamPath,
		weekPath,
		SITE_ORIGIN,
		formatSpread,
		findTeamBySlug,
		impliedSpread,
		teamSlug,
		matchupSlug,
	} from '$lib/brand';
	import { fetchRankingsFromApi } from '$lib/api';
	import type { Team } from '$lib/types';

	export let data: {
		year: number;
		week: number;
		teamA: Team & { rank: number };
		teamB: Team & { rank: number };
		favoriteName: string;
		impliedSpread: number;
		marketSpread: number | null;
		delta: number | null;
		canonicalSlug: string;
	};

	let year = data.year;
	let week = data.week;
	let teamA = data.teamA;
	let teamB = data.teamB;
	let favoriteName = data.favoriteName;
	let spread = data.impliedSpread;
	let marketSpread = data.marketSpread;
	let delta = data.delta;
	let canonicalSlug = data.canonicalSlug;

	onMount(async () => {
		const y = Number($page.url.searchParams.get('year'));
		const w = Number($page.url.searchParams.get('week'));
		if (!y || !w || (y === year && w === week)) return;
		try {
			const rankings = await fetchRankingsFromApi(y, w);
			const a = findTeamBySlug(rankings.teams, teamSlug(data.teamA.team_name));
			const b = findTeamBySlug(rankings.teams, teamSlug(data.teamB.team_name));
			if (!a || !b) return;
			const rankA = rankings.teams.findIndex((t) => t.team_name === a.team_name) + 1;
			const rankB = rankings.teams.findIndex((t) => t.team_name === b.team_name) + 1;
			const aFav = a.final_ranking_score >= b.final_ranking_score;
			const favorite = aFav ? a : b;
			const underdog = aFav ? b : a;
			year = y;
			week = w;
			teamA = { ...a, rank: rankA };
			teamB = { ...b, rank: rankB };
			favoriteName = favorite.team_name;
			spread = impliedSpread(favorite.final_ranking_score, underdog.final_ranking_score);
			delta = marketSpread == null ? null : spread - Math.abs(marketSpread);
			canonicalSlug = matchupSlug(a.team_name, b.team_name);
		} catch {
			/* keep SSR seed */
		}
	});

	$: title = pageTitle([`${teamA.team_name} vs ${teamB.team_name}`, `${RATING_NAME} line`]);
	$: description = `${teamA.team_name} (#${teamA.rank}) vs ${teamB.team_name} (#${teamB.rank}) — TR+ implies ${formatSpread(spread, favoriteName)}. ${TAGLINE}`;
	$: path = `/games/${canonicalSlug}`;
	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'SportsEvent',
		name: `${teamA.team_name} vs ${teamB.team_name}`,
		description,
		url: `${SITE_ORIGIN}${path}`,
		homeTeam: teamA.team_name,
		awayTeam: teamB.team_name,
	};
</script>

<SeoHead {title} {description} canonicalPath={path} {jsonLd} />

<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
		{BRAND_NAME} matchup · {year} Week {week}
	</p>
	<h1 class="mt-2 font-display text-3xl sm:text-4xl text-primary-900 dark:text-white">
		{teamA.team_name}
		<span class="text-primary-400 font-sans text-xl mx-2">vs</span>
		{teamB.team_name}
	</h1>
	<p class="mt-2 text-primary-700 dark:text-primary-300">
		TR+ favorite: <strong>{favoriteName}</strong>
		({formatSpread(spread, favoriteName)})
	</p>

	<div class="mt-6 grid sm:grid-cols-2 gap-4">
		{#each [teamA, teamB] as side}
			<a
				href={teamPath(side.team_name, year, week)}
				class="card p-4 hover:border-cfb-gold transition-colors"
			>
				<p class="text-xs uppercase text-primary-600 dark:text-primary-400">#{side.rank}</p>
				<p class="font-display text-xl text-primary-900 dark:text-white">{side.team_name}</p>
				<p class="mt-1 text-sm text-primary-700 dark:text-primary-300">
					{RATING_NAME}
					{side.final_ranking_score.toFixed(1)} · {side.records.total_wins}-{side.records.total_losses}
				</p>
			</a>
		{/each}
	</div>

	<MatchupLines
		{favoriteName}
		impliedSpread={spread}
		{marketSpread}
		{delta}
	/>

	<p class="mt-6 text-sm text-primary-700 dark:text-primary-300">
		Rankings stay free. This page exists so you can see where {RATING_NAME} disagrees with the market
		before you risk a dollar.
	</p>

	<div class="mt-8">
		<DropSignup compact />
	</div>

	<p class="mt-6 text-sm">
		<a href={weekPath(year, week)} class="text-primary-700 dark:text-cfb-gold-bright hover:underline"
			>← Week {week} board</a
		>
	</p>
</div>
