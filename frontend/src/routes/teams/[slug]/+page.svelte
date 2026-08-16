<script lang="ts">
	import SeoHead from '$lib/components/SeoHead.svelte';
	import DropSignup from '$lib/components/DropSignup.svelte';
	import AgentChatPanel from '$lib/components/AgentChatPanel.svelte';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
		teamPath,
		teamSlug,
		weekPath,
		gamePath,
		SITE_ORIGIN,
		citationText,
	} from '$lib/brand';
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

	$: t = data.team;
	$: title = pageTitle([`${t.team_name} ${RATING_NAME} rank`, `${data.year} Week ${data.week}`]);
	$: description = `${t.team_name} is #${data.rank} in ${BRAND_NAME} (${RATING_NAME} ${t.final_ranking_score.toFixed(1)}) for ${data.year} Week ${data.week}. ${TAGLINE}`;
	$: path = `/teams/${teamSlug(t.team_name)}`;
	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'SportsTeam',
		name: t.team_name,
		sport: 'American Football',
		memberOf: t.conference,
		url: `${SITE_ORIGIN}${path}`,
	};

	$: compareCandidates = data.neighbors.filter((n) => n.team_name !== t.team_name).slice(0, 3);
</script>

<SeoHead {title} {description} canonicalPath={path} {jsonLd} />

<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
		{BRAND_NAME} · {data.year} Week {data.week}
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
			<p class="font-display text-2xl text-primary-900 dark:text-white">#{data.rank}</p>
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
		<a href={weekPath(data.year, data.week)} class="btn btn-secondary">Full week board</a>
		<a href="/" class="btn btn-secondary">Live board</a>
	</div>

	{#if compareCandidates.length}
		<div class="mt-8">
			<h2 class="font-display text-lg text-primary-900 dark:text-white">Compare with TR+</h2>
			<ul class="mt-2 space-y-2">
				{#each compareCandidates as other}
					<li>
						<a
							href={gamePath(t.team_name, other.team_name, data.year, data.week)}
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
		{citationText(data.year, data.week)}
	</p>

	<div class="mt-8">
		<DropSignup compact />
	</div>
</div>

<AgentChatPanel teamName={t.team_name} open={askOpen} on:close={() => (askOpen = false)} />
