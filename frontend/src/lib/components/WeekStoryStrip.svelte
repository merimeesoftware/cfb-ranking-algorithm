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
	<section class="mb-5 mt-1 px-0.5 sm:px-0" aria-label="This week on the board">
		{#if headline}
			<h2 class="font-display text-xl sm:text-2xl font-semibold text-primary-900 dark:text-cfb-chalk leading-snug tracking-wide">
				{headline}
			</h2>
		{/if}
		{#if paragraphs.length > 0}
			<div class="mt-3 space-y-2 max-w-3xl">
				{#each paragraphs as para}
					<p class="text-sm sm:text-[0.95rem] text-primary-800/90 dark:text-primary-100/85 leading-relaxed">
						{para}
					</p>
				{/each}
			</div>
		{/if}
	</section>
{/if}
