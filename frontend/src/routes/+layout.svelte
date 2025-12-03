<script lang="ts">
	import '../app.css';
	import Header from '$lib/components/Header.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { theme, applyTheme } from '$lib/stores/theme';
	import { onMount } from 'svelte';

	onMount(() => {
		// Apply theme on mount
		applyTheme($theme);
	});

	// React to theme changes
	$: applyTheme($theme);
</script>

<div class="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 transition-colors">
	<Header />
	
	<main class="flex-1">
		<slot />
	</main>

	<Footer />
</div>
