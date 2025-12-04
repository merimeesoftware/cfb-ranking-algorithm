<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Conference } from '$lib/types';

	export let conferences: Conference[] = [];
	export let loading: boolean = false;

	const dispatch = createEventDispatcher();

	let showAllConferences = false;
	const DEFAULT_DISPLAY_COUNT = 7;

	// Sort conferences by average ranking (highest/best first)
	$: sortedConferences = [...conferences].sort((a, b) => b.avg_ranking - a.avg_ranking);
	
	// Display limited conferences unless expanded
	$: displayedConferences = showAllConferences 
		? sortedConferences 
		: sortedConferences.slice(0, DEFAULT_DISPLAY_COUNT);
	
	function formatWinPct(pct: number): string {
		return (pct * 100).toFixed(0) + '%';
	}
	
	function formatFcsWinPct(conf: Conference): string {
		if (conf.fcs_wins !== undefined && conf.fcs_losses !== undefined) {
			const total = conf.fcs_wins + conf.fcs_losses;
			if (total === 0) return '-';
			const pct = conf.fcs_wins / total;
			return formatWinPct(pct);
		}
		return '-';
	}

	function handleConferenceClick(conf: Conference, index: number) {
		dispatch('click', { conference: conf, rank: index + 1 });
	}

	// Conference colors map
	const conferenceColors: Record<string, string> = {
		'SEC': '#ffd700',
		'Big Ten': '#0033a0',
		'Big 12': '#003087',
		'ACC': '#013ca6',
		'Pac-12': '#004b91',
		'Mountain West': '#1c4d8f',
		'American Athletic': '#c41230',
		'Conference USA': '#1a3461',
		'Sun Belt': '#f9a11b',
		'Mid-American': '#1a1a1a',
		'FBS Independents': '#4b5563'
	};

	function getConferenceColor(confName: string): string {
		return conferenceColors[confName] || '#6b7280';
	}
</script>

<div class="space-y-3">
	{#if loading}
		<div class="animate-pulse space-y-3">
			{#each Array(7) as _}
				<div class="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
			{/each}
		</div>
	{:else if sortedConferences.length === 0}
		<div class="text-center py-8 text-gray-500 dark:text-gray-400">
			No conference data available
		</div>
	{:else}
		<!-- Header -->
		<div class="card overflow-hidden">
			<div class="bg-gray-50 dark:bg-gray-800 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
				<h3 class="font-semibold text-gray-900 dark:text-white">
					{showAllConferences ? 'All Conferences' : 'Top 7 Conferences'}
				</h3>
			</div>

			<!-- Mobile Card View -->
			<div class="sm:hidden">
				{#each displayedConferences as conf, index}
					<button
						on:click={() => handleConferenceClick(conf, index)}
						class="w-full text-left p-4 border-b border-gray-100 dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
					>
						<div class="flex items-start gap-3">
							<span 
								class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 text-white"
								style="background-color: {getConferenceColor(conf.conference)}"
							>
								{index + 1}
							</span>
							<div class="flex-1 min-w-0">
								<h3 class="font-semibold text-gray-900 dark:text-white truncate">
									{conf.conference}
								</h3>
								<div class="mt-2 grid grid-cols-4 gap-2 text-xs">
									<div>
										<div class="text-gray-500 dark:text-gray-400">Avg Rank</div>
										<div class="font-medium text-gray-900 dark:text-white">
											{conf.avg_ranking.toFixed(1)}
										</div>
									</div>
									<div>
										<div class="text-gray-500 dark:text-gray-400">Teams</div>
										<div class="font-medium text-gray-900 dark:text-white">
											{conf.team_count}
										</div>
									</div>
									<div>
										<div class="text-gray-500 dark:text-gray-400">P4 W%</div>
										<div class="font-medium text-gray-900 dark:text-white">
											{formatWinPct(conf.power_win_pct)}
										</div>
									</div>
									<div>
										<div class="text-gray-500 dark:text-gray-400">FCS W%</div>
										<div class="font-medium text-gray-900 dark:text-white">
											{formatFcsWinPct(conf)}
										</div>
									</div>
								</div>
							</div>
						</div>
					</button>
				{/each}
			</div>

			<!-- Desktop Table View -->
			<div class="hidden sm:block overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="bg-gray-50 dark:bg-gray-700/50 text-left text-xs font-medium 
							text-gray-500 dark:text-gray-400 uppercase tracking-wider">
							<th class="px-4 py-3 w-16">#</th>
							<th class="px-4 py-3">Conference</th>
							<th class="px-4 py-3 text-right">Avg Rank</th>
							<th class="px-4 py-3 text-right">Teams</th>
							<th class="px-4 py-3 text-right">Power 4 W%</th>
							<th class="px-4 py-3 text-right">G5 W%</th>
							<th class="px-4 py-3 text-right">FCS W%</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each displayedConferences as conf, index}
							<tr 
								on:click={() => handleConferenceClick(conf, index)}
								class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors cursor-pointer"
							>
								<td class="px-4 py-3">
									<span 
										class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white"
										style="background-color: {getConferenceColor(conf.conference)}"
									>
										{index + 1}
									</span>
								</td>
								<td class="px-4 py-3 font-medium text-gray-900 dark:text-white">
									{conf.conference}
								</td>
								<td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
									{conf.avg_ranking.toFixed(1)}
								</td>
								<td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
									{conf.team_count}
								</td>
								<td class="px-4 py-3 text-right">
									<span class="{conf.power_win_pct >= 0.5 
										? 'text-green-600 dark:text-green-400' 
										: 'text-gray-600 dark:text-gray-400'}">
										{formatWinPct(conf.power_win_pct)}
									</span>
								</td>
								<td class="px-4 py-3 text-right">
									<span class="{conf.g5_win_pct >= 0.5 
										? 'text-green-600 dark:text-green-400' 
										: 'text-gray-600 dark:text-gray-400'}">
										{formatWinPct(conf.g5_win_pct)}
									</span>
								</td>
								<td class="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
									{formatFcsWinPct(conf)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			
			<!-- Show More / Show Less Button -->
			{#if sortedConferences.length > DEFAULT_DISPLAY_COUNT}
				<div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
					<button
						on:click={() => showAllConferences = !showAllConferences}
						class="w-full text-center text-sm font-medium text-primary-600 dark:text-primary-400 
							hover:text-primary-800 dark:hover:text-primary-300 transition-colors
							flex items-center justify-center gap-2"
					>
						{#if showAllConferences}
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
							</svg>
							Show Top 7 Only
						{:else}
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
							</svg>
							View All {sortedConferences.length} Conferences
						{/if}
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
