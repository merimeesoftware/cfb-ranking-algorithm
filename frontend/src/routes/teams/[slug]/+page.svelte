<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import SeoHead from '$lib/components/SeoHead.svelte';
	import DropSignup from '$lib/components/DropSignup.svelte';
	import AgentChatPanel from '$lib/components/AgentChatPanel.svelte';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
		teamSlug,
		weekPath,
		gamePath,
		SITE_ORIGIN,
		citationText,
		findTeamBySlug,
	} from '$lib/brand';
	import { fetchRankingsFromApi } from '$lib/api';
	import type { Team } from '$lib/types';

	export let data: {
		year: number;
		week: number;
		team: Team;
		rank: number;
		neighbors: Team[];
		top: Array<{ name: string; rank: number }>;
	};

	let askOpen = false;
	let year = data.year;
	let week = data.week;
	let t = data.team;
	let rank = data.rank;
	let neighbors = data.neighbors;

	onMount(async () => {
		const y = Number($page.url.searchParams.get('year'));
		const w = Number($page.url.searchParams.get('week'));
		if (!y || !w || (y === year && w === week)) return;
		try {
			const rankings = await fetchRankingsFromApi(y, w);
			const found = findTeamBySlug(rankings.teams, teamSlug(data.team.team_name));
			if (!found) return;
			const idx = rankings.teams.findIndex((x) => x.team_name === found.team_name);
			year = y;
			week = w;
			t = found;
			rank = idx + 1;
			neighbors = rankings.teams.slice(Math.max(0, idx - 2), Math.min(rankings.teams.length, idx + 3));
		} catch {
			/* keep SSR seed */
		}
	});

	$: title = pageTitle([`${t.team_name} ${RATING_NAME} rank`, `${year} Week ${week}`]);
	$: description = `${t.team_name} is #${rank} in ${BRAND_NAME} (${RATING_NAME} ${t.final_ranking_score.toFixed(1)}) for ${year} Week ${week}. ${TAGLINE}`;
	$: path = `/teams/${teamSlug(t.team_name)}`;
	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'SportsTeam',
		name: t.team_name,
		sport: 'American Football',
		memberOf: t.conference,
		url: `${SITE_ORIGIN}${path}`,
	};

	$: compareCandidates = neighbors.filter((n) => n.team_name !== t.team_name).slice(0, 3);
</script>

<SeoHead {title} {description} canonicalPath={path} {jsonLd} />

<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
		{BRAND_NAME} · {year} Week {week}
	</p>
	<div class="mt-3 flex items-center gap-3">
		{#if t.logo}
			<img src={t.logo} alt="" class="w-12 h-12 object-contain" />
		{/if}
		<div>
			<h1 class="font-display text-3xl sm:text-4xl text-primary-900 dark:text-white">
				{t.team_name}
			</h1>
			<p class="text-sm text-primary-700 dark:text-primary-300">
				{t.conference} · {t.records.total_wins}-{t.records.total_losses}
			</p>
		</div>
	</div>

	<div class="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
		<div class="card p-3">
			<p class="text-xs uppercase text-primary-600 dark:text-primary-400">Rank</p>
			<p class="font-display text-2xl text-primary-900 dark:text-white">#{rank}</p>
		</div>
		<div class="card p-3">
			<p class="text-xs uppercase text-primary-600 dark:text-primary-400">{RATING_NAME}</p>
			<p class="font-display text-2xl text-primary-900 dark:text-white">
				{t.final_ranking_score.toFixed(1)}
			</p>
		</div>
		<div class="card p-3">
			<p class="text-xs uppercase text-primary-600 dark:text-primary-400">How they look</p>
			<p class="font-display text-2xl text-primary-900 dark:text-white">
				{t.team_quality_score.toFixed(0)}
			</p>
		</div>
		<div class="card p-3">
			<p class="text-xs uppercase text-primary-600 dark:text-primary-400">Who they beat</p>
			<p class="font-display text-2xl text-primary-900 dark:text-white">
				{t.record_score.toFixed(0)}
			</p>
		</div>
	</div>

	<p class="mt-4 text-sm text-primary-700 dark:text-primary-300">
		Quality wins: {t.quality_wins ?? 0} · Quality losses: {t.quality_losses ?? 0} · Bad losses:
		{t.bad_losses ?? 0}
	</p>

	<div class="mt-6 flex flex-wrap gap-2">
		<button type="button" class="btn btn-primary" on:click={() => (askOpen = true)}>
			Ask why they’re here
		</button>
		<a href={weekPath(year, week)} class="btn btn-secondary">Full week board</a>
		<a href="/" class="btn btn-secondary">Live board</a>
	</div>

	{#if compareCandidates.length}
		<div class="mt-8">
			<h2 class="font-display text-lg text-primary-900 dark:text-white">Compare with TR+</h2>
			<ul class="mt-2 space-y-2">
				{#each compareCandidates as other}
					<li>
						<a
							href={gamePath(t.team_name, other.team_name, year, week)}
							class="text-primary-700 dark:text-cfb-gold-bright hover:underline"
						>
							{t.team_name} vs {other.team_name}
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<p class="mt-6 text-xs text-primary-600 dark:text-primary-400">
		{citationText(year, week)}
	</p>

	<div class="mt-8">
		<DropSignup compact />
	</div>
</div>

<AgentChatPanel teamName={t.team_name} open={askOpen} on:close={() => (askOpen = false)} />
