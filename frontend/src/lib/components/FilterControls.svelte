<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let years: number[] = [];
	export let selectedYear: number;
	export let selectedWeek: number;
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
</script>

<div class="flex flex-col sm:flex-row gap-3 sm:items-center">
	<!-- Year Selector -->
	<div class="flex items-center gap-2">
		<label for="year-select" class="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
			Season:
		</label>
		<select
			id="year-select"
			value={selectedYear}
			on:change={handleYearChange}
			class="form-select rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 
				dark:text-white text-sm py-2 px-3 focus:ring-primary-500 focus:border-primary-500
				flex-1 sm:flex-none sm:w-24"
		>
			{#each years as year}
				<option value={year}>{year}</option>
			{/each}
		</select>
	</div>

	<!-- Week Selector -->
	<div class="flex items-center gap-2">
		<label for="week-select" class="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
			Week:
		</label>
		<div class="flex items-center gap-1 flex-1 sm:flex-none overflow-x-auto pb-1 sm:pb-0">
			<!-- Quick week buttons for mobile -->
			<div class="flex sm:hidden gap-1">
				{#each weeks as week}
					<button
						on:click={() => dispatch('weekChange', week)}
						class="min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors
							{selectedWeek === week 
								? 'bg-primary-600 text-white' 
								: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
					>
						{week}
					</button>
				{/each}
			</div>
			
			<!-- Dropdown for desktop -->
			<select
				id="week-select"
				value={selectedWeek}
				on:change={handleWeekChange}
				class="hidden sm:block form-select rounded-lg border-gray-300 dark:border-gray-600 
					dark:bg-gray-700 dark:text-white text-sm py-2 px-3 
					focus:ring-primary-500 focus:border-primary-500 w-24"
			>
				{#each weeks as week}
					<option value={week}>Week {week}</option>
				{/each}
			</select>
		</div>
	</div>
</div>
