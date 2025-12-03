<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let years: number[] = [];
	export let selectedYear: number;
	export let selectedWeek: number;
	export let maxWeek: number = 15;

	const dispatch = createEventDispatcher();

	// Advanced controls state
	let showAdvanced = false;
	let teamQualityWeight = 55;
	let recordScoreWeight = 35;
	let conferenceQualityWeight = 10;
	let priorStrength = 0;

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
			week: selectedWeek,
			weights: {
				teamQuality: teamQualityWeight / 100,
				recordScore: recordScoreWeight / 100,
				conferenceQuality: conferenceQualityWeight / 100,
				priorStrength: priorStrength / 100
			}
		});
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
		<button
			on:click={() => showAdvanced = !showAdvanced}
			class="flex items-center gap-1 text-sm bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg transition-colors"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
					d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
			</svg>
			{showAdvanced ? 'Hide' : 'Advanced'}
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

	<!-- Advanced Controls -->
	{#if showAdvanced}
		<div class="p-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
			<h4 class="font-medium text-gray-900 dark:text-white mb-4">Algorithm Weights</h4>
			
			<div class="grid sm:grid-cols-3 gap-6 mb-6">
				<!-- Team Quality Weight -->
				<div>
					<label for="team-quality-weight" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Team Quality (Elo)
					</label>
					<input
						id="team-quality-weight"
						type="range"
						min="0"
						max="100"
						bind:value={teamQualityWeight}
						class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
					/>
					<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						Current: {teamQualityWeight}%
					</div>
				</div>

				<!-- Record Score Weight -->
				<div>
					<label for="record-score-weight" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Record Score (Resume)
					</label>
					<input
						id="record-score-weight"
						type="range"
						min="0"
						max="100"
						bind:value={recordScoreWeight}
						class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
					/>
					<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						Current: {recordScoreWeight}%
					</div>
				</div>

				<!-- Conference Quality Weight -->
				<div>
					<label for="conference-quality-weight" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Conference Quality
					</label>
					<input
						id="conference-quality-weight"
						type="range"
						min="0"
						max="100"
						bind:value={conferenceQualityWeight}
						class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
					/>
					<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						Current: {conferenceQualityWeight}%
					</div>
				</div>
			</div>

			<h4 class="font-medium text-gray-900 dark:text-white mb-4">Historical Prior Influence</h4>
			
			<div class="grid sm:grid-cols-2 gap-6">
				<div>
					<label for="prior-strength" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Prior Strength <span class="text-gray-400 font-normal">(Historical vs Fresh Start)</span>
					</label>
					<input
						id="prior-strength"
						type="range"
						min="0"
						max="100"
						bind:value={priorStrength}
						class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
					/>
					<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						Current: {priorStrength}% historical, {100 - priorStrength}% fresh
					</div>
				</div>

				<div class="bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded-lg p-3">
					<div class="flex gap-2">
						<svg class="w-5 h-5 text-cyan-600 dark:text-cyan-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
						</svg>
						<p class="text-sm text-cyan-700 dark:text-cyan-300">
							<strong>0%</strong> = Pure current season (like CFP). 
							<strong>100%</strong> = Full historical weight. 
							Default 30% balances stability with current-season focus.
						</p>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
