<script lang="ts">
	import type { Team } from '$lib/types';
	import TeamRow from './TeamRow.svelte';
	import TeamDetailModal from './TeamDetailModal.svelte';

	export let teams: Team[] = [];

	let selectedTeam: Team | null = null;
	let showModal = false;

	function handleTeamClick(team: Team) {
		selectedTeam = team;
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		selectedTeam = null;
	}
</script>

<div class="card overflow-hidden">
	<!-- Mobile Card View -->
	<div class="sm:hidden">
		{#each teams as team, index}
			<button
				on:click={() => handleTeamClick(team)}
				class="w-full text-left p-4 border-b border-gray-100 dark:border-gray-700 last:border-0
					hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
			>
				<div class="flex items-center gap-3">
					<!-- Rank -->
					<div class="rank-badge {index < 4 ? 'rank-top5' : index < 10 ? 'rank-top10' : index < 25 ? 'rank-top25' : 'rank-other'}">
						{index + 1}
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
				{#each teams as team, index}
					<TeamRow {team} rank={index + 1} on:click={() => handleTeamClick(team)} />
				{/each}
			</tbody>
		</table>
	</div>
</div>

<!-- Team Detail Modal -->
{#if showModal && selectedTeam}
	<TeamDetailModal team={selectedTeam} rank={teams.indexOf(selectedTeam) + 1} on:close={closeModal} />
{/if}
