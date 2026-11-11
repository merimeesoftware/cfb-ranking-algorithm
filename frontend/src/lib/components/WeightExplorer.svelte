<script lang="ts">
	import { onMount } from 'svelte';
	import { PUBLIC_FORMULA } from '$lib/publicFormula';
	import { whatIfTop } from '$lib/whatIfOrder.js';

	type Row = {
		team_name: string;
		team_quality_score: number;
		record_score: number;
		conference_quality_score: number;
		final_ranking_score: number;
		officialRank: number;
	};

	let look = PUBLIC_FORMULA.team_quality_weight * 100;
	let resume = PUBLIC_FORMULA.record_weight * 100;
	let league = PUBLIC_FORMULA.conference_weight * 100;
	let teams: Row[] = [];
	let weekLabel = '';
	let unavailable = false;

	function shareRest(changed: number, a: number, b: number): [number, number] {
		const rest = Math.max(0, 100 - changed);
		const other = a + b;
		if (other <= 0) return [rest / 2, rest / 2];
		return [rest * (a / other), rest * (b / other)];
	}

	function setLook(value: number) {
		look = value;
		[resume, league] = shareRest(value, resume, league);
	}

	function setResume(value: number) {
		resume = value;
		[look, league] = shareRest(value, look, league);
	}

	function setLeague(value: number) {
		league = value;
		[look, resume] = shareRest(value, look, resume);
	}

	function resetOfficial() {
		look = PUBLIC_FORMULA.team_quality_weight * 100;
		resume = PUBLIC_FORMULA.record_weight * 100;
		league = PUBLIC_FORMULA.conference_weight * 100;
	}

	$: ordered = whatIfTop(
		teams,
		{ look: look / 100, resume: resume / 100, league: league / 100 },
		8
	);
	$: officialWeights =
		Math.abs(look - PUBLIC_FORMULA.team_quality_weight * 100) < 0.05 &&
		Math.abs(resume - PUBLIC_FORMULA.record_weight * 100) < 0.05 &&
		Math.abs(league - PUBLIC_FORMULA.conference_weight * 100) < 0.05;

	onMount(async () => {
		try {
			const manifestRes = await fetch('/rankings/manifest.json');
			if (!manifestRes.ok) {
				unavailable = true;
				return;
			}
			const manifest = (await manifestRes.json()) as { years?: Record<string, number[]> };
			const years = Object.keys(manifest.years || {})
				.map(Number)
				.filter((year) => Number.isFinite(year))
				.sort((a, b) => a - b);
			const year = years[years.length - 1];
			const weeks = (manifest.years?.[String(year)] || []).slice().sort((a, b) => a - b);
			const week = weeks[weeks.length - 1];
			if (!year || !week) {
				unavailable = true;
				return;
			}
			const weekRes = await fetch(`/rankings/${year}/week-${week}.json`);
			if (!weekRes.ok) {
				unavailable = true;
				return;
			}
			const data = (await weekRes.json()) as {
				team_rankings?: Row[];
			};
			const ranked = (data.team_rankings || [])
				.filter((team) => team.team_name)
				.sort((a, b) => b.final_ranking_score - a.final_ranking_score);
			teams = ranked.map((team, index) => ({ ...team, officialRank: index + 1 }));
			weekLabel = `${year} week ${week}`;
		} catch {
			unavailable = true;
		}
	});
</script>

<section
	class="card p-6 mb-8 border-dashed border-2 border-cfb-gold/70"
	aria-labelledby="exploratory-weights"
>
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-700 dark:text-cfb-gold-bright">
		Exploratory
	</p>
	<h2 id="exploratory-weights" class="mt-1 text-xl font-semibold text-gray-900 dark:text-white">
		Weight sliders
	</h2>
	<p class="mt-2 text-sm text-gray-600 dark:text-gray-400 max-w-2xl">
		A what-if on this browser. It does not change the official board.
	</p>

	{#if unavailable}
		<p class="mt-4 text-sm text-gray-600 dark:text-gray-400" role="status">
			This week's published board isn't available in the browser yet.
		</p>
	{:else if teams.length === 0}
		<p class="mt-4 text-sm text-gray-600 dark:text-gray-400" role="status">Loading the published board…</p>
	{:else}
		<div class="mt-5 space-y-4">
			<label class="block text-sm">
				<span class="flex justify-between text-gray-800 dark:text-gray-200">
					<span>How they look</span>
					<span class="font-mono">{look.toFixed(0)}%</span>
				</span>
				<input
					class="mt-1 w-full accent-primary-700"
					type="range"
					min="0"
					max="100"
					step="1"
					value={look}
					on:input={(event) => setLook(Number(event.currentTarget.value))}
				/>
			</label>
			<label class="block text-sm">
				<span class="flex justify-between text-gray-800 dark:text-gray-200">
					<span>Who they beat</span>
					<span class="font-mono">{resume.toFixed(0)}%</span>
				</span>
				<input
					class="mt-1 w-full accent-amber-600"
					type="range"
					min="0"
					max="100"
					step="1"
					value={resume}
					on:input={(event) => setResume(Number(event.currentTarget.value))}
				/>
			</label>
			<label class="block text-sm">
				<span class="flex justify-between text-gray-800 dark:text-gray-200">
					<span>League strength</span>
					<span class="font-mono">{league.toFixed(0)}%</span>
				</span>
				<input
					class="mt-1 w-full accent-stone-500"
					type="range"
					min="0"
					max="100"
					step="1"
					value={league}
					on:input={(event) => setLeague(Number(event.currentTarget.value))}
				/>
			</label>
		</div>
		<div class="mt-4 flex flex-wrap items-center gap-3">
			<button
				type="button"
				class="btn btn-secondary active:translate-y-px"
				on:click={resetOfficial}
			>
				Reset to the official weights
			</button>
			<p class="text-xs text-gray-500 dark:text-gray-400">
				{officialWeights ? `Official weights for ${weekLabel}.` : `What-if for ${weekLabel}. Official order unchanged.`}
			</p>
		</div>
		<div class="mt-4 overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="text-left text-xs uppercase tracking-wider text-gray-500">
						<th class="py-2 pr-3">What-if</th>
						<th class="py-2 pr-3">Team</th>
						<th class="py-2 text-right">Official rank</th>
					</tr>
				</thead>
				<tbody>
					{#each ordered as team, index (team.team_name)}
						<tr class="border-t border-gray-100 dark:border-gray-700">
							<td class="py-2 pr-3 font-display">{index + 1}</td>
							<td class="py-2 pr-3">{team.team_name}</td>
							<td class="py-2 text-right font-mono">{team.officialRank}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</section>
