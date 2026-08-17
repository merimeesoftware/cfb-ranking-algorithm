<script lang="ts">
	import { BRAND_NAME } from '$lib/brand';

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
				</a>. The board is ours. Rankings stay free.
			</p>
			<div class="flex items-center gap-4 text-sm">
				<a
					href="/methodology"
					class="hover:text-white focus:outline-none focus-visible:underline"
				>
					How it works
				</a>
				<a
					href="/#the-drop"
					class="hover:text-white focus:outline-none focus-visible:underline"
				>
					The Drop
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
		<div class="mt-4 text-center text-xs text-cfb-chalk/50 space-y-1">
			<p>
				© {new Date().getFullYear()}
				{BRAND_NAME}. Not affiliated with the NCAA or College Football Playoff.
			</p>
			<p>
				21+ where required. Gambling problem? Call
				<a href="https://www.ncpgambling.org/help-treatment/" class="underline hover:text-cfb-chalk" rel="noopener noreferrer" target="_blank">1-800-GAMBLER</a>
				or visit
				<a href="https://www.ncpgambling.org/" class="underline hover:text-cfb-chalk" rel="noopener noreferrer" target="_blank">ncpgambling.org</a>.
			</p>
		</div>
	</div>
</footer>
{/if}
