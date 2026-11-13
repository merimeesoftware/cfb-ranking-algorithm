<script lang="ts">
	import '../app.css';
	import '$lib/boardFace.css';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import TurnstileSlot from '$lib/components/TurnstileSlot.svelte';
	import { theme, applyTheme } from '$lib/stores/theme';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	// SvelteKit injects these; declare so Svelte 4 does not warn about unknown props
	// svelte-ignore unused-export-let
	export let params: Record<string, string> = {};
	// svelte-ignore unused-export-let
	export let data: Record<string, unknown> = {};

	onMount(() => {
		applyTheme($theme);
	});

	$: applyTheme($theme);
</script>

<div class={page.url.pathname === '/' || page.url.pathname === '/methodology' ? 'board-face' : 'min-h-screen flex flex-col bg-cfb-chalk dark:bg-primary-950 transition-colors'} class:formula={page.url.pathname === '/methodology'}>
	{#if page.url.pathname === '/' || page.url.pathname === '/methodology'}
		<slot />
	{:else}
		<Header />
		<main class="flex-1">
			<slot />
		</main>
		<Footer />
		<TurnstileSlot />
	{/if}
</div>
