interface Env {
	/** Full API origin, no trailing slash. Example: https://cfb-rankings-api.account.workers.dev */
	API_ORIGIN: string;
}

/**
 * Proxy /api/* to the Flask API Worker/Container.
 * Set API_ORIGIN per Pages environment (Production vs Preview) in the dashboard.
 */
export const onRequest: PagesFunction<Env> = async (context) => {
	const apiOrigin = context.env.API_ORIGIN;
	if (!apiOrigin) {
		return new Response(
			JSON.stringify({
				error: 'API_ORIGIN is not configured for this Pages environment.',
				hint: 'Set API_ORIGIN in Cloudflare Pages → Settings → Variables (Production and Preview).',
			}),
			{ status: 503, headers: { 'Content-Type': 'application/json' } },
		);
	}

	const incoming = new URL(context.request.url);
	const target = new URL(incoming.pathname.replace(/^\/api/, '') || '/', apiOrigin);
	target.search = incoming.search;

	const headers = new Headers(context.request.headers);
	headers.delete('host');

	const proxied = new Request(target.toString(), {
		method: context.request.method,
		headers,
		body: context.request.body,
		redirect: 'manual',
	});

	return fetch(proxied);
};
