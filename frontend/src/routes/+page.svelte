<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import RankingsTable from '$lib/components/RankingsTable.svelte';
	import ConferenceTable from '$lib/components/ConferenceTable.svelte';
	import ConferenceDetailModal from '$lib/components/ConferenceDetailModal.svelte';
	import FilterControls from '$lib/components/FilterControls.svelte';
	import WeekStoryStrip from '$lib/components/WeekStoryStrip.svelte';
	import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
	import type { Conference } from '$lib/types';
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

	// SvelteKit injects these; declare so Svelte 4 does not warn about unknown props
	// svelte-ignore unused-export-let
	export let params: Record<string, string> = {};
	// svelte-ignore unused-export-let
	export let data: Record<string, unknown> = {};

	let activeTab: 'teams' | 'conferences' = 'teams';
	let selectedConference: Conference | null = null;
	let selectedConferenceRank = 0;
	let showConferenceModal = false;
	let selectedTeamName: string | null = null;
	let initialTeamName: string | null = null;

	$: conferenceOptions = [
		...new Set($teams.map((t) => t.conference).filter(Boolean)),
	].sort((a, b) => a.localeCompare(b));

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
		const search = document.getElementById('team-search');
		board?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		await tick();
		if (search instanceof HTMLElement) {
			search.focus({ preventScroll: true });
		}
	}
</script>

<svelte:head>
	<title>CFB Rankings | Who belongs higher?</title>
</svelte:head>

<section
	class="relative overflow-hidden bg-field-haze text-cfb-chalk"
	aria-labelledby="hero-brand"
>
	<div
		class="pointer-events-none absolute inset-0 opacity-40"
		aria-hidden="true"
	>
		<div class="absolute left-0 right-0 top-1/3 h-px bg-cfb-chalk/25 animate-stripe-pulse"></div>
		<div class="absolute left-0 right-0 top-1/2 h-px bg-cfb-chalk/15"></div>
		<div class="absolute left-0 right-0 top-2/3 h-px bg-cfb-chalk/25 animate-stripe-pulse"></div>
		<div class="absolute inset-y-0 left-[8%] w-px bg-cfb-gold/30"></div>
		<div class="absolute inset-y-0 right-[8%] w-px bg-cfb-gold/30"></div>
	</div>

	<div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 sm:py-20 lg:py-24">
		<p
			id="hero-brand"
			class="hero-brand animate-hero-rise"
		>
			CFB Rankings
		</p>
		<h1 class="hero-headline mt-4 sm:mt-5 animate-hero-rise" style="animation-delay: 80ms">
			Who belongs higher?
		</h1>
		<p
			class="mt-4 max-w-2xl text-base sm:text-lg text-cfb-chalk/90 leading-relaxed animate-hero-rise"
			style="animation-delay: 140ms"
		>
			This week’s board — clear takes for the fight, not voter vibes.
		</p>

		<div
			class="mt-8 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 animate-hero-rise"
			style="animation-delay: 200ms"
		>
			<div>
				<a
					href="#board"
					on:click={goToBoard}
					class="btn btn-primary bg-cfb-gold text-primary-950 hover:bg-cfb-gold-bright focus:ring-cfb-gold px-6 py-3 text-base font-semibold shadow-sm"
				>
					See this week’s rankings
				</a>
				<p class="mt-2 text-sm text-cfb-chalk/70 sm:pl-1">Jump into the controversy</p>
			</div>
			<a
				href="/methodology"
				class="btn btn-ghost-light px-5 py-3 text-base sm:self-start"
			>
				How the board works
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

	{#if $loading}
		<LoadingSpinner message="Building the board…" />
	{:else if $error}
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
				teams={$filteredTeams}
				allTeams={$teams}
				{initialTeamName}
				on:teamSelect={handleTeamSelect}
				on:teamClear={handleTeamClear}
			/>
		{:else}
			<ConferenceTable conferences={$filteredConferences} on:click={handleConferenceClick} />
		{/if}
	{/if}
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
