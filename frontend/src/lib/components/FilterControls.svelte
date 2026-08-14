<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let years: number[] = [];
	export let selectedYear: number;
	export let selectedWeek: number;
	export let selectedView: 'fbs' | 'p4' | 'g5' | 'fcs' = 'fbs';
	export let maxWeek: number = 15;
	export let searchQuery = '';
	export let conferenceFilter: string | null = null;
	export let conferenceOptions: string[] = [];

	const dispatch = createEventDispatcher();

	$: weeks = Array.from({ length: maxWeek }, (_, i) => i + 1);

	function handleYearChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		dispatch('yearChange', parseInt(target.value));
	}

	function handleWeekChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		dispatch('weekChange', parseInt(target.value));
	}

	function handleUpdateRankings() {
		dispatch('updateRankings', {
			year: selectedYear,
			week: selectedWeek
		});
	}

	function handleViewChange(view: 'fbs' | 'p4' | 'g5' | 'fcs') {
		dispatch('viewChange', view);
	}

	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		dispatch('searchChange', target.value);
	}

	function handleConferenceChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		dispatch('conferenceChange', target.value || null);
	}
</script>

<div class="mb-6 overflow-hidden rounded-lg border border-primary-200 dark:border-primary-800 bg-white dark:bg-primary-900 shadow-sm">
	<div
		class="flex border-b border-primary-100 dark:border-primary-800 bg-cfb-chalk/70 dark:bg-primary-950/60 overflow-x-auto"
		role="tablist"
		aria-label="Board view"
	>
		<button
			type="button"
			role="tab"
			aria-selected={selectedView === 'fbs'}
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500
				{selectedView === 'fbs'
					? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright bg-white dark:bg-primary-900'
					: 'border-transparent text-primary-600/80 hover:text-primary-900 dark:text-primary-300 hover:bg-white/60 dark:hover:bg-primary-800/50'}"
			on:click={() => handleViewChange('fbs')}
		>
			National
		</button>
		<button
			type="button"
			role="tab"
			aria-selected={selectedView === 'g5'}
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500
				{selectedView === 'g5'
					? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright bg-white dark:bg-primary-900'
					: 'border-transparent text-primary-600/80 hover:text-primary-900 dark:text-primary-300 hover:bg-white/60 dark:hover:bg-primary-800/50'}"
			on:click={() => handleViewChange('g5')}
		>
			Group of 5
		</button>
		<button
			type="button"
			role="tab"
			aria-selected={selectedView === 'p4'}
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500
				{selectedView === 'p4'
					? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright bg-white dark:bg-primary-900'
					: 'border-transparent text-primary-600/80 hover:text-primary-900 dark:text-primary-300 hover:bg-white/60 dark:hover:bg-primary-800/50'}"
			on:click={() => handleViewChange('p4')}
		>
			Power 4
		</button>
		<button
			type="button"
			role="tab"
			aria-selected={selectedView === 'fcs'}
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500
				{selectedView === 'fcs'
					? 'border-primary-700 text-primary-800 dark:text-cfb-gold-bright bg-white dark:bg-primary-900'
					: 'border-transparent text-primary-600/80 hover:text-primary-900 dark:text-primary-300 hover:bg-white/60 dark:hover:bg-primary-800/50'}"
			on:click={() => handleViewChange('fcs')}
		>
			FCS
		</button>
	</div>

	<div class="p-4 space-y-4">
		<div class="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
			<div class="flex-1 min-w-0 w-full sm:w-auto">
				<label for="year-select" class="block text-sm font-medium text-primary-800 dark:text-primary-200 mb-1">
					Season
				</label>
				<select
					id="year-select"
					value={selectedYear}
					on:change={handleYearChange}
					class="w-full form-select rounded-md border-primary-200 dark:border-primary-700 dark:bg-primary-950
						dark:text-white py-2.5 px-3 focus:ring-primary-600 focus:border-primary-600"
				>
					{#each years as year}
						<option value={year}>{year}</option>
					{/each}
				</select>
			</div>

			<div class="flex-1 min-w-0 w-full sm:w-auto">
				<label for="week-select" class="block text-sm font-medium text-primary-800 dark:text-primary-200 mb-1">
					Week
				</label>
				<select
					id="week-select"
					value={selectedWeek}
					on:change={handleWeekChange}
					class="w-full form-select rounded-md border-primary-200 dark:border-primary-700
						dark:bg-primary-950 dark:text-white py-2.5 px-3
						focus:ring-primary-600 focus:border-primary-600"
				>
					{#each weeks as week}
						<option value={week}>Week {week}</option>
					{/each}
				</select>
			</div>

			<button
				type="button"
				on:click={handleUpdateRankings}
				class="w-full sm:w-auto btn btn-primary px-6 py-2.5 flex items-center justify-center gap-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					/>
				</svg>
				Refresh board
			</button>
		</div>

		<div class="flex flex-col sm:flex-row gap-4">
			<div class="flex-1 min-w-0 w-full">
				<label for="team-search" class="block text-sm font-medium text-primary-800 dark:text-primary-200 mb-1">
					Find your team
				</label>
				<input
					id="team-search"
					type="search"
					value={searchQuery}
					on:input={handleSearchInput}
					placeholder="Ohio State, SEC, Boise…"
					class="w-full rounded-md border-primary-200 dark:border-primary-700 dark:bg-primary-950 dark:text-white py-2.5 px-3 focus:ring-primary-600 focus:border-primary-600"
				/>
			</div>
			<div class="flex-1 min-w-0 w-full sm:max-w-xs">
				<label for="conference-filter" class="block text-sm font-medium text-primary-800 dark:text-primary-200 mb-1">
					Conference
				</label>
				<select
					id="conference-filter"
					value={conferenceFilter || ''}
					on:change={handleConferenceChange}
					class="w-full form-select rounded-md border-primary-200 dark:border-primary-700 dark:bg-primary-950 dark:text-white py-2.5 px-3 focus:ring-primary-600 focus:border-primary-600"
				>
					<option value="">All conferences</option>
					{#each conferenceOptions as conf}
						<option value={conf}>{conf}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>
</div>
