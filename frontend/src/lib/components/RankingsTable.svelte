<script lang="ts">
	import type { Team } from '$lib/types';
	import TeamRow from './TeamRow.svelte';
	import TeamDetailModal from './TeamDetailModal.svelte';

	export let teams: Team[] = [];

	let selectedTeam: Team | null = null;
	let showModal = false;
	let showAllTeams = false;

	// Display top 25 by default, or all if expanded
	$: displayedTeams = showAllTeams ? teams : teams.slice(0, 25);
	
	// CFP playoff spots (first 12 get highlighted)
	const CFP_CUTOFF = 12;

	function handleTeamClick(team: Team) {
		selectedTeam = team;
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		selectedTeam = null;
	}
	
	function getCfpClass(rank: number): string {
		if (rank <= CFP_CUTOFF) return 'cfp-in';
		if (rank <= 25) return 'cfp-bubble';
		return '';
	}
</script>

<div class="card overflow-hidden">
	<!-- Header with CFP Legend -->
	<div class="bg-gray-50 dark:bg-gray-800 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h3 class="font-semibold text-gray-900 dark:text-white">
				{showAllTeams ? 'All Teams' : 'Top 25 Teams'}
			</h3>
			<div class="flex items-center gap-4 text-xs sm:text-sm">
				<div class="flex items-center gap-2">
					<span class="inline-block w-3 h-3 rounded-sm bg-yellow-100 dark:bg-yellow-900/50 border border-yellow-300 dark:border-yellow-700"></span>
					<span class="text-gray-600 dark:text-gray-400">CFP Playoff (1-12)</span>
				</div>
				<div class="flex items-center gap-2">
					<span class="inline-block w-3 h-3 rounded-sm bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600"></span>
					<span class="text-gray-600 dark:text-gray-400">On the Bubble (13-25)</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Mobile Card View -->
	<div class="sm:hidden">
		{#each displayedTeams as team, index}
			{@const rank = index + 1}
			<button
				on:click={() => handleTeamClick(team)}
				class="w-full text-left p-4 border-b border-gray-100 dark:border-gray-700 last:border-0
					hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors
					{rank <= CFP_CUTOFF ? 'bg-yellow-50 dark:bg-yellow-900/20' : ''}"
			>
				<div class="flex items-center gap-3">
					<!-- Rank -->
					<div class="rank-badge {rank <= CFP_CUTOFF ? 'rank-cfp' : rank <= 25 ? 'rank-bubble' : 'rank-other'}">
						{rank}
					</div>

					<!-- Team Info -->
					<div class="flex-1 min-w-0">
						<div class="font-semibold text-gray-900 dark:text-white truncate">
							{team.team_name}
						</div>
						<div class="flex items-center gap-2 mt-0.5">
							<span class="badge {team.conference_type === 'Power 4' ? 'badge-power4' : team.conference_type === 'Group of 5' ? 'badge-g5' : 'badge-ind'}">
								{team.conference}
							</span>
							<span class="text-sm text-gray-500 dark:text-gray-400">
								{team.records.total_wins}-{team.records.total_losses}
							</span>
						</div>
					</div>

					<!-- Score -->
					<div class="text-right">
						<div class="font-bold text-lg text-primary-600 dark:text-primary-400">
							{team.final_ranking_score.toFixed(1)}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							Score
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
				<tr class="bg-gray-50 dark:bg-gray-700/50">
					<th class="table-header px-4 py-3 text-left w-16">Rank</th>
					<th class="table-header px-4 py-3 text-left">Team</th>
					<th class="table-header px-4 py-3 text-left">Conference</th>
					<th class="table-header px-4 py-3 text-center">Record</th>
					<th class="table-header px-4 py-3 text-center">Team Elo</th>
					<th class="table-header px-4 py-3 text-center">Resume</th>
					<th class="table-header px-4 py-3 text-center">Conf Qual</th>
					<th class="table-header px-4 py-3 text-right">Score</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-100 dark:divide-gray-700">
				{#each displayedTeams as team, index}
					{@const rank = index + 1}
					<TeamRow 
						{team} 
						{rank} 
						cfpClass={getCfpClass(rank)}
						on:click={() => handleTeamClick(team)} 
					/>
				{/each}
			</tbody>
		</table>
	</div>
	
	<!-- Show More / Show Less Button -->
	{#if teams.length > 25}
		<div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
			<button
				on:click={() => showAllTeams = !showAllTeams}
				class="w-full text-center text-sm font-medium text-primary-600 dark:text-primary-400 
					hover:text-primary-800 dark:hover:text-primary-300 transition-colors
					flex items-center justify-center gap-2"
			>
				{#if showAllTeams}
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
					</svg>
					Show Top 25 Only
				{:else}
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
					</svg>
					View All {teams.length} Teams
				{/if}
			</button>
		</div>
	{/if}
</div>

<!-- Team Detail Modal -->
{#if showModal && selectedTeam}
	<TeamDetailModal team={selectedTeam} rank={teams.indexOf(selectedTeam) + 1} on:close={closeModal} />
{/if}
