<script lang="ts">
	import { theme, toggleTheme, isDarkMode } from '$lib/stores/theme';
	import { page } from '$app/stores';
	import { BRAND_NAME, BRAND_SHORT } from '$lib/brand';

	let mobileMenuOpen = false;

	const navItems = [
		{ href: '/', label: 'The Board' },
		{ href: '/methodology', label: 'How it works' },
		{ href: '/#the-drop', label: 'The Drop' }
	];

	$: darkMode = isDarkMode($theme);
</script>

<header class="bg-primary-900/95 text-cfb-chalk backdrop-blur sticky top-0 z-50 border-b border-primary-800">
	<nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" aria-label="Primary">
		<div class="flex justify-between h-14 sm:h-16">
			<div class="flex items-center">
				<a
					href="/"
					class="flex items-center gap-2.5 text-cfb-chalk hover:text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cfb-gold rounded-sm"
				>
					<span
						class="inline-flex h-8 w-8 items-center justify-center rounded-sm bg-cfb-gold text-primary-950 font-display font-bold text-sm tracking-wide"
						aria-hidden="true"
					>
						{BRAND_SHORT}
					</span>
					<span class="font-display font-semibold text-lg tracking-wide hidden sm:block">
						{BRAND_NAME}
					</span>
					<span class="font-display font-semibold text-lg sm:hidden">{BRAND_SHORT}</span>
				</a>
			</div>

			<div class="hidden sm:flex items-center gap-6">
				{#each navItems as item}
					<a
						href={item.href}
						class="text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cfb-gold rounded-sm
							{$page.url.pathname === item.href
								? 'text-cfb-gold-bright'
								: 'text-cfb-chalk/80 hover:text-white'}"
					>
						{item.label}
					</a>
				{/each}

				<button
					on:click={toggleTheme}
					class="p-2 rounded-md text-cfb-chalk/70 hover:bg-white/10 hover:text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cfb-gold"
					aria-label="Toggle dark mode"
				>
					{#if darkMode}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
							/>
						</svg>
					{:else}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
							/>
						</svg>
					{/if}
				</button>
			</div>

			<div class="flex items-center sm:hidden gap-2">
				<button
					on:click={toggleTheme}
					class="p-2 rounded-md text-cfb-chalk/70 hover:bg-white/10"
					aria-label="Toggle dark mode"
				>
					{#if darkMode}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
							/>
						</svg>
					{:else}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
							/>
						</svg>
					{/if}
				</button>

				<button
					on:click={() => (mobileMenuOpen = !mobileMenuOpen)}
					class="p-2 rounded-md text-cfb-chalk/70 hover:bg-white/10"
					aria-expanded={mobileMenuOpen}
					aria-controls="mobile-nav"
					aria-label="Open menu"
				>
					{#if mobileMenuOpen}
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					{:else}
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
						</svg>
					{/if}
				</button>
			</div>
		</div>

		{#if mobileMenuOpen}
			<div id="mobile-nav" class="sm:hidden pb-3 border-t border-primary-800">
				{#each navItems as item}
					<a
						href={item.href}
						on:click={() => (mobileMenuOpen = false)}
						class="block px-4 py-3 text-base font-medium
							{$page.url.pathname === item.href
								? 'text-cfb-gold-bright bg-white/5'
								: 'text-cfb-chalk/80 hover:bg-white/5 hover:text-white'}"
					>
						{item.label}
					</a>
				{/each}
			</div>
		{/if}
	</nav>
</header>
