<script lang="ts">
	import { citationText, weekPath, SITE_ORIGIN, BRAND_NAME, RATING_NAME } from '$lib/brand';

	export let year: number;
	export let week: number;
	export let topTeams: Array<{ team_name: string; final_ranking_score?: number }> = [];

	let copyStatus: string | null = null;

	$: pageUrl =
		typeof window !== 'undefined'
			? `${window.location.origin}${weekPath(year, week)}`
			: `${SITE_ORIGIN}${weekPath(year, week)}`;

	$: cite = citationText(year, week, pageUrl);

	$: shareText = (() => {
		const lines = topTeams.slice(0, 5).map((t, i) => `${i + 1}. ${t.team_name}`);
		return `${BRAND_NAME} ${year} Week ${week} Top 5 (${RATING_NAME})\n${lines.join('\n')}\n${pageUrl}`;
	})();

	async function copyCitation() {
		try {
			await navigator.clipboard.writeText(cite);
			copyStatus = 'Citation copied';
		} catch {
			copyStatus = 'Copy failed — select the text manually';
		}
		setTimeout(() => (copyStatus = null), 2500);
	}

	async function shareTop25() {
		if (typeof navigator !== 'undefined' && navigator.share) {
			try {
				await navigator.share({
					title: `${BRAND_NAME} · ${year} Week ${week}`,
					text: shareText,
					url: pageUrl,
				});
				return;
			} catch {
				/* fall through to clipboard */
			}
		}
		try {
			await navigator.clipboard.writeText(shareText);
			copyStatus = 'Top 5 copied for posting';
		} catch {
			copyStatus = 'Could not copy share text';
		}
		setTimeout(() => (copyStatus = null), 2500);
	}
</script>

<div class="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:items-center" role="group" aria-label="Share and cite">
	<button type="button" class="btn btn-primary" on:click={shareTop25}>
		Share Top 25
	</button>
	<button type="button" class="btn btn-secondary" on:click={copyCitation}>
		Copy citation
	</button>
	<a href="#the-drop" class="btn btn-secondary">
		Get The Drop
	</a>
	{#if copyStatus}
		<span class="text-xs text-primary-600 dark:text-cfb-gold-bright" role="status">{copyStatus}</span>
	{/if}
</div>
<p class="mt-2 text-xs text-primary-600/80 dark:text-primary-400 truncate" title={cite}>
	Cite: {cite}
</p>
