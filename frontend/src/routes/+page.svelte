<script lang="ts">
	import RankingsTable from '$lib/components/RankingsTable.svelte';
	import ConferenceTable from '$lib/components/ConferenceTable.svelte';
	import FilterControls from '$lib/components/FilterControls.svelte';
	import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
	import { 
		filteredTeams, 
		conferences, 
		loading, 
		error, 
		filterState,
		availableYears,
		maxWeek,
		fetchRankings,
		setYear,
		setWeek
	} from '$lib/stores/rankings';
	import { onMount } from 'svelte';

	let activeTab: 'teams' | 'conferences' = 'teams';

	onMount(() => {
		fetchRankings($filterState.year, $filterState.week);
	});

	function handleYearChange(event: CustomEvent<number>) {
		setYear(event.detail);
		fetchRankings(event.detail, $filterState.week);
	}

	function handleWeekChange(event: CustomEvent<number>) {
		setWeek(event.detail);
		fetchRankings($filterState.year, event.detail);
	}
</script>

<svelte:head>
	<title>CFB Rankings | Home</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
	<!-- Hero Section - Mobile Optimized -->
	<div class="text-center mb-6 sm:mb-8">
		<h1 class="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 dark:text-white">
			College Football Rankings
		</h1>
		<p class="mt-2 text-sm sm:text-base text-gray-600 dark:text-gray-400">
			Data-driven team quality rankings using Elo methodology
		</p>
	</div>

	<!-- Filter Controls -->
	<FilterControls 
		years={$availableYears}
		selectedYear={$filterState.year}
		selectedWeek={$filterState.week}
		maxWeek={$maxWeek}
		on:yearChange={handleYearChange}
		on:weekChange={handleWeekChange}
	/>

	<!-- Tab Navigation - Mobile Friendly -->
	<div class="flex border-b border-gray-200 dark:border-gray-700 mb-4 mt-6">
		<button
			on:click={() => (activeTab = 'teams')}
			class="flex-1 sm:flex-none px-4 py-3 text-sm font-medium border-b-2 transition-colors
				{activeTab === 'teams'
					? 'border-primary-500 text-primary-600 dark:text-primary-400'
					: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
		>
			<span class="flex items-center justify-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
						d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
				</svg>
				Teams
			</span>
		</button>
		<button
			on:click={() => (activeTab = 'conferences')}
			class="flex-1 sm:flex-none px-4 py-3 text-sm font-medium border-b-2 transition-colors
				{activeTab === 'conferences'
					? 'border-primary-500 text-primary-600 dark:text-primary-400'
					: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
		>
			<span class="flex items-center justify-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
						d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
				</svg>
				Conferences
			</span>
		</button>
	</div>

	<!-- Content -->
	{#if $loading}
		<LoadingSpinner message="Loading rankings..." />
	{:else if $error}
		<div class="card p-6 text-center">
			<div class="text-red-500 dark:text-red-400 mb-2">
				<svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
						d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
			</div>
			<p class="text-gray-600 dark:text-gray-400">{$error}</p>
			<button 
				on:click={() => fetchRankings($filterState.year, $filterState.week)} 
				class="btn btn-primary mt-4"
			>
				Try Again
			</button>
		</div>
	{:else}
		{#if activeTab === 'teams'}
			<RankingsTable teams={$filteredTeams} />
		{:else}
			<ConferenceTable conferences={$conferences} />
		{/if}
	{/if}
</div>
