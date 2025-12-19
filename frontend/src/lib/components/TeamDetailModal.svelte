<script lang="ts">
	import type { Team, WinDetail, LossDetail } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import { fade, fly, slide } from 'svelte/transition';

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

	// Score breakdown calculations (V5.0 weights: 65/27/8)
	$: tqContrib = team.team_quality_score * 0.65;
	$: recContrib = team.record_score * 0.27;
	$: confContrib = team.conference_quality_score * 0.08;

	// Get teams ahead and behind for comparison
	$: teamsAhead = allTeams
		.filter((_, i) => i < rank - 1 && i >= Math.max(0, rank - 4))
		.map((t, i) => ({ team: t, rank: rank - (rank - 1 - Math.max(0, rank - 4) - i) }))
		.reverse();
	
	$: teamsBehind = allTeams
		.filter((_, i) => i > rank - 1 && i <= rank + 2)
		.map((t, i) => ({ team: t, rank: rank + 1 + i }));

	// Calculate component contributions for any team (V5.0 weights)
	function getContribs(t: Team) {
		return {
			tq: t.team_quality_score * 0.65,
			rec: t.record_score * 0.27,
			conf: t.conference_quality_score * 0.08
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

	// Narrative Generation
	function generateNarrative(t: Team): string {
		const parts = [];
		
		// Record Context
		if (t.records.total_losses === 0) parts.push("Undefeated season");
		else if (t.records.total_losses === 1) parts.push("One-loss season");
		
		// Strength Context
		if ((t.sos ?? 0) > 1600) parts.push("played a brutal schedule");
		else if ((t.sos ?? 0) > 1500) parts.push("played a tough schedule");
		else if ((t.sos ?? 0) < 1350) parts.push("played a relatively weak schedule");

		// Key Wins/Losses
		if ((t.top_10_wins ?? 0) > 0) parts.push(`boasts ${t.top_10_wins} top-10 win${t.top_10_wins === 1 ? '' : 's'}`);
		if ((t.bad_losses ?? 0) > 0) parts.push(`suffered ${t.bad_losses} bad loss${t.bad_losses === 1 ? '' : 'es'}`);

		if (parts.length === 0) return "Solid performance throughout the season.";
		return parts.join(", ") + ".";
	}

	// Accordion State
	let expandedSection: string | null = null;
	function toggleSection(section: string) {
		expandedSection = expandedSection === section ? null : section;
	}

	// Timeline Data
	$: timelineEvents = [
		...(team.wins_details || []).map(w => ({ ...w, type: 'win', date: 0 })), // We don't have dates, but order matters? 
		// Actually, we don't have dates in the API response yet, but the arrays are likely in chronological order if the backend preserves it.
		// The backend appends to the list as games are processed.
		...(team.losses_details || []).map(l => ({ ...l, type: 'loss', date: 0 }))
	]; 
	// Merging and sorting isn't possible without dates or week numbers. 
	// For now, let's just list Key Games (Quality Wins & Bad Losses) separately or assume we can't do a true timeline yet.
	// Wait, the backend `wins_details` and `losses_details` are just lists.
	// Let's just show "Key Games" instead of a timeline for now, or list them by category.

	// Filter for "Key Games" - use is_quality_win and is_bad_loss flags from backend
	$: keyWins = (team.wins_details || []).filter(w => w.is_quality_win);
	$: badLosses = (team.losses_details || []).filter(l => l.is_bad_loss);
	
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
		class="bg-white dark:bg-gray-800 w-full sm:max-w-2xl sm:rounded-xl rounded-t-xl 
			max-h-[90vh] overflow-hidden flex flex-col shadow-2xl"
	>
		<!-- Header -->
		<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
			<div class="flex items-center gap-4">
				<span class="rank-badge text-xl w-12 h-12 flex items-center justify-center {rank <= 4 ? 'rank-top5' : rank <= 10 ? 'rank-top10' : 'rank-top25'}">
					{rank}
				</span>
				<div>
					<h2 class="font-bold text-2xl text-gray-900 dark:text-white leading-tight">{team.team_name}</h2>
					<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
						<span>{team.conference}</span>
						<span>•</span>
						<span>{team.records.total_wins}-{team.records.total_losses}</span>
					</div>
				</div>
			</div>
			<button
				on:click={close}
				class="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
			>
				<svg class="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-0">
			
			<!-- Narrative Summary -->
			<div class="p-6 bg-gradient-to-b from-gray-50 to-white dark:from-gray-800/50 dark:to-gray-800 border-b border-gray-100 dark:border-gray-700">
				<p class="text-gray-700 dark:text-gray-300 italic text-lg leading-relaxed">
					"{generateNarrative(team)}"
				</p>
			</div>

			<div class="p-6 space-y-6">
				<!-- Score Breakdown -->
				<div>
					<h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-3">Ranking Components</h3>
					<div class="space-y-4">
						<!-- Team Quality -->
						<div>
							<div class="flex justify-between text-sm mb-1">
								<div class="flex items-center gap-2">
									<span class="font-medium text-gray-700 dark:text-gray-300">Team Quality</span>
								<span class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">65%</span>
								</div>
								<span class="font-mono text-gray-900 dark:text-white">
									{team.team_quality_score.toFixed(1)} <span class="text-gray-400">→</span> {tqContrib.toFixed(1)}
								</span>
							</div>
							<div class="h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
								<div 
									class="h-full bg-blue-500 rounded-full" 
									style="width: {Math.min((tqContrib / team.final_ranking_score) * 100, 100)}%"
								></div>
							</div>
							<p class="text-xs text-gray-500 mt-1">Elo-based power rating. Measures pure team strength.</p>
						</div>

						<!-- Record Score -->
						<div>
							<div class="flex justify-between text-sm mb-1">
								<div class="flex items-center gap-2">
									<span class="font-medium text-gray-700 dark:text-gray-300">Resume</span>
								<span class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">27%</span>
								</div>
								<span class="font-mono text-gray-900 dark:text-white">
									{team.record_score.toFixed(1)} <span class="text-gray-400">→</span> {recContrib.toFixed(1)}
								</span>
							</div>
							<div class="h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
								<div 
									class="h-full bg-green-500 rounded-full" 
									style="width: {Math.min((recContrib / team.final_ranking_score) * 100, 100)}%"
								></div>
							</div>
							<p class="text-xs text-gray-500 mt-1">Rewards accomplishments: wins, SoS, and quality victories.</p>
						</div>

						<!-- Conference Quality -->
						<div>
							<div class="flex justify-between text-sm mb-1">
								<div class="flex items-center gap-2">
									<span class="font-medium text-gray-700 dark:text-gray-300">Conference</span>
								<span class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">8%</span>
								</div>
								<span class="font-mono text-gray-900 dark:text-white">
									{team.conference_quality_score.toFixed(1)} <span class="text-gray-400">→</span> {confContrib.toFixed(1)}
								</span>
							</div>
							<div class="h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
								<div 
									class="h-full bg-purple-500 rounded-full" 
									style="width: {Math.min((confContrib / team.final_ranking_score) * 100, 100)}%"
								></div>
							</div>
						</div>
					</div>
					
					<div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
						<span class="font-bold text-gray-900 dark:text-white">Total Score</span>
						<span class="text-2xl font-bold text-primary-600 dark:text-primary-400">
							{team.final_ranking_score.toFixed(2)}
						</span>
					</div>
				</div>

				<!-- Resume Deep Dive (Accordion) -->
				<div class="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
					<!-- Quality Wins Header -->
					<button 
						class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
						on:click={() => toggleSection('wins')}
					>
						<div class="flex items-center gap-3">
							<div class="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600 dark:text-green-400 font-bold">
								{team.quality_wins ?? 0}
							</div>
							<div class="text-left">
								<div class="font-semibold text-gray-900 dark:text-white">Quality Wins</div>
								<div class="text-xs text-gray-500">vs Top 25 or Elite Opponents</div>
							</div>
						</div>
						<svg class="w-5 h-5 text-gray-400 transform transition-transform {expandedSection === 'wins' ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
					</button>
					
					{#if expandedSection === 'wins'}
						<div transition:slide class="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
							{#if (team.wins_details || []).filter(w => w.is_quality_win).length > 0}
								<div class="space-y-2">
									{#each (team.wins_details || []).filter(w => w.is_quality_win).sort((a,b) => b.opponent_elo - a.opponent_elo) as win}
										<div class="flex items-center justify-between text-sm p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700/50">
											<div class="flex items-center gap-2">
												<span class="font-bold text-gray-900 dark:text-white">
													{win.opponent_rank <= 25 ? `#${win.opponent_rank}` : ''} {win.opponent}
												</span>
												<span class="text-xs text-gray-500">({win.opponent_elo.toFixed(0)} Elo)</span>
											</div>
											<div class="flex items-center gap-3">
												<span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
													{win.is_road ? 'Away' : 'Home'}
												</span>
												<span class="font-mono font-medium text-green-600">+{win.mov}</span>
											</div>
										</div>
									{/each}
								</div>
							{:else}
								<p class="text-sm text-gray-500 italic text-center py-2">No quality wins recorded.</p>
							{/if}
						</div>
					{/if}

					<!-- Bad Losses Header -->
					<button 
						class="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-t border-gray-200 dark:border-gray-700"
						on:click={() => toggleSection('losses')}
					>
						<div class="flex items-center gap-3">
							<div class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center text-red-600 dark:text-red-400 font-bold">
								{team.bad_losses ?? 0}
							</div>
							<div class="text-left">
								<div class="font-semibold text-gray-900 dark:text-white">Bad Losses</div>
								<div class="text-xs text-gray-500">vs Inferior Opponents</div>
							</div>
						</div>
						<svg class="w-5 h-5 text-gray-400 transform transition-transform {expandedSection === 'losses' ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
					</button>

					{#if expandedSection === 'losses'}
						<div transition:slide class="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
							{#if (team.losses_details || []).filter(l => l.is_bad_loss).length > 0}
								<div class="space-y-2">
									{#each (team.losses_details || []).filter(l => l.is_bad_loss).sort((a,b) => a.opponent_elo - b.opponent_elo) as loss}
										<div class="flex items-center justify-between text-sm p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700/50">
											<div class="flex items-center gap-2">
												<span class="font-bold text-gray-900 dark:text-white">
													{loss.opponent_rank <= 136 ? `#${loss.opponent_rank}` : ''} {loss.opponent}
												</span>
												<span class="text-xs text-gray-500">({loss.opponent_elo.toFixed(0)} Elo)</span>
											</div>
											<div class="flex items-center gap-3">
												<span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
													{loss.is_home ? 'Home' : 'Away'}
												</span>
												<span class="font-mono font-medium text-red-600">-{Math.abs(loss.mov)}</span>
											</div>
										</div>
									{/each}
								</div>
							{:else}
								<p class="text-sm text-gray-500 italic text-center py-2">No bad losses recorded.</p>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Strength Metrics -->
				<div class="grid grid-cols-2 gap-4">
					<div class="card p-4 text-center bg-gray-50 dark:bg-gray-800 border-none">
						<div class="text-3xl font-bold text-gray-900 dark:text-white">
							{team.sos?.toFixed(0) ?? 'N/A'}
						</div>
						<div class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mt-1">
							Strength of Schedule
						</div>
					</div>
					<div class="card p-4 text-center bg-gray-50 dark:bg-gray-800 border-none">
						<div class="text-3xl font-bold text-gray-900 dark:text-white">
							{team.sov?.toFixed(0) ?? 'N/A'}
						</div>
						<div class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide mt-1">
							Strength of Victory
						</div>
					</div>
				</div>

				<!-- Ranking Comparison Section -->
				{#if teamsAhead.length > 0 || teamsBehind.length > 0}
					<div>
						<h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-3">Context</h3>
						
						<!-- Teams Ahead -->
						{#if teamsAhead.length > 0}
							<div class="mb-4">
								<h4 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase">
									Chasing
								</h4>
								<div class="space-y-2">
									{#each teamsAhead as { team: compTeam, rank: compRank }}
										{@const diff = getDiff(compTeam, true)}
										<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3">
											<div class="flex items-center justify-between mb-2">
												<div class="flex items-center gap-2">
													<span class="text-xs font-bold text-gray-500 dark:text-gray-400">#{compRank}</span>
													<span class="font-medium text-gray-900 dark:text-white text-sm">{compTeam.team_name}</span>
												</div>
												<span class="text-xs font-mono text-gray-500">
													{formatDiff(diff.total)} pts ahead
												</span>
											</div>
											<div class="grid grid-cols-3 gap-2 text-xs">
												<div class="text-center">
													<div class="text-gray-400 mb-0.5">Quality</div>
													<div class={getDiffClass(diff.tq, false)}>{formatDiff(diff.tq)}</div>
												</div>
												<div class="text-center">
													<div class="text-gray-400 mb-0.5">Resume</div>
													<div class={getDiffClass(diff.rec, false)}>{formatDiff(diff.rec)}</div>
												</div>
												<div class="text-center">
													<div class="text-gray-400 mb-0.5">Conf</div>
													<div class={getDiffClass(diff.conf, false)}>{formatDiff(diff.conf)}</div>
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
</div>