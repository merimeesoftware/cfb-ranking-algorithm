<script lang="ts">
	import type { Team } from '$lib/types';
	import { createEventDispatcher } from 'svelte';

	export let team: Team;
	export let rank: number;

	const dispatch = createEventDispatcher();

	function handleClick() {
		dispatch('click');
	}

	function getRankClass(r: number): string {
		if (r <= 4) return 'rank-top5';
		if (r <= 10) return 'rank-top10';
		if (r <= 25) return 'rank-top25';
		return 'rank-other';
	}

	function getConfClass(type: string): string {
		if (type === 'Power 4') return 'badge-power4';
		if (type === 'Group of 5') return 'badge-g5';
		return 'badge-ind';
	}
</script>

<tr
	on:click={handleClick}
	class="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
>
	<td class="px-4 py-3">
		<span class="rank-badge {getRankClass(rank)}">
			{rank}
		</span>
	</td>
	<td class="px-4 py-3">
		<span class="font-semibold text-gray-900 dark:text-white">
			{team.team_name}
		</span>
	</td>
	<td class="px-4 py-3">
		<span class="badge {getConfClass(team.conference_type)}">
			{team.conference}
		</span>
	</td>
	<td class="px-4 py-3 text-center text-gray-700 dark:text-gray-300">
		{team.records.total_wins}-{team.records.total_losses}
	</td>
	<td class="px-4 py-3 text-center font-medium text-gray-700 dark:text-gray-300">
		{team.team_quality_score.toFixed(1)}
	</td>
	<td class="px-4 py-3 text-center font-medium text-gray-700 dark:text-gray-300">
		{team.record_score.toFixed(1)}
	</td>
	<td class="px-4 py-3 text-center font-medium text-gray-700 dark:text-gray-300">
		{team.conference_quality_score.toFixed(1)}
	</td>
	<td class="px-4 py-3 text-right">
		<span class="font-bold text-primary-600 dark:text-primary-400">
			{team.final_ranking_score.toFixed(2)}
		</span>
	</td>
</tr>
