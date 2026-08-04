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
		class="mb-4 mt-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 px-4 py-3"
		aria-label="Week story"
	>
		{#if headline}
			<h2 class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white">
				{headline}
			</h2>
		{/if}
		{#if paragraphs.length > 0}
			<div class="mt-2 space-y-2">
				{#each paragraphs as para}
					<p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{para}</p>
				{/each}
			</div>
		{/if}
	</section>
{/if}
