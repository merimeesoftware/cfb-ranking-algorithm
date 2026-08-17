<script lang="ts">
	import { DROP_NAME, BRAND_NAME } from '$lib/brand';
	import { API_BASE } from '$lib/api';

	export let compact = false;

	let email = '';
	let status: 'idle' | 'loading' | 'ok' | 'error' = 'idle';
	let message = '';

	async function subscribe(event: Event) {
		event.preventDefault();
		const trimmed = email.trim();
		if (!trimmed || !trimmed.includes('@')) {
			status = 'error';
			message = 'Enter a valid email.';
			return;
		}
		status = 'loading';
		message = '';
		try {
			const res = await fetch(`${API_BASE}/drop/subscribe`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email: trimmed, source: 'web' }),
			});
			const data = (await res.json().catch(() => ({}))) as { message?: string; error?: string };
			if (!res.ok) {
				status = 'error';
				message = data.error || 'Could not subscribe right now.';
				return;
			}
			status = 'ok';
			message = data.message || `You're on ${DROP_NAME}.`;
			email = '';
			try {
				localStorage.setItem('tr_drop_email', trimmed);
			} catch {
				/* ignore */
			}
		} catch {
			status = 'error';
			message = 'Network error — try again in a minute.';
		}
	}
</script>

<section
	id="the-drop"
	class={compact
		? 'card p-4 sm:p-5'
		: 'card p-5 sm:p-6 border-cfb-gold/40'}
	aria-labelledby="drop-heading"
>
	<div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
		<div class="min-w-0">
			<p class="text-xs font-semibold uppercase tracking-wider text-primary-600 dark:text-cfb-gold-bright">
				{DROP_NAME}
			</p>
			<h2 id="drop-heading" class="mt-1 font-display text-xl sm:text-2xl text-primary-900 dark:text-white">
				Get the weekly board in your inbox
			</h2>
			<p class="mt-1 text-sm text-primary-700 dark:text-primary-300 max-w-xl">
				Same free {BRAND_NAME} numbers as the site — Top 25, movers, and CFP 1–12 shifts. No paywall.
			</p>
		</div>
		<form class="w-full sm:w-auto sm:min-w-[20rem] flex flex-col gap-2" on:submit={subscribe}>
			<label class="sr-only" for="drop-email">Email</label>
			<div class="flex flex-col sm:flex-row gap-2">
				<input
					id="drop-email"
					type="email"
					autocomplete="email"
					bind:value={email}
					placeholder="you@email.com"
					class="flex-1 rounded-md border border-primary-200 dark:border-primary-700 bg-white dark:bg-primary-950 px-3 py-2 text-sm text-primary-900 dark:text-cfb-chalk focus:outline-none focus-visible:ring-2 focus-visible:ring-cfb-gold"
					disabled={status === 'loading'}
					required
				/>
				<button
					type="submit"
					class="btn btn-primary whitespace-nowrap"
					disabled={status === 'loading'}
				>
					{status === 'loading' ? 'Joining…' : `Get ${DROP_NAME}`}
				</button>
			</div>
			{#if message}
				<p
					class="text-xs {status === 'ok'
						? 'text-primary-700 dark:text-cfb-gold-bright'
						: 'text-cfb-red'}"
					role="status"
				>
					{message}
				</p>
			{/if}
		</form>
	</div>
</section>
