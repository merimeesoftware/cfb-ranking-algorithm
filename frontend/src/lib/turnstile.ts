/**
 * Public Turnstile widget. Rendered only when PUBLIC_TURNSTILE_SITE_KEY is
 * set at build time. The secret stays on the Worker as TURNSTILE_SECRET_KEY.
 */

export const TURNSTILE_HEADER = 'cf-turnstile-response';

interface TurnstileApi {
	render: (el: HTMLElement, options: Record<string, unknown>) => string;
	reset: (widgetId?: string) => void;
	remove: (widgetId: string) => void;
}

declare global {
	interface Window {
		turnstile?: TurnstileApi;
	}
}

export function turnstileSiteKey(): string {
	const raw = import.meta.env.PUBLIC_TURNSTILE_SITE_KEY;
	return typeof raw === 'string' ? raw.trim() : '';
}

let scriptPromise: Promise<void> | null = null;
let widgetId: string | null = null;
let host: HTMLElement | null = null;
let current: string | null = null;
const waiters: Array<(token: string | null) => void> = [];

function loadScript(): Promise<void> {
	if (typeof window === 'undefined') return Promise.resolve();
	if (window.turnstile) return Promise.resolve();
	if (scriptPromise) return scriptPromise;
	scriptPromise = new Promise((resolve, reject) => {
		const script = document.createElement('script');
		script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
		script.async = true;
		script.onload = () => resolve();
		script.onerror = () => {
			scriptPromise = null;
			reject(new Error('turnstile'));
		};
		document.head.appendChild(script);
	});
	return scriptPromise;
}

function publish(token: string | null): void {
	const waiter = waiters.shift();
	if (waiter) {
		waiter(token);
		return;
	}
	current = token;
}

/** Mount the widget. No-op when the site key is unset. */
export function startTurnstile(el: HTMLElement): () => void {
	const siteKey = turnstileSiteKey();
	if (!siteKey) return () => undefined;
	host = el;
	let stopped = false;
	void loadScript()
		.then(() => {
			if (stopped || !window.turnstile || !host) return;
			widgetId = window.turnstile.render(host, {
				sitekey: siteKey,
				callback: (token: string) => publish(token),
				'error-callback': () => publish(null),
				'expired-callback': () => {
					current = null;
					if (widgetId) window.turnstile?.reset(widgetId);
				},
			});
		})
		.catch(() => {
			publish(null);
		});
	return () => {
		stopped = true;
		if (widgetId && window.turnstile) window.turnstile.remove(widgetId);
		widgetId = null;
		host = null;
		current = null;
	};
}

/** One token for the next agent request. Null when the widget is not configured. */
export function turnstileToken(): Promise<string | null> {
	if (!turnstileSiteKey() || typeof window === 'undefined') return Promise.resolve(null);
	if (current) {
		const token = current;
		current = null;
		if (widgetId) window.turnstile?.reset(widgetId);
		return Promise.resolve(token);
	}
	return new Promise((resolve) => {
		const timer = window.setTimeout(() => {
			const index = waiters.indexOf(finish);
			if (index !== -1) waiters.splice(index, 1);
			resolve(null);
		}, 10000);
		function finish(token: string | null) {
			window.clearTimeout(timer);
			resolve(token);
			if (token && widgetId) window.turnstile?.reset(widgetId);
		}
		waiters.push(finish);
	});
}

export async function agentHeaders(): Promise<Record<string, string>> {
	const headers: Record<string, string> = { 'Content-Type': 'application/json' };
	const token = await turnstileToken();
	if (token) headers[TURNSTILE_HEADER] = token;
	return headers;
}
