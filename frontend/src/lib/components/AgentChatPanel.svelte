<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { BUSY_MESSAGE, explainRanking } from '$lib/api';
	import { filterState } from '$lib/stores/rankings';

	export let teamName: string;
	export let year: number | null = null;
	export let week: number | null = null;
	export let open = false;

	const dispatch = createEventDispatcher<{ close: void }>();

	let explanation = '';
	let loading = false;
	let busy = false;
	let busyMessage = BUSY_MESSAGE;
	let aiWritten = false;
	let error: string | null = null;

	const FRIENDLY_ERROR = 'Couldn’t break down this ranking right now.';
	const AI_WRITTEN_LINE = "Written by AI from this week's numbers.";
	const QUESTIONS = [
		{ id: 'why_here', label: 'Why is this team here?' },
		{ id: 'path_up', label: "What's holding them back?" },
		{ id: 'results', label: 'Which results are carrying this?' },
		{ id: 'neighbors', label: 'Why not the teams next to them?' },
	];

	async function ask(questionId: string) {
		loading = true;
		error = null;
		busy = false;
		busyMessage = BUSY_MESSAGE;
		aiWritten = false;
		explanation = '';
		try {
			const result = await explainRanking(
				teamName,
				year ?? $filterState.year,
				week ?? $filterState.week,
				questionId
			);
			if (result.busy) {
				busy = true;
				busyMessage = result.message || BUSY_MESSAGE;
			}
			if (result.explanation) explanation = result.explanation;
			aiWritten = result.aiWritten === true;
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

			<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Pick a question</p>
			<div class="flex flex-col gap-2">
				{#each QUESTIONS as item}
					<button
						type="button"
						on:click={() => ask(item.id)}
						disabled={loading}
						class="btn btn-secondary w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50"
					>
						{item.label}
					</button>
				{/each}
			</div>

			{#if busy}
				<p class="mt-3 text-sm text-gray-700 dark:text-gray-300" role="status">{busyMessage}</p>
			{:else if error}
				<p class="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
			{/if}

			{#if explanation}
				<div class="mt-4 p-3 rounded-lg bg-gray-50 dark:bg-gray-900 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
					{explanation}
				</div>
				{#if aiWritten}
					<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">{AI_WRITTEN_LINE}</p>
				{/if}
			{/if}
		</div>
	</div>
{/if}
