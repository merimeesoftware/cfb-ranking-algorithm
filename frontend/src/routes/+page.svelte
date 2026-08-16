<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import RankingsTable from '$lib/components/RankingsTable.svelte';
	import ConferenceTable from '$lib/components/ConferenceTable.svelte';
	import ConferenceDetailModal from '$lib/components/ConferenceDetailModal.svelte';
	import FilterControls from '$lib/components/FilterControls.svelte';
	import WeekStoryStrip from '$lib/components/WeekStoryStrip.svelte';
	import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
	import BoardActions from '$lib/components/BoardActions.svelte';
	import DropSignup from '$lib/components/DropSignup.svelte';
	import SeoHead from '$lib/components/SeoHead.svelte';
	import type { Conference } from '$lib/types';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
		weekPath,
		SITE_ORIGIN,
	} from '$lib/brand';
	import {
		teams,
		filteredTeams,
		filteredConferences,
		loading,
		error,
		filterState,
		availableYears,
		maxWeek,
		fetchRankings,
		setYear,
		setWeek,
		setView,
		setSearchQuery,
		setConferenceFilter,
		loadAvailableWeeks,
		parseUrlParams,
		buildUrlParams,
	} from '$lib/stores/rankings';

	export let data: {
		seed: {
			year: number;
			week: number;
			teams: import('$lib/types').Team[];
			teamCount: number;
		} | null;
		story: { headline?: string; paragraphs?: string[] } | null;
		prevRanks: Record<string, number>;
	};

	// SvelteKit injects these; declare so Svelte 4 does not warn about unknown props
	// svelte-ignore unused-export-let
	export let params: Record<string, string> = {};

	let activeTab: 'teams' | 'conferences' = 'teams';
	let selectedConference: Conference | null = null;
	let selectedConferenceRank = 0;
	let showConferenceModal = false;
	let selectedTeamName: string | null = null;
	let initialTeamName: string | null = null;
	let prevRanks: Record<string, number> = data.prevRanks || {};

	$: conferenceOptions = [
		...new Set($teams.map((t) => t.conference).filter(Boolean)),
	].sort((a, b) => a.localeCompare(b));

	$: seoTitle = pageTitle([
		$filterState.year && $filterState.week
			? `${$filterState.year} Week ${$filterState.week}`
			: 'This week',
		TAGLINE,
	]);

	$: seoDescription = data.story?.headline
		? `${data.story.headline} — ${TAGLINE}`
		: `${BRAND_NAME} ${RATING_NAME} board for ${$filterState.year} Week ${$filterState.week}. ${TAGLINE}`;

	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'ItemList',
		name: `${BRAND_NAME} ${$filterState.year} Week ${$filterState.week}`,
		description: seoDescription,
		url: `${SITE_ORIGIN}${weekPath($filterState.year, $filterState.week)}`,
		numberOfItems: Math.min(25, ($teams.length || data.seed?.teams.length || 0)),
		itemListElement: ($teams.length ? $teams : data.seed?.teams || []).slice(0, 25).map((t, i) => ({
			'@type': 'ListItem',
			position: i + 1,
			name: t.team_name,
		})),
	};

	function syncUrl() {
		const params = buildUrlParams($filterState, activeTab, selectedTeamName);
		goto(`?${params}`, { replaceState: true, keepFocus: true, noScroll: true });
	}

	onMount(async () => {
		const urlState = parseUrlParams(window.location.search);
		if (urlState.year) setYear(urlState.year);
		if (urlState.week) setWeek(urlState.week);
		if (urlState.view) setView(urlState.view);
		if (urlState.tab) activeTab = urlState.tab;
		if (urlState.searchQuery) setSearchQuery(urlState.searchQuery);
		if (urlState.conferenceFilter) setConferenceFilter(urlState.conferenceFilter);
		if (urlState.team) {
			initialTeamName = urlState.team;
			selectedTeamName = urlState.team;
		}
		await loadAvailableWeeks($filterState.year);
		await fetchRankings($filterState.year, $filterState.week);
		syncUrl();
	});

	function handleYearChange(event: CustomEvent<number>) {
		setYear(event.detail);
		fetchRankings(event.detail, $filterState.week).then(syncUrl);
	}

	function handleWeekChange(event: CustomEvent<number>) {
		setWeek(event.detail);
		fetchRankings($filterState.year, event.detail).then(syncUrl);
	}

	function handleViewChange(event: CustomEvent<'fbs' | 'p4' | 'g5' | 'fcs'>) {
		setView(event.detail);
		fetchRankings($filterState.year, $filterState.week, { view: event.detail, force: true }).then(syncUrl);
	}

	function handleSearchChange(event: CustomEvent<string>) {
		setSearchQuery(event.detail);
		syncUrl();
	}

	function handleConferenceFilterChange(event: CustomEvent<string | null>) {
		setConferenceFilter(event.detail);
		syncUrl();
	}

	function handleUpdateRankings(event: CustomEvent<{ year: number; week: number }>) {
		const { year, week } = event.detail;
		setYear(year);
		setWeek(week);
		fetchRankings(year, week, { force: true }).then(syncUrl);
	}

	function handleConferenceClick(event: CustomEvent<{ conference: Conference; rank: number }>) {
		selectedConference = event.detail.conference;
		selectedConferenceRank = event.detail.rank;
		showConferenceModal = true;
	}

	function closeConferenceModal() {
		showConferenceModal = false;
		selectedConference = null;
	}

	function handleTeamSelect(event: CustomEvent<string>) {
		selectedTeamName = event.detail;
		syncUrl();
	}

	function handleTeamClear() {
		selectedTeamName = null;
		initialTeamName = null;
		syncUrl();
	}

	function setTab(tab: 'teams' | 'conferences') {
		activeTab = tab;
		syncUrl();
	}

	async function goToBoard(event?: MouseEvent) {
		event?.preventDefault();
		const board = document.getElementById('board');
		board?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		await tick();
		const search = document.getElementById('team-search');
		if (search instanceof HTMLElement) {
			search.focus({ preventScroll: true });
		}
	}
</script>

<SeoHead
	title={seoTitle}
	description={seoDescription}
	canonicalPath={weekPath($filterState.year, $filterState.week)}
	{jsonLd}
/>

<section
	class="relative overflow-hidden bg-field-haze text-cfb-chalk"
	aria-labelledby="hero-brand"
>
	<div class="pointer-events-none absolute inset-0 opacity-40" aria-hidden="true">
		<div class="absolute left-0 right-0 top-1/3 h-px bg-cfb-chalk/25 animate-stripe-pulse"></div>
		<div class="absolute left-0 right-0 top-1/2 h-px bg-cfb-chalk/15"></div>
		<div class="absolute left-0 right-0 top-2/3 h-px bg-cfb-chalk/25 animate-stripe-pulse"></div>
		<div class="absolute inset-y-0 left-[8%] w-px bg-cfb-gold/30"></div>
		<div class="absolute inset-y-0 right-[8%] w-px bg-cfb-gold/30"></div>
	</div>

	<div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 lg:py-16">
		<p id="hero-brand" class="hero-brand animate-hero-rise">{BRAND_NAME}</p>
		<p class="mt-2 text-sm sm:text-base text-cfb-chalk/75 animate-hero-rise" style="animation-delay: 40ms">
			{$filterState.year} Week {$filterState.week} · {RATING_NAME} · through Saturday
		</p>
		<h1 class="hero-headline mt-3 sm:mt-4 animate-hero-rise" style="animation-delay: 80ms">
			{TAGLINE}
		</h1>
		<p
			class="mt-3 max-w-2xl text-base sm:text-lg text-cfb-chalk/90 leading-relaxed animate-hero-rise"
			style="animation-delay: 140ms"
		>
			{#if data.story?.headline}
				{data.story.headline}
			{:else}
				This week’s true order — open math, free to cite, ready before you argue or bet.
			{/if}
		</p>

		<div class="mt-6 animate-hero-rise" style="animation-delay: 200ms">
			<BoardActions
				year={$filterState.year}
				week={$filterState.week}
				topTeams={$teams.length ? $teams : data.seed?.teams || []}
			/>
		</div>

		<div class="mt-4 animate-hero-rise" style="animation-delay: 240ms">
			<a
				href="#board"
				on:click={goToBoard}
				class="text-sm text-cfb-gold-bright hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-cfb-gold rounded-sm"
			>
				Jump to the board
			</a>
			<span class="mx-2 text-cfb-chalk/40">·</span>
			<a
				href="/methodology"
				class="text-sm text-cfb-chalk/80 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cfb-gold rounded-sm"
			>
				How it works
			</a>
		</div>
	</div>
</section>

<div id="board" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 scroll-mt-20">
	<WeekStoryStrip year={$filterState.year} week={$filterState.week} />

	<FilterControls
		years={$availableYears}
		selectedYear={$filterState.year}
		selectedWeek={$filterState.week}
		selectedView={$filterState.view}
		maxWeek={$maxWeek}
		searchQuery={$filterState.searchQuery}
		conferenceFilter={$filterState.conferenceFilter}
		{conferenceOptions}
		on:yearChange={handleYearChange}
		on:weekChange={handleWeekChange}
		on:viewChange={handleViewChange}
		on:updateRankings={handleUpdateRankings}
		on:searchChange={handleSearchChange}
		on:conferenceChange={handleConferenceFilterChange}
	/>

	<div
		class="flex border-b border-primary-200 dark:border-primary-800 mb-4 mt-2"
		role="tablist"
		aria-label="Board sections"
	>
		<button
			type="button"
			role="tab"
			aria-selected={activeTab === 'teams'}
			on:click={() => setTab('teams')}
			class="flex-1 sm:flex-none px-4 py-3 text-sm font-semibold border-b-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600
				{activeTab === 'teams'
					? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright'
					: 'border-transparent text-primary-600 hover:text-primary-900 dark:text-primary-300'}"
		>
			The Board
		</button>
		<button
			type="button"
			role="tab"
			aria-selected={activeTab === 'conferences'}
			on:click={() => setTab('conferences')}
			class="flex-1 sm:flex-none px-4 py-3 text-sm font-semibold border-b-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600
				{activeTab === 'conferences'
					? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright'
					: 'border-transparent text-primary-600 hover:text-primary-900 dark:text-primary-300'}"
		>
			Conferences
		</button>
	</div>

	{#if $loading && $teams.length === 0 && !data.seed}
		<LoadingSpinner message="Building the board…" />
	{:else if $error && $teams.length === 0 && !data.seed}
		<div class="card p-6 text-center" role="alert" aria-live="assertive">
			<p class="font-display text-lg text-primary-900 dark:text-white">
				Couldn’t load this week’s rankings.
			</p>
			<p class="mt-2 text-sm text-primary-700 dark:text-primary-300">{$error}</p>
			<button
				type="button"
				on:click={() => fetchRankings($filterState.year, $filterState.week, { force: true })}
				class="btn btn-primary mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
			>
				Reload board
			</button>
		</div>
	{:else}
		{#if activeTab === 'teams'}
			<RankingsTable
				teams={$filteredTeams.length ? $filteredTeams : data.seed?.teams || []}
				allTeams={$teams.length ? $teams : data.seed?.teams || []}
				{initialTeamName}
				{prevRanks}
				year={$filterState.year}
				week={$filterState.week}
				on:teamSelect={handleTeamSelect}
				on:teamClear={handleTeamClear}
			/>
		{:else}
			<ConferenceTable conferences={$filteredConferences} on:click={handleConferenceClick} />
		{/if}
	{/if}

	<div class="mt-8">
		<DropSignup />
	</div>
</div>

{#if showConferenceModal && selectedConference}
	<ConferenceDetailModal
		conference={selectedConference}
		rank={selectedConferenceRank}
		allConferences={$filteredConferences}
		allTeams={$filteredTeams}
		on:close={closeConferenceModal}
	/>
{/if}
