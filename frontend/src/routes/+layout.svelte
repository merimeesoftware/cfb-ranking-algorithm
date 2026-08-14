<script lang="ts">
	import '../app.css';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { theme, applyTheme } from '$lib/stores/theme';
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

<div class="min-h-screen flex flex-col bg-cfb-chalk dark:bg-primary-950 transition-colors">
	<Header />

	<main class="flex-1">
		<slot />
	</main>

	<Footer />
</div>
