<script lang="ts">
	import type { Team } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { fade, fly } from 'svelte/transition';

	export let team: Team;
	export let rank: number;
	export let allTeams: Team[] = [];

	const dispatch = createEventDispatcher();

	function close() {
		dispatch('close');
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			close();
		}
	}

	// Score breakdown calculations
	$: tqContrib = team.team_quality_score * 0.55;
	$: recContrib = team.record_score * 0.35;
	$: confContrib = team.conference_quality_score * 0.10;

	// Get teams ahead and behind for comparison
	$: teamsAhead = allTeams
		.filter((_, i) => i < rank - 1 && i >= Math.max(0, rank - 4))
		.map((t, i) => ({ team: t, rank: rank - (rank - 1 - Math.max(0, rank - 4) - i) }))
		.reverse();
	
	$: teamsBehind = allTeams
		.filter((_, i) => i > rank - 1 && i <= rank + 2)
		.map((t, i) => ({ team: t, rank: rank + 1 + i }));

	// Calculate component contributions for any team
	function getContribs(t: Team) {
		return {
			tq: t.team_quality_score * 0.55,
			rec: t.record_score * 0.35,
			conf: t.conference_quality_score * 0.10
		};
	}

	// Calculate differences between selected team and comparison team
	function getDiff(compTeam: Team, isAhead: boolean) {
		const myContribs = getContribs(team);
		const theirContribs = getContribs(compTeam);
		
		// If they're ahead, show what they have MORE of
		// If they're behind, show what we have MORE of
		if (isAhead) {
			return {
				tq: theirContribs.tq - myContribs.tq,
				rec: theirContribs.rec - myContribs.rec,
				conf: theirContribs.conf - myContribs.conf,
				total: compTeam.final_ranking_score - team.final_ranking_score
			};
		} else {
			return {
				tq: myContribs.tq - theirContribs.tq,
				rec: myContribs.rec - theirContribs.rec,
				conf: myContribs.conf - theirContribs.conf,
				total: team.final_ranking_score - compTeam.final_ranking_score
			};
		}
	}

	function formatDiff(val: number): string {
		if (val > 0) return `+${val.toFixed(1)}`;
		return val.toFixed(1);
	}

	function getDiffClass(val: number, isPositiveGood: boolean): string {
		if (Math.abs(val) < 0.5) return 'text-gray-500';
		if (isPositiveGood) {
			return val > 0 ? 'text-green-500' : 'text-red-500';
		} else {
			return val < 0 ? 'text-green-500' : 'text-red-500';
		}
	}
</script>

<svelte:window on:keydown={(e) => e.key === 'Escape' && close()} />

<!-- Backdrop -->
<div
	transition:fade={{ duration: 200 }}
	on:click={handleBackdropClick}
	on:keydown={(e) => e.key === 'Escape' && close()}
	role="button"
	tabindex="0"
	class="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
>
	<!-- Modal -->
	<div
		transition:fly={{ y: 100, duration: 300 }}
		class="bg-white dark:bg-gray-800 w-full sm:max-w-lg sm:rounded-xl rounded-t-xl 
			max-h-[90vh] overflow-hidden flex flex-col"
	>
		<!-- Header -->
		<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-3">
				<span class="rank-badge {rank <= 4 ? 'rank-top5' : rank <= 10 ? 'rank-top10' : 'rank-top25'}">
					{rank}
				</span>
				<div>
					<h2 class="font-bold text-lg text-gray-900 dark:text-white">{team.team_name}</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400">{team.conference}</p>
				</div>
			</div>
			<button
				on:click={close}
				class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
			>
				<svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-4 space-y-4">
			<!-- Record Summary -->
			<div class="grid grid-cols-3 gap-3">
				<div class="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
					<div class="text-2xl font-bold text-gray-900 dark:text-white">
						{team.records.total_wins}-{team.records.total_losses}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Overall</div>
				</div>
				<div class="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
					<div class="text-2xl font-bold text-gray-900 dark:text-white">
						{team.records.conf_wins}-{team.records.conf_losses}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Conference</div>
				</div>
				<div class="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
					<div class="text-2xl font-bold text-primary-600 dark:text-primary-400">
						{team.final_ranking_score.toFixed(1)}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Final Score</div>
				</div>
			</div>

			<!-- Score Breakdown -->
			<div class="card p-4">
				<h3 class="font-semibold text-gray-900 dark:text-white mb-3">Score Breakdown</h3>
				
				<div class="space-y-3">
					<!-- Team Quality -->
					<div>
						<div class="flex justify-between text-sm mb-1">
							<span class="text-gray-600 dark:text-gray-400">Team Quality (55%)</span>
							<span class="font-medium text-gray-900 dark:text-white">
								{team.team_quality_score.toFixed(1)} × 0.55 = {tqContrib.toFixed(1)}
							</span>
						</div>
						<div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
							<div 
								class="h-full bg-blue-500 rounded-full" 
								style="width: {Math.min((tqContrib / team.final_ranking_score) * 100, 100)}%"
							></div>
						</div>
					</div>

					<!-- Record Score -->
					<div>
						<div class="flex justify-between text-sm mb-1">
							<span class="text-gray-600 dark:text-gray-400">Resume (35%)</span>
							<span class="font-medium text-gray-900 dark:text-white">
								{team.record_score.toFixed(1)} × 0.35 = {recContrib.toFixed(1)}
							</span>
						</div>
						<div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
							<div 
								class="h-full bg-green-500 rounded-full" 
								style="width: {Math.min((recContrib / team.final_ranking_score) * 100, 100)}%"
							></div>
						</div>
					</div>

					<!-- Conference Quality -->
					<div>
						<div class="flex justify-between text-sm mb-1">
							<span class="text-gray-600 dark:text-gray-400">Conf Quality (10%)</span>
							<span class="font-medium text-gray-900 dark:text-white">
								{team.conference_quality_score.toFixed(1)} × 0.10 = {confContrib.toFixed(1)}
							</span>
						</div>
						<div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
							<div 
								class="h-full bg-purple-500 rounded-full" 
								style="width: {Math.min((confContrib / team.final_ranking_score) * 100, 100)}%"
							></div>
						</div>
					</div>
				</div>

				<div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 flex justify-between">
					<span class="font-semibold text-gray-900 dark:text-white">Total</span>
					<span class="font-bold text-primary-600 dark:text-primary-400">
						{team.final_ranking_score.toFixed(2)}
					</span>
				</div>
			</div>

			<!-- Strength Metrics -->
			<div class="grid grid-cols-2 gap-3">
				<div class="card p-4 text-center">
					<div class="text-2xl font-bold text-gray-900 dark:text-white">
						{team.sos?.toFixed(0) ?? 'N/A'}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Strength of Schedule
					</div>
					<div class="text-xs text-gray-400 dark:text-gray-500">
						(Avg Opponent Elo)
					</div>
				</div>
				<div class="card p-4 text-center">
					<div class="text-2xl font-bold text-gray-900 dark:text-white">
						{team.sov?.toFixed(0) ?? 'N/A'}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Strength of Victory
					</div>
					<div class="text-xs text-gray-400 dark:text-gray-500">
						(Avg Win Elo)
					</div>
				</div>
			</div>

			<!-- Record Breakdown -->
			<div class="card p-4">
				<h3 class="font-semibold text-gray-900 dark:text-white mb-3">Record Breakdown</h3>
				<div class="grid grid-cols-2 gap-3 text-sm">
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">vs Power 4</span>
						<span class="font-medium text-gray-900 dark:text-white">
							{team.records.power_wins}-{team.records.power_losses}
						</span>
					</div>
					<div class="flex justify-between">
						<span class="text-gray-600 dark:text-gray-400">vs Group of 5</span>
						<span class="font-medium text-gray-900 dark:text-white">
							{team.records.group_five_wins}-{team.records.group_five_losses}
						</span>
					</div>
				</div>
			</div>

			<!-- Ranking Comparison Section -->
			{#if teamsAhead.length > 0 || teamsBehind.length > 0}
				<div class="card p-4">
					<h3 class="font-semibold text-gray-900 dark:text-white mb-3">Ranking Comparison</h3>
					
					<!-- Teams Ahead -->
					{#if teamsAhead.length > 0}
						<div class="mb-4">
							<h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
								Why teams are ranked ahead
							</h4>
							<div class="space-y-2">
								{#each teamsAhead as { team: compTeam, rank: compRank }}
									{@const diff = getDiff(compTeam, true)}
									<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
										<div class="flex items-center justify-between mb-2">
											<div class="flex items-center gap-2">
												<span class="text-xs font-bold text-gray-500 dark:text-gray-400">#{compRank}</span>
												<span class="font-medium text-gray-900 dark:text-white text-sm">{compTeam.team_name}</span>
											</div>
											<span class="text-xs text-gray-500">
												{compTeam.final_ranking_score.toFixed(1)} ({formatDiff(diff.total)})
											</span>
										</div>
										<div class="grid grid-cols-3 gap-2 text-xs">
											<div class="text-center">
												<div class="text-gray-500 dark:text-gray-400">Team Quality</div>
												<div class={getDiffClass(diff.tq, false)}>{formatDiff(diff.tq)}</div>
											</div>
											<div class="text-center">
												<div class="text-gray-500 dark:text-gray-400">Resume</div>
												<div class={getDiffClass(diff.rec, false)}>{formatDiff(diff.rec)}</div>
											</div>
											<div class="text-center">
												<div class="text-gray-500 dark:text-gray-400">Conf</div>
												<div class={getDiffClass(diff.conf, false)}>{formatDiff(diff.conf)}</div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Teams Behind -->
					{#if teamsBehind.length > 0}
						<div>
							<h4 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
								Why {team.team_name} is ahead of
							</h4>
							<div class="space-y-2">
								{#each teamsBehind as { team: compTeam, rank: compRank }}
									{@const diff = getDiff(compTeam, false)}
									<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
										<div class="flex items-center justify-between mb-2">
											<div class="flex items-center gap-2">
												<span class="text-xs font-bold text-gray-500 dark:text-gray-400">#{compRank}</span>
												<span class="font-medium text-gray-900 dark:text-white text-sm">{compTeam.team_name}</span>
											</div>
											<span class="text-xs text-gray-500">
												{compTeam.final_ranking_score.toFixed(1)} ({formatDiff(-diff.total)})
											</span>
										</div>
										<div class="grid grid-cols-3 gap-2 text-xs">
											<div class="text-center">
												<div class="text-gray-500 dark:text-gray-400">Team Quality</div>
												<div class={getDiffClass(diff.tq, true)}>{formatDiff(diff.tq)}</div>
											</div>
											<div class="text-center">
												<div class="text-gray-500 dark:text-gray-400">Resume</div>
												<div class={getDiffClass(diff.rec, true)}>{formatDiff(diff.rec)}</div>
											</div>
											<div class="text-center">
												<div class="text-gray-500 dark:text-gray-400">Conf</div>
												<div class={getDiffClass(diff.conf, true)}>{formatDiff(diff.conf)}</div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
