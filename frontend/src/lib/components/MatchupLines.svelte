<script lang="ts">
	import {
		AFFILIATE_DISCLOSURE,
		BOOKS,
		BETTING_ALLOWED_STATES,
		RG_HELP_LABEL,
		RG_HELP_URL,
		booksForState,
		detectUsState,
		persistUsState,
		type AffiliateBook,
	} from '$lib/affiliates';
	import { onMount } from 'svelte';

	export let favoriteName: string;
	export let impliedSpread: number;
	export let marketSpread: number | null = null;
	export let delta: number | null = null;

	let state = '';
	let books: AffiliateBook[] = BOOKS;
	let blocked = false;

	onMount(() => {
		const detected = detectUsState();
		if (detected) {
			state = detected;
			applyState(detected);
		}
	});

	function applyState(st: string) {
		const upper = st.toUpperCase();
		persistUsState(upper);
		if (!BETTING_ALLOWED_STATES.has(upper)) {
			blocked = true;
			books = [];
			return;
		}
		blocked = false;
		books = booksForState(upper);
	}

	function onStateChange() {
		if (state.length === 2) applyState(state);
	}
</script>

<section class="card p-5 sm:p-6 mt-6" aria-labelledby="lines-heading">
	<h2 id="lines-heading" class="font-display text-xl text-primary-900 dark:text-white">
		Model vs market
	</h2>
	<p class="mt-1 text-sm text-primary-700 dark:text-primary-300">
		The market is buying the brand. TR+ is buying the team.
	</p>

	<div class="mt-4 grid sm:grid-cols-3 gap-3 text-sm">
		<div class="rounded-md bg-primary-50 dark:bg-primary-950/60 p-3">
			<p class="text-xs uppercase tracking-wide text-primary-600 dark:text-primary-400">TR+ implied</p>
			<p class="mt-1 font-semibold text-primary-900 dark:text-white">
				{#if impliedSpread === 0}
					Pick'em
				{:else}
					{favoriteName} -{impliedSpread.toFixed(1)}
				{/if}
			</p>
		</div>
		<div class="rounded-md bg-primary-50 dark:bg-primary-950/60 p-3">
			<p class="text-xs uppercase tracking-wide text-primary-600 dark:text-primary-400">Market</p>
			<p class="mt-1 font-semibold text-primary-900 dark:text-white">
				{#if marketSpread == null}
					When lines are available
				{:else if marketSpread === 0}
					Pick'em
				{:else}
					{favoriteName} -{Math.abs(marketSpread).toFixed(1)}
				{/if}
			</p>
		</div>
		<div class="rounded-md bg-primary-50 dark:bg-primary-950/60 p-3">
			<p class="text-xs uppercase tracking-wide text-primary-600 dark:text-primary-400">Delta</p>
			<p class="mt-1 font-semibold text-primary-900 dark:text-white">
				{#if delta == null}
					—
				{:else}
					{delta > 0 ? '+' : ''}{delta.toFixed(1)} pts
				{/if}
			</p>
		</div>
	</div>

	<div class="mt-4 flex flex-wrap items-end gap-3">
		<label class="text-sm text-primary-700 dark:text-primary-300" for="us-state">
			Your state (21+)
			<select
				id="us-state"
				bind:value={state}
				on:change={onStateChange}
				class="mt-1 block rounded-md border border-primary-200 dark:border-primary-700 bg-white dark:bg-primary-950 px-3 py-2 text-sm"
			>
				<option value="">Select</option>
				{#each [...BETTING_ALLOWED_STATES].sort() as st}
					<option value={st}>{st}</option>
				{/each}
				<option value="XX">Other / not listed</option>
			</select>
		</label>
	</div>

	{#if blocked}
		<p class="mt-3 text-sm text-primary-700 dark:text-primary-300">
			Sportsbook links are hidden in your state. The TR+ number above stays free for everyone.
		</p>
	{:else if books.length}
		<div class="mt-4 flex flex-col sm:flex-row flex-wrap gap-2">
			{#each books as book}
				<a
					href={book.url}
					target="_blank"
					rel="noopener noreferrer sponsored"
					class="btn btn-primary"
				>
					Open {book.name} on this number
				</a>
			{/each}
		</div>
	{/if}

	<p class="mt-4 text-xs text-primary-600 dark:text-primary-400">
		{AFFILIATE_DISCLOSURE}
		Must be 21+ (18+ where permitted). Gambling problem?
		<a href={RG_HELP_URL} class="underline" target="_blank" rel="noopener noreferrer">{RG_HELP_LABEL}</a>.
	</p>
</section>
