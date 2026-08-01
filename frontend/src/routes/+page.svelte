<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import RankingsTable from '$lib/components/RankingsTable.svelte';
	import ConferenceTable from '$lib/components/ConferenceTable.svelte';
	import ConferenceDetailModal from '$lib/components/ConferenceDetailModal.svelte';
	import FilterControls from '$lib/components/FilterControls.svelte';
	import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
	import type { Conference } from '$lib/types';
	import {
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
		loadAvailableWeeks,
		parseUrlParams,
		buildUrlParams,
	} from '$lib/stores/rankings';

	let activeTab: 'teams' | 'conferences' = 'teams';
	let selectedConference: Conference | null = null;
	let selectedConferenceRank = 0;
	let showConferenceModal = false;

	function syncUrl() {
		const params = buildUrlParams($filterState, activeTab);
		goto(`?${params}`, { replaceState: true, keepFocus: true, noScroll: true });
	}

	onMount(async () => {
		const urlState = parseUrlParams(window.location.search);
		if (urlState.year) setYear(urlState.year);
		if (urlState.week) setWeek(urlState.week);
		if (urlState.view) setView(urlState.view);
		if (urlState.tab) activeTab = urlState.tab;
		await loadAvailableWeeks($filterState.year);
		await fetchRankings($filterState.year, $filterState.week);
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

	function setTab(tab: 'teams' | 'conferences') {
		activeTab = tab;
		syncUrl();
	}
</script>

<svelte:head>
	<title>CFB Rankings | Home</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
	<div class="text-center mb-6 sm:mb-8">
		<h1 class="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white">
			College Football Rankings
		</h1>
		<p class="mt-2 text-sm sm:text-base text-gray-600 dark:text-gray-400">
			Data-driven team quality rankings using Elo methodology
		</p>
	</div>

	<FilterControls
		years={$availableYears}
		selectedYear={$filterState.year}
		selectedWeek={$filterState.week}
		selectedView={$filterState.view}
		maxWeek={$maxWeek}
		on:yearChange={handleYearChange}
		on:weekChange={handleWeekChange}
		on:viewChange={handleViewChange}
		on:updateRankings={handleUpdateRankings}
	/>

	<div class="flex border-b border-gray-200 dark:border-gray-700 mb-4 mt-6" role="tablist">
		<button
			role="tab"
			aria-selected={activeTab === 'teams'}
			on:click={() => setTab('teams')}
			class="flex-1 sm:flex-none px-4 py-3 text-sm font-medium border-b-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
				{activeTab === 'teams'
					? 'border-primary-500 text-primary-600 dark:text-primary-400'
					: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
		>
			Teams
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'conferences'}
			on:click={() => setTab('conferences')}
			class="flex-1 sm:flex-none px-4 py-3 text-sm font-medium border-b-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500
				{activeTab === 'conferences'
					? 'border-primary-500 text-primary-600 dark:text-primary-400'
					: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
		>
			Conferences
		</button>
	</div>

	{#if $loading}
		<LoadingSpinner message="Loading rankings..." />
	{:else if $error}
		<div class="card p-6 text-center">
			<p class="text-gray-600 dark:text-gray-400">{$error}</p>
			<button
				on:click={() => fetchRankings($filterState.year, $filterState.week, { force: true })}
				class="btn btn-primary mt-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
			>
				Try Again
			</button>
		</div>
	{:else}
		{#if activeTab === 'teams'}
			<RankingsTable teams={$filteredTeams} />
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
