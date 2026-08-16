<script lang="ts">
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
	} from '$lib/brand';
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

	$: title = pageTitle([
		`${data.teamA.team_name} vs ${data.teamB.team_name}`,
		`${RATING_NAME} line`,
	]);
	$: description = `${data.teamA.team_name} (#${data.teamA.rank}) vs ${data.teamB.team_name} (#${data.teamB.rank}) — TR+ implies ${formatSpread(data.impliedSpread, data.favoriteName)}. ${TAGLINE}`;
	$: path = `/games/${data.canonicalSlug}`;
	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'SportsEvent',
		name: `${data.teamA.team_name} vs ${data.teamB.team_name}`,
		description,
		url: `${SITE_ORIGIN}${path}`,
		homeTeam: data.teamA.team_name,
		awayTeam: data.teamB.team_name,
	};
</script>

<SeoHead {title} {description} canonicalPath={path} {jsonLd} />

<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
		{BRAND_NAME} matchup · {data.year} Week {data.week}
	</p>
	<h1 class="mt-2 font-display text-3xl sm:text-4xl text-primary-900 dark:text-white">
		{data.teamA.team_name}
		<span class="text-primary-400 font-sans text-xl mx-2">vs</span>
		{data.teamB.team_name}
	</h1>
	<p class="mt-2 text-primary-700 dark:text-primary-300">
		TR+ favorite: <strong>{data.favoriteName}</strong>
		({formatSpread(data.impliedSpread, data.favoriteName)})
	</p>

	<div class="mt-6 grid sm:grid-cols-2 gap-4">
		{#each [data.teamA, data.teamB] as side}
			<a
				href={teamPath(side.team_name, data.year, data.week)}
				class="card p-4 hover:border-cfb-gold transition-colors"
			>
				<p class="text-xs uppercase text-primary-600 dark:text-primary-400">#{side.rank}</p>
				<p class="font-display text-xl text-primary-900 dark:text-white">{side.team_name}</p>
				<p class="mt-1 text-sm text-primary-700 dark:text-primary-300">
					{RATING_NAME} {side.final_ranking_score.toFixed(1)} · {side.records.total_wins}-{side.records.total_losses}
				</p>
			</a>
		{/each}
	</div>

	<MatchupLines
		favoriteName={data.favoriteName}
		impliedSpread={data.impliedSpread}
		marketSpread={data.marketSpread}
		delta={data.delta}
	/>

	<p class="mt-6 text-sm text-primary-700 dark:text-primary-300">
		Rankings stay free. This page exists so you can see where {RATING_NAME} disagrees with the market
		before you risk a dollar.
	</p>

	<div class="mt-8">
		<DropSignup compact />
	</div>

	<p class="mt-6 text-sm">
		<a href={weekPath(data.year, data.week)} class="text-primary-700 dark:text-cfb-gold-bright hover:underline"
			>← Week {data.week} board</a
		>
	</p>
</div>
