<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { explainRanking } from '$lib/api';
	import { filterState } from '$lib/stores/rankings';

	export let teamName: string;
	export let open = false;

	const dispatch = createEventDispatcher<{ close: void }>();

	let question = '';
	let explanation = '';
	let loading = false;
	let error: string | null = null;

	const FRIENDLY_ERROR = 'Couldn’t break down this ranking right now.';

	async function ask() {
		loading = true;
		error = null;
		explanation = '';
		try {
			const result = await explainRanking(
				teamName,
				$filterState.year,
				$filterState.week,
				question || `Why is ${teamName} here — and who should be mad?`
			);
			explanation = result.explanation;
		} catch {
			error = FRIENDLY_ERROR;
		} finally {
			loading = false;
		}
	}

	function close() {
		dispatch('close');
	}
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/50"
		role="dialog"
		aria-modal="true"
		aria-labelledby="agent-chat-title"
	>
		<div class="card w-full max-w-lg p-4 sm:p-6 max-h-[80vh] overflow-y-auto">
			<div class="flex items-center justify-between mb-4">
				<h2 id="agent-chat-title" class="text-lg font-semibold text-gray-900 dark:text-white">
					Why {teamName}?
				</h2>
				<button
					type="button"
					on:click={close}
					class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded"
					aria-label="Close chat"
				>
					✕
				</button>
			</div>

			<label class="block text-sm text-gray-600 dark:text-gray-400 mb-2" for="agent-question">
				Ask anything (optional)
			</label>
			<input
				id="agent-question"
				bind:value={question}
				placeholder={`Why is ${teamName} here — and who should be mad?`}
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
			/>

			<button
				type="button"
				on:click={ask}
				disabled={loading}
				class="btn btn-primary mt-3 w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50"
			>
				{loading ? 'Breaking it down…' : 'Break it down'}
			</button>

			{#if error}
				<p class="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
			{/if}

			{#if explanation}
				<div class="mt-4 p-3 rounded-lg bg-gray-50 dark:bg-gray-900 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
					{explanation}
				</div>
			{/if}
		</div>
	</div>
{/if}
