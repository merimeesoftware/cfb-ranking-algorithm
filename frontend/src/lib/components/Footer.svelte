<script lang="ts">
	export let footerOnly: boolean = false;
</script>

{#if !footerOnly}
<footer class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
	<div class="max-w-7xl mx-auto px-4 py-6">
		<div class="flex flex-col sm:flex-row items-center justify-between gap-4">
			<div class="text-sm text-gray-500 dark:text-gray-400">
				<p>Data provided by <a href="https://collegefootballdata.com/" target="_blank" rel="noopener noreferrer" 
					class="text-primary-600 dark:text-primary-400 hover:underline">College Football Data API</a></p>
			</div>
			<div class="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
				<a href="/about" class="hover:text-gray-700 dark:hover:text-gray-300">About</a>
				<a href="/methodology" class="hover:text-gray-700 dark:hover:text-gray-300">Methodology</a>
				<a href="https://github.com" target="_blank" rel="noopener noreferrer" 
					class="hover:text-gray-700 dark:hover:text-gray-300">GitHub</a>
			</div>
		</div>
		<div class="mt-4 text-center text-xs text-gray-400 dark:text-gray-500">
			© {new Date().getFullYear()} CFB Rankings. Not affiliated with the NCAA or College Football Playoff.
		</div>
	</div>
</footer>
{/if}
