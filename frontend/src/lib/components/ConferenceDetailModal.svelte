<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Conference, Team } from '$lib/types';

	export let conference: Conference;
	export let rank: number;
	export let allConferences: Conference[] = [];
	export let allTeams: Team[] = [];

	const dispatch = createEventDispatcher();

	// Get conferences ahead and behind
	$: sortedConferences = [...allConferences].sort((a, b) => b.avg_ranking - a.avg_ranking);
	$: currentIndex = sortedConferences.findIndex(c => c.conference === conference.conference);
	
	$: conferencesAhead = currentIndex > 0 
		? sortedConferences.slice(Math.max(0, currentIndex - 3), currentIndex).reverse()
		: [];
	
	$: conferencesBehind = currentIndex < sortedConferences.length - 1
		? sortedConferences.slice(currentIndex + 1, currentIndex + 4)
		: [];

	// Get teams in this conference
	$: conferenceTeams = allTeams
		.filter(t => t.conference === conference.conference)
		.sort((a, b) => b.final_ranking_score - a.final_ranking_score);

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

	function getDiff(current: Conference, other: Conference): number {
		return current.avg_ranking - other.avg_ranking;
	}

	function formatDiff(diff: number): string {
		const sign = diff > 0 ? '+' : '';
		return sign + diff.toFixed(1);
	}

	function getDiffClass(diff: number): string {
		if (diff > 0) return 'text-green-600 dark:text-green-400';
		if (diff < 0) return 'text-red-600 dark:text-red-400';
		return 'text-gray-500 dark:text-gray-400';
	}

	function getTeamRank(team: Team): number {
		return allTeams.findIndex(t => t.team_name === team.team_name) + 1;
	}

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			close();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- Modal Backdrop -->
<div
	class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
	on:click={handleBackdropClick}
	role="dialog"
	aria-modal="true"
	aria-labelledby="modal-title"
>
	<!-- Modal Content -->
	<div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden animate-in fade-in zoom-in duration-200">
		<!-- Header with conference color accent -->
		<div 
			class="px-6 py-4 border-b border-gray-200 dark:border-gray-700"
			style="background: linear-gradient(135deg, {getConferenceColor(conference.conference)}15, transparent)"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<span 
						class="w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold text-white shadow-lg"
						style="background-color: {getConferenceColor(conference.conference)}"
					>
						{rank}
					</span>
					<div>
						<h2 id="modal-title" class="text-xl font-bold text-gray-900 dark:text-white">
							{conference.conference}
						</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							Avg Ranking Score: <span class="font-semibold text-gray-900 dark:text-white">{conference.avg_ranking.toFixed(2)}</span>
						</p>
					</div>
				</div>
				<button
					on:click={close}
					class="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					aria-label="Close modal"
				>
					<svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Scrollable Content -->
		<div class="overflow-y-auto max-h-[calc(90vh-80px)]">
			<!-- Conference Stats -->
			<div class="p-6 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
					Conference Performance
				</h3>
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
					<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
						<div class="text-2xl font-bold text-gray-900 dark:text-white">{conference.team_count}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">Teams</div>
					</div>
					<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
						<div class="text-2xl font-bold {conference.power_win_pct >= 0.5 ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-white'}">
							{formatWinPct(conference.power_win_pct)}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">vs Power 4</div>
					</div>
					<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
						<div class="text-2xl font-bold {conference.g5_win_pct >= 0.5 ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-white'}">
							{formatWinPct(conference.g5_win_pct)}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">vs Group of 5</div>
					</div>
					<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
						<div class="text-2xl font-bold text-gray-900 dark:text-white">{formatFcsWinPct(conference)}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">vs FCS</div>
					</div>
				</div>
			</div>

			<!-- Conference Teams -->
			<div class="p-6 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
					Conference Teams ({conferenceTeams.length})
				</h3>
				<div class="space-y-2 max-h-48 overflow-y-auto">
					{#each conferenceTeams as team}
						{@const teamRank = getTeamRank(team)}
						<div class="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/30">
							<div class="flex items-center gap-3">
								<span class="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/50 
									text-primary-600 dark:text-primary-400 flex items-center justify-center 
									text-sm font-bold">
									{teamRank}
								</span>
								{#if team.logo}
									<img src={team.logo} alt="{team.team_name} logo" class="w-6 h-6 object-contain" />
								{/if}
								<span class="font-medium text-gray-900 dark:text-white">{team.team_name}</span>
							</div>
							<div class="flex items-center gap-4 text-sm">
								<span class="text-gray-500 dark:text-gray-400">
									{team.records.total_wins}-{team.records.total_losses}
								</span>
								<span class="font-semibold text-primary-600 dark:text-primary-400">
									{team.final_ranking_score.toFixed(1)}
								</span>
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Comparison Section -->
			{#if conferencesAhead.length > 0 || conferencesBehind.length > 0}
				<div class="p-6">
					<h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
						Conference Comparison
					</h3>

					<!-- Conferences Ahead -->
					{#if conferencesAhead.length > 0}
						<div class="mb-4">
							<h4 class="text-xs font-medium text-gray-400 dark:text-gray-500 mb-2">
								Conferences Ranked Higher
							</h4>
							<div class="space-y-2">
								{#each conferencesAhead as conf, i}
									{@const confRank = sortedConferences.findIndex(c => c.conference === conf.conference) + 1}
									{@const diff = getDiff(conference, conf)}
									<div class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/30">
										<div class="flex items-center gap-3">
											<span 
												class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
												style="background-color: {getConferenceColor(conf.conference)}"
											>
												{confRank}
											</span>
											<span class="font-medium text-gray-900 dark:text-white">{conf.conference}</span>
										</div>
										<div class="flex items-center gap-3 text-sm">
											<span class="text-gray-600 dark:text-gray-400">
												Avg: {conf.avg_ranking.toFixed(1)}
											</span>
											<span class="{getDiffClass(diff)} font-medium">
												{formatDiff(diff)}
											</span>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Current Conference Highlight -->
					<div 
						class="p-3 rounded-lg border-2 mb-4"
						style="border-color: {getConferenceColor(conference.conference)}; background-color: {getConferenceColor(conference.conference)}15"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-3">
								<span 
									class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
									style="background-color: {getConferenceColor(conference.conference)}"
								>
									{rank}
								</span>
								<span class="font-semibold text-gray-900 dark:text-white">{conference.conference}</span>
							</div>
							<span class="font-bold text-primary-600 dark:text-primary-400">
								{conference.avg_ranking.toFixed(1)}
							</span>
						</div>
					</div>

					<!-- Conferences Behind -->
					{#if conferencesBehind.length > 0}
						<div>
							<h4 class="text-xs font-medium text-gray-400 dark:text-gray-500 mb-2">
								Conferences Ranked Lower
							</h4>
							<div class="space-y-2">
								{#each conferencesBehind as conf, i}
									{@const confRank = sortedConferences.findIndex(c => c.conference === conf.conference) + 1}
									{@const diff = getDiff(conference, conf)}
									<div class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/30">
										<div class="flex items-center gap-3">
											<span 
												class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
												style="background-color: {getConferenceColor(conf.conference)}"
											>
												{confRank}
											</span>
											<span class="font-medium text-gray-900 dark:text-white">{conf.conference}</span>
										</div>
										<div class="flex items-center gap-3 text-sm">
											<span class="text-gray-600 dark:text-gray-400">
												Avg: {conf.avg_ranking.toFixed(1)}
											</span>
											<span class="{getDiffClass(diff)} font-medium">
												{formatDiff(diff)}
											</span>
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

<style>
	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}
	
	@keyframes zoom-in {
		from { transform: scale(0.95); }
		to { transform: scale(1); }
	}
	
	.animate-in {
		animation: fade-in 0.2s ease-out, zoom-in 0.2s ease-out;
	}
</style>
