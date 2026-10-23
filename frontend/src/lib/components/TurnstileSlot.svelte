<script lang="ts">
	import { onMount } from 'svelte';
	import { startTurnstile, turnstileSiteKey } from '$lib/turnstile';

	const siteKey = turnstileSiteKey();
	let host: HTMLDivElement | undefined;

	onMount(() => {
		if (!siteKey || !host) return undefined;
		return startTurnstile(host);
	});
</script>

{#if siteKey}
	<div
		class="fixed bottom-4 right-4 z-40 rounded-md border border-primary-200 bg-white/95 p-2 shadow-sm dark:border-primary-800 dark:bg-primary-950/95"
	>
		<p class="sr-only">Visitor check</p>
		<div bind:this={host}></div>
	</div>
{/if}
