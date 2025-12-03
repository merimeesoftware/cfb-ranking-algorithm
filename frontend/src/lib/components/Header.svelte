<script lang="ts">
	import { theme, toggleTheme, isDarkMode } from '$lib/stores/theme';
	import { page } from '$app/stores';

	let mobileMenuOpen = false;

	const navItems = [
		{ href: '/', label: 'Rankings' },
		{ href: '/methodology', label: 'Methodology' }
	];

	$: darkMode = isDarkMode($theme);
</script>

<header class="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50">
	<nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<div class="flex justify-between h-14 sm:h-16">
			<!-- Logo -->
			<div class="flex items-center">
				<a href="/" class="flex items-center gap-2 text-primary-600 dark:text-primary-400">
					<svg class="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
					</svg>
					<span class="font-bold text-lg hidden sm:block">CFB Rankings</span>
					<span class="font-bold text-lg sm:hidden">CFB</span>
				</a>
			</div>

			<!-- Desktop Nav -->
			<div class="hidden sm:flex items-center gap-6">
				{#each navItems as item}
					<a
						href={item.href}
						class="text-sm font-medium transition-colors
							{$page.url.pathname === item.href
								? 'text-primary-600 dark:text-primary-400'
								: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'}"
					>
						{item.label}
					</a>
				{/each}

				<!-- Dark Mode Toggle -->
				<button
					on:click={toggleTheme}
					class="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					aria-label="Toggle dark mode"
				>
					{#if darkMode}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
						</svg>
					{:else}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
						</svg>
					{/if}
				</button>
			</div>

			<!-- Mobile Menu Button -->
			<div class="flex items-center sm:hidden gap-2">
				<button
					on:click={toggleTheme}
					class="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
				>
					{#if darkMode}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
						</svg>
					{:else}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
						</svg>
					{/if}
				</button>

				<button
					on:click={() => (mobileMenuOpen = !mobileMenuOpen)}
					class="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
				>
					{#if mobileMenuOpen}
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					{:else}
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
						</svg>
					{/if}
				</button>
			</div>
		</div>

		<!-- Mobile Menu -->
		{#if mobileMenuOpen}
			<div class="sm:hidden pb-3 border-t border-gray-200 dark:border-gray-700">
				{#each navItems as item}
					<a
						href={item.href}
						on:click={() => (mobileMenuOpen = false)}
						class="block px-4 py-3 text-base font-medium
							{$page.url.pathname === item.href
								? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20'
								: 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'}"
					>
						{item.label}
					</a>
				{/each}
			</div>
		{/if}
	</nav>
</header>
