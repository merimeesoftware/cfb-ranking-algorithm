<script lang="ts">
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let message: string = 'Loading...';

	const sizeClasses = {
		sm: 'w-5 h-5',
		md: 'w-8 h-8',
		lg: 'w-12 h-12'
	};
</script>

<div class="flex flex-col items-center justify-center gap-3 py-8">
	<div class="relative">
		<!-- Outer ring -->
		<div class="{sizeClasses[size]} border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
		<!-- Spinner -->
		<div 
			class="absolute inset-0 {sizeClasses[size]} border-4 border-transparent 
				border-t-primary-600 dark:border-t-primary-400 rounded-full animate-spin"
		></div>
	</div>
	{#if message}
		<p class="text-sm text-gray-500 dark:text-gray-400">{message}</p>
	{/if}
</div>
