<script lang="ts">
	import { fetchWeekStory } from '$lib/api';

	export let year: number;
	export let week: number;

	let headline: string | null = null;
	let paragraphs: string[] = [];
	let requestId = 0;

	$: loadStory(year, week);

	async function loadStory(y: number, w: number) {
		const id = ++requestId;
		headline = null;
		paragraphs = [];
		const story = await fetchWeekStory(y, w);
		if (id !== requestId) return;
		if (story?.headline) headline = story.headline;
		if (story?.paragraphs?.length) paragraphs = story.paragraphs;
	}
</script>

{#if headline || paragraphs.length > 0}
	<section
		class="mb-5 mt-1 relative overflow-hidden border-l-4 border-cfb-gold bg-white/80 dark:bg-primary-900/70 px-4 sm:px-5 py-4"
		aria-label="This week on the board"
	>
		<div
			class="pointer-events-none absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-primary-700/5 to-transparent dark:from-cfb-gold/10"
			aria-hidden="true"
		></div>
		<p class="font-display text-xs uppercase tracking-[0.18em] text-primary-600 dark:text-cfb-gold-bright mb-1.5">
			This week on the board
		</p>
		{#if headline}
			<h2 class="font-display text-xl sm:text-2xl font-semibold text-primary-900 dark:text-white leading-snug">
				{headline}
			</h2>
		{/if}
		{#if paragraphs.length > 0}
			<div class="mt-3 space-y-2 max-w-3xl">
				{#each paragraphs as para}
					<p class="text-sm sm:text-[0.95rem] text-primary-800/85 dark:text-primary-100/85 leading-relaxed">
						{para}
					</p>
				{/each}
			</div>
		{/if}
	</section>
{/if}
