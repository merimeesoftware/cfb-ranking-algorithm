<script lang="ts">
	import type { Conference } from '$lib/types';

	export let conferences: Conference[] = [];
	export let loading: boolean = false;

	// Sort conferences by average ranking (highest/best first)
	$: sortedConferences = [...conferences].sort((a, b) => b.avg_ranking - a.avg_ranking);
</script>

<div class="space-y-3">
	{#if loading}
		<div class="animate-pulse space-y-3">
			{#each Array(10) as _}
				<div class="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
			{/each}
		</div>
	{:else if sortedConferences.length === 0}
		<div class="text-center py-8 text-gray-500 dark:text-gray-400">
			No conference data available
		</div>
	{:else}
		<!-- Mobile Card View -->
		<div class="sm:hidden space-y-3">
			{#each sortedConferences as conf, index}
				<div class="card p-4">
					<div class="flex items-start gap-3">
						<span class="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/50 
							text-primary-600 dark:text-primary-400 flex items-center justify-center 
							text-sm font-bold shrink-0">
							{index + 1}
						</span>
						<div class="flex-1 min-w-0">
							<h3 class="font-semibold text-gray-900 dark:text-white truncate">
								{conf.conference}
							</h3>
							<div class="mt-2 grid grid-cols-3 gap-2 text-xs">
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
									<div class="text-gray-500 dark:text-gray-400">Power 4 W%</div>
									<div class="font-medium text-gray-900 dark:text-white">
										{(conf.power_win_pct * 100).toFixed(0)}%
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Desktop Table View -->
		<div class="hidden sm:block card overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="bg-gray-50 dark:bg-gray-700/50 text-left text-xs font-medium 
							text-gray-500 dark:text-gray-400 uppercase tracking-wider">
							<th class="px-4 py-3 w-16">#</th>
							<th class="px-4 py-3">Conference</th>
							<th class="px-4 py-3 text-right">Avg Rank</th>
							<th class="px-4 py-3 text-right">Teams</th>
							<th class="px-4 py-3 text-right">Ranked Teams</th>
							<th class="px-4 py-3 text-right">Power 4 W%</th>
							<th class="px-4 py-3 text-right">G5 W%</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each sortedConferences as conf, index}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
								<td class="px-4 py-3">
									<span class="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/50 
										text-primary-600 dark:text-primary-400 flex items-center justify-center 
										text-sm font-bold">
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
									{#if conf.ranked_teams > 0}
										<span class="inline-flex items-center px-2 py-0.5 rounded text-xs 
											font-medium bg-green-100 text-green-800 dark:bg-green-900/50 
											dark:text-green-400">
											{conf.ranked_teams}
										</span>
									{:else}
										<span class="text-gray-400 dark:text-gray-500">0</span>
									{/if}
								</td>
								<td class="px-4 py-3 text-right">
									<span class="{conf.power_win_pct >= 0.5 
										? 'text-green-600 dark:text-green-400' 
										: 'text-gray-600 dark:text-gray-400'}">
										{(conf.power_win_pct * 100).toFixed(0)}%
									</span>
								</td>
								<td class="px-4 py-3 text-right">
									<span class="{conf.g5_win_pct >= 0.5 
										? 'text-green-600 dark:text-green-400' 
										: 'text-gray-600 dark:text-gray-400'}">
										{(conf.g5_win_pct * 100).toFixed(0)}%
									</span>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
