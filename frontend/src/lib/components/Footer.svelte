<script lang="ts">
	export let footerOnly: boolean = false;

	const githubUrl = 'https://github.com/merimeesoftware/cfb-ranking-algorithm';
</script>

{#if !footerOnly}
<footer class="bg-primary-900 text-cfb-chalk/80 border-t border-primary-800">
	<div class="max-w-7xl mx-auto px-4 py-6">
		<div class="flex flex-col sm:flex-row items-center justify-between gap-4">
			<p class="text-sm text-center sm:text-left">
				Game data from
				<a
					href="https://collegefootballdata.com/"
					target="_blank"
					rel="noopener noreferrer"
					class="text-cfb-gold-bright hover:underline focus:outline-none focus-visible:underline"
				>
					College Football Data
				</a>. The board is ours.
			</p>
			<div class="flex items-center gap-4 text-sm">
				<a
					href="/methodology"
					class="hover:text-white focus:outline-none focus-visible:underline"
				>
					How it works
				</a>
				<a
					href={githubUrl}
					target="_blank"
					rel="noopener noreferrer"
					class="hover:text-white focus:outline-none focus-visible:underline"
				>
					GitHub
				</a>
			</div>
		</div>
		<div class="mt-4 text-center text-xs text-cfb-chalk/50">
			© {new Date().getFullYear()} CFB Rankings. Not affiliated with the NCAA or College Football Playoff.
		</div>
	</div>
</footer>
{/if}
