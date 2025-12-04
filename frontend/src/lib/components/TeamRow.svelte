<script lang="ts">
	import type { Team } from '$lib/types';
	import { createEventDispatcher } from 'svelte';

	export let team: Team;
	export let rank: number;
	export let cfpClass: string = '';

	const dispatch = createEventDispatcher();

	function handleClick() {
		dispatch('click');
	}

	function getRankClass(r: number): string {
		if (r <= 12) return 'rank-cfp';
		if (r <= 25) return 'rank-bubble';
		return 'rank-other';
	}

	function getConfClass(type: string): string {
		if (type === 'Power 4') return 'badge-power4';
		if (type === 'Group of 5') return 'badge-g5';
		return 'badge-ind';
	}
	
	function getRowBgClass(): string {
		if (cfpClass === 'cfp-in') {
			return 'bg-yellow-50 dark:bg-yellow-900/20 hover:bg-yellow-100 dark:hover:bg-yellow-900/30';
		}
		if (cfpClass === 'cfp-bubble') {
			return 'bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-700/50';
		}
		return 'hover:bg-gray-50 dark:hover:bg-gray-700/50';
	}
</script>

<tr
	on:click={handleClick}
	class="{getRowBgClass()} cursor-pointer transition-colors"
>
	<td class="px-4 py-3">
		<span class="rank-badge {getRankClass(rank)}">
			{rank}
		</span>
	</td>
	<td class="px-4 py-3">
		<div class="flex items-center gap-2">
			{#if team.logo}
				<img 
					src={team.logo} 
					alt="{team.team_name} logo" 
					class="w-6 h-6 object-contain"
					loading="lazy"
				/>
			{:else}
				<div 
					class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
					style="background-color: {team.color || '#6b7280'}"
				>
					{team.team_name.charAt(0)}
				</div>
			{/if}
			<span class="font-semibold text-gray-900 dark:text-white">
				{team.team_name}
			</span>
		</div>
	</td>
	<td class="px-4 py-3">
		<span class="badge {getConfClass(team.conference_type || '')}">
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
