<script lang="ts">
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let message: string = 'Building the board…';

	const sizeClasses = {
		sm: 'w-5 h-5',
		md: 'w-8 h-8',
		lg: 'w-12 h-12'
	};
</script>

<div class="flex flex-col items-center justify-center gap-3 py-8" role="status" aria-live="polite">
	<div class="relative" aria-hidden="true">
		<div class="{sizeClasses[size]} border-4 border-primary-200 dark:border-primary-800 rounded-full"></div>
		<div
			class="absolute inset-0 {sizeClasses[size]} border-4 border-transparent
				border-t-primary-700 dark:border-t-cfb-gold rounded-full animate-spin motion-reduce:animate-none"
		></div>
	</div>
	{#if message}
		<p class="text-sm font-medium text-primary-700 dark:text-primary-200">{message}</p>
	{/if}
</div>
