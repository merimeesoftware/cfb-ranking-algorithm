<script lang="ts">
	import { BRAND_NAME, NAV, POSITIONING_LINE, RATING_NAME, TAGLINE } from '$lib/brand';

	export let year: number;
	export let week: number;
	export let showLines = false;
	/** Formula page only. The signed comp leaves the brand as text on the board. */
	export let linkHome = false;
</script>

<header class="mast">
	<div class="mast-row">
		<p class="brand">
			{#if linkHome}
				<a href="/">{BRAND_NAME}</a>
			{:else}
				{BRAND_NAME}
			{/if}
		</p>
		<p class="week">{year} · Week {week} · {RATING_NAME}</p>
		<p class="tagline">{TAGLINE}</p>
		<p class="formula-link"><a href="/methodology">{NAV.formula}</a></p>
	</div>
	{#if showLines}
		<p class="position">{POSITIONING_LINE}</p>
	{/if}
</header>
