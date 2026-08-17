<script lang="ts">
	import RankingsTable from '$lib/components/RankingsTable.svelte';
	import ConferenceTable from '$lib/components/ConferenceTable.svelte';
	import BoardActions from '$lib/components/BoardActions.svelte';
	import DropSignup from '$lib/components/DropSignup.svelte';
	import SeoHead from '$lib/components/SeoHead.svelte';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
		weekPath,
		SITE_ORIGIN,
		citationText,
	} from '$lib/brand';

	export let data: {
		year: number;
		week: number;
		teams: import('$lib/types').Team[];
		conferences: import('$lib/types').Conference[];
		story: { headline?: string; paragraphs?: string[] } | null;
		prevRanks: Record<string, number>;
	};

	let tab: 'teams' | 'conferences' = 'teams';

	$: title = pageTitle([`${data.year} Week ${data.week}`, `${RATING_NAME} rankings`]);
	$: description = data.story?.headline
		? `${data.story.headline} — ${TAGLINE}`
		: `${BRAND_NAME} ${RATING_NAME} for ${data.year} Week ${data.week}. ${TAGLINE}`;
	$: path = weekPath(data.year, data.week);
	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'ItemList',
		name: `${BRAND_NAME} ${data.year} Week ${data.week}`,
		description,
		url: `${SITE_ORIGIN}${path}`,
		numberOfItems: Math.min(25, data.teams.length),
		itemListElement: data.teams.slice(0, 25).map((t, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: t.team_name,
		})),
	};
</script>

<SeoHead {title} {description} canonicalPath={path} {jsonLd} />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
		{BRAND_NAME} · {data.year} Week {data.week}
	</p>
	<h1 class="mt-2 font-display text-3xl sm:text-4xl text-primary-900 dark:text-white">
		{TAGLINE}
	</h1>
	{#if data.story?.headline}
		<p class="mt-3 text-lg text-primary-800 dark:text-primary-200">{data.story.headline}</p>
	{/if}
	{#if data.story?.paragraphs?.length}
		<div class="mt-3 space-y-2 max-w-3xl">
			{#each data.story.paragraphs.slice(0, 3) as para}
				<p class="text-sm text-primary-700 dark:text-primary-300 leading-relaxed">{para}</p>
			{/each}
		</div>
	{/if}

	<div class="mt-6">
		<BoardActions year={data.year} week={data.week} topTeams={data.teams} />
	</div>
	<p class="mt-2 text-xs text-primary-600 dark:text-primary-400">
		{citationText(data.year, data.week)}
	</p>

	<div class="flex gap-4 border-b border-primary-200 dark:border-primary-800 mt-8 mb-4" role="tablist">
		<button
			type="button"
			role="tab"
			aria-selected={tab === 'teams'}
			class="pb-2 text-sm font-semibold border-b-2 {tab === 'teams'
				? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright'
				: 'border-transparent text-primary-600'}"
			on:click={() => (tab = 'teams')}
		>
			The Board
		</button>
		<button
			type="button"
			role="tab"
			aria-selected={tab === 'conferences'}
			class="pb-2 text-sm font-semibold border-b-2 {tab === 'conferences'
				? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright'
				: 'border-transparent text-primary-600'}"
			on:click={() => (tab = 'conferences')}
		>
			Conferences
		</button>
	</div>

	{#if tab === 'teams'}
		<RankingsTable
			teams={data.teams}
			allTeams={data.teams}
			prevRanks={data.prevRanks}
			year={data.year}
			week={data.week}
		/>
	{:else}
		<ConferenceTable conferences={data.conferences} />
	{/if}

	<div class="mt-8">
		<DropSignup />
	</div>

	<p class="mt-6 text-sm">
		<a href="/" class="text-primary-700 dark:text-cfb-gold-bright hover:underline">← Live board</a>
		<span class="mx-2 text-primary-300">·</span>
		<a href="/methodology" class="text-primary-700 dark:text-cfb-gold-bright hover:underline"
			>How it works</a
		>
	</p>
</div>
