<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import SeoHead from '$lib/components/SeoHead.svelte';
	import ScoreBreakdown from '$lib/components/ScoreBreakdown.svelte';
	import { scoreParts } from '$lib/publicFormula';
	import {
		BRAND_NAME,
		RATING_NAME,
		TAGLINE,
		pageTitle,
		teamPath,
		weekPath,
		publicUrl,
		findTeamBySlug,
		teamSlug,
		matchupSlug,
	} from '$lib/brand';
	import { fetchRankingsFromApi } from '$lib/api';
	import type { Team } from '$lib/types';

	export let data: {
		year: number;
		week: number;
		teamA: Team & { rank: number };
		teamB: Team & { rank: number };
		canonicalSlug: string;
	};

	let year = data.year;
	let week = data.week;
	let teamA = data.teamA;
	let teamB = data.teamB;
	let canonicalSlug = data.canonicalSlug;

	onMount(async () => {
		const y = Number(page.url.searchParams.get('year'));
		const w = Number(page.url.searchParams.get('week'));
		if (!y || !w || (y === year && w === week)) return;
		try {
			const rankings = await fetchRankingsFromApi(y, w);
			const a = findTeamBySlug(rankings.teams, teamSlug(data.teamA.team_name));
			const b = findTeamBySlug(rankings.teams, teamSlug(data.teamB.team_name));
			if (!a || !b) return;
			const rankA = rankings.teams.findIndex((t) => t.team_name === a.team_name) + 1;
			const rankB = rankings.teams.findIndex((t) => t.team_name === b.team_name) + 1;
			year = y;
			week = w;
			teamA = { ...a, rank: rankA };
			teamB = { ...b, rank: rankB };
			canonicalSlug = matchupSlug(a.team_name, b.team_name);
		} catch {
			/* keep SSR seed */
		}
	});

	$: title = pageTitle([`${teamA.team_name} vs ${teamB.team_name}`, RATING_NAME]);
	$: description = `${teamA.team_name} (#${teamA.rank}, ${RATING_NAME} ${teamA.final_ranking_score.toFixed(1)}) and ${teamB.team_name} (#${teamB.rank}, ${RATING_NAME} ${teamB.final_ranking_score.toFixed(1)}). ${TAGLINE}`;
	$: path = `/games/${canonicalSlug}`;
	$: partsA = scoreParts(teamA);
	$: partsB = scoreParts(teamB);
	$: edges = [
		{ label: 'How they look', a: partsA.look, b: partsB.look },
		{ label: 'Who they beat', a: partsA.resume, b: partsB.resume },
		{ label: 'League strength', a: partsA.league, b: partsB.league },
	];

	function edgeName(a: number, b: number): string {
		if (Math.abs(a - b) < 0.05) return 'Even';
		return a > b ? teamA.team_name : teamB.team_name;
	}
	$: jsonLd = {
		'@context': 'https://schema.org',
		'@type': 'SportsEvent',
		name: `${teamA.team_name} vs ${teamB.team_name}`,
		description,
		url: publicUrl(path),
		homeTeam: teamA.team_name,
		awayTeam: teamB.team_name,
	};
</script>

<SeoHead {title} {description} canonicalPath={path} {jsonLd} />

<div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
	<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
		{BRAND_NAME} comparison · {year} Week {week}
	</p>
	<h1 class="mt-2 font-display text-3xl sm:text-4xl text-primary-900 dark:text-white">
		{teamA.team_name}
		<span class="text-primary-400 font-sans text-xl mx-2">vs</span>
		{teamB.team_name}
	</h1>
	<p class="mt-2 text-primary-700 dark:text-primary-300">
		Side by side on the published {RATING_NAME} board.
	</p>

	<div class="mt-6 grid sm:grid-cols-2 gap-4">
		{#each [teamA, teamB] as side}
			<a
				href={teamPath(side.team_name, year, week)}
				class="card p-4 hover:border-cfb-gold transition-colors"
			>
				<p class="text-xs uppercase text-primary-600 dark:text-primary-400">#{side.rank}</p>
				<p class="font-display text-xl text-primary-900 dark:text-white">{side.team_name}</p>
				<p class="mt-1 text-sm text-primary-700 dark:text-primary-300">
					{side.conference} · {RATING_NAME}
					{side.final_ranking_score.toFixed(1)} · {side.records.total_wins}-{side.records.total_losses}
				</p>
			</a>
		{/each}
	</div>

	<div class="mt-6 card p-4 sm:p-5">
		<h2 class="font-display text-lg text-primary-900 dark:text-white">Why one is ahead</h2>
		<p class="mt-1 text-sm text-primary-700 dark:text-primary-300">
			Same published week. Official board scores.
		</p>
		<div class="mt-4 overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="text-left text-xs uppercase tracking-wider text-primary-600">
						<th class="py-2 pr-3">Part</th>
						<th class="py-2 pr-3 text-right">{teamA.team_name}</th>
						<th class="py-2 pr-3 text-right">{teamB.team_name}</th>
						<th class="py-2 text-right">Higher</th>
					</tr>
				</thead>
				<tbody>
					{#each edges as edge (edge.label)}
						<tr class="border-t border-primary-100 dark:border-primary-800">
							<td class="py-2 pr-3">{edge.label}</td>
							<td class="py-2 pr-3 text-right font-mono">{edge.a.toFixed(1)}</td>
							<td class="py-2 pr-3 text-right font-mono">{edge.b.toFixed(1)}</td>
							<td class="py-2 text-right">{edgeName(edge.a, edge.b)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>

	<div class="mt-6 grid sm:grid-cols-2 gap-4">
		<div class="card p-4">
			<ScoreBreakdown team={teamA} />
		</div>
		<div class="card p-4">
			<ScoreBreakdown team={teamB} />
		</div>
	</div>

	<p class="mt-6 text-sm">
		<a href={weekPath(year, week)} class="text-primary-700 dark:text-cfb-gold-bright hover:underline"
			>← Week {week} board</a
		>
	</p>
</div>
