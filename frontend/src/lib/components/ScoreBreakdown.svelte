<script lang="ts">
	import { PUBLIC_FORMULA, scoreParts, weightPercent } from '$lib/publicFormula';

	export let team: {
		team_quality_score: number;
		record_score: number;
		conference_quality_score: number;
		final_ranking_score: number;
	};

	$: parts = scoreParts(team);
	$: rows = [
		{
			label: 'How they look',
			weight: PUBLIC_FORMULA.team_quality_weight,
			raw: team.team_quality_score,
			part: parts.look,
			bar: 'bg-primary-600',
		},
		{
			label: 'Who they beat',
			weight: PUBLIC_FORMULA.record_weight,
			raw: team.record_score,
			part: parts.resume,
			bar: 'bg-amber-500',
		},
		{
			label: 'League strength',
			weight: PUBLIC_FORMULA.conference_weight,
			raw: team.conference_quality_score,
			part: parts.league,
			bar: 'bg-stone-500',
		},
	];
</script>

<div>
	<h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-3">
		Why this spot
	</h3>
	<div class="space-y-4">
		{#each rows as row (row.label)}
			<div>
				<div class="flex justify-between text-sm mb-1 gap-3">
					<div class="flex items-center gap-2 min-w-0">
						<span class="font-medium text-gray-700 dark:text-gray-300">{row.label}</span>
						<span class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
							{weightPercent(row.weight)}
						</span>
					</div>
					<span class="font-mono text-gray-900 dark:text-white shrink-0">
						{row.raw.toFixed(1)}
						<span class="text-gray-400">→</span>
						{row.part.toFixed(1)}
					</span>
				</div>
				<div class="h-2.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
					<div
						class="h-full rounded-full {row.bar}"
						style="width: {team.final_ranking_score > 0
							? Math.min((row.part / team.final_ranking_score) * 100, 100)
							: 0}%"
					></div>
				</div>
			</div>
		{/each}
	</div>
	<div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-between items-center">
		<span class="font-bold text-gray-900 dark:text-white">Board score</span>
		<span class="text-2xl font-bold text-primary-600 dark:text-primary-400">
			{team.final_ranking_score.toFixed(2)}
		</span>
	</div>
	<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
		These three parts add up to the board score.
	</p>
</div>
