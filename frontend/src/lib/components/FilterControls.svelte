<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let years: number[] = [];
	export let selectedYear: number;
	export let selectedWeek: number;
	export let selectedView: 'fbs' | 'p4' | 'g5' | 'fcs' = 'fbs';
	export let maxWeek: number = 15;

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
</script>

<div class="card mb-6 overflow-hidden">
	<!-- Header -->
	<div class="bg-primary-600 text-white px-4 py-3 flex justify-between items-center">
		<h3 class="font-semibold flex items-center gap-2">
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
					d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
			</svg>
			Ranking Controls
		</h3>
	</div>

	<!-- View Tabs -->
	<div class="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 overflow-x-auto">
		<button 
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
				{selectedView === 'fbs' ? 'border-primary-500 text-primary-600 dark:text-primary-400 bg-white dark:bg-gray-800' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50'}"
			on:click={() => handleViewChange('fbs')}
		>
			National (FBS)
		</button>
		<button 
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
				{selectedView === 'g5' ? 'border-primary-500 text-primary-600 dark:text-primary-400 bg-white dark:bg-gray-800' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50'}"
			on:click={() => handleViewChange('g5')}
		>
			Group of 5
		</button>
		<button 
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
				{selectedView === 'p4' ? 'border-primary-500 text-primary-600 dark:text-primary-400 bg-white dark:bg-gray-800' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50'}"
			on:click={() => handleViewChange('p4')}
		>
			Power 4
		</button>
		<button 
			class="flex-1 min-w-[100px] py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
				{selectedView === 'fcs' ? 'border-primary-500 text-primary-600 dark:text-primary-400 bg-white dark:bg-gray-800' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/50'}"
			on:click={() => handleViewChange('fcs')}
		>
			FCS
		</button>
	</div>

	<!-- Basic Controls -->
	<div class="p-4 bg-white dark:bg-gray-800">
		<div class="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
			<!-- Year Selector -->
			<div class="flex-1 min-w-0 w-full sm:w-auto">
				<label for="year-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Season Year
				</label>
				<select
					id="year-select"
					value={selectedYear}
					on:change={handleYearChange}
					class="w-full form-select rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 
						dark:text-white py-2.5 px-3 focus:ring-primary-500 focus:border-primary-500"
				>
					{#each years as year}
						<option value={year}>{year}</option>
					{/each}
				</select>
			</div>

			<!-- Week Selector -->
			<div class="flex-1 min-w-0 w-full sm:w-auto">
				<label for="week-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Week
				</label>
				<select
					id="week-select"
					value={selectedWeek}
					on:change={handleWeekChange}
					class="w-full form-select rounded-lg border-gray-300 dark:border-gray-600 
						dark:bg-gray-700 dark:text-white py-2.5 px-3 
						focus:ring-primary-500 focus:border-primary-500"
				>
					{#each weeks as week}
						<option value={week}>Week {week}</option>
					{/each}
				</select>
			</div>

			<!-- Update Button -->
			<button
				on:click={handleUpdateRankings}
				class="w-full sm:w-auto btn btn-primary px-6 py-2.5 flex items-center justify-center gap-2"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
				</svg>
				Update Rankings
			</button>
		</div>
	</div>
</div>
