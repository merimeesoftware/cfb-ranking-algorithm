import { Container, ContainerProxy, getRandom } from '@cloudflare/containers';
import { CFBD_APP_SOURCE, CFBD_PROVIDER, dailyLimitFor, type SpendBucket } from './budget.ts';
import {
	boardRoute,
	buildRuntimeEnv,
	busyResponse,
	checkPublicQuery,
	clientIp,
	containerSecrets,
	enforceVisitorLimit,
	isCounterEndpoint,
	isInternalHost,
	isSpendKillRoute,
	isVisitorApiPath,
	paidCallAllowed,
	routeApiRequest,
	VISITOR_HOST_HEADER,
	stripPublicCounters,
	UNPUBLISHED_MESSAGE,
	type CapEnv,
	type Manifest,
	type RateLimiter,
} from './caps.ts';
import { completeFromRequest, WORKERS_AI_HOST, XAI_HOST, type WorkersAiBinding } from './providers.ts';
import { consumeSpend, publicKillSetBody } from './spend-object.ts';

export { ContainerProxy };

export interface Env extends CapEnv {
	ASSETS: Fetcher;
	CFB_API: DurableObjectNamespace<CfbApiContainer>;
	API_RATE_LIMITER: RateLimiter;
	AGENT_RATE_LIMITER: RateLimiter;
	CFBD_API_KEY?: string;
	XAI_API_KEY?: string;
	CF_ACCOUNT_ID?: string;
	AI_GATEWAY_ID?: string;
	CACHE_CLEAR_SECRET?: string;
	CORS_ORIGINS?: string;
	AI?: WorkersAiBinding;
}

/** Flask API container (gunicorn on port 8080). */
export class CfbApiContainer extends Container<Env> {
	defaultPort = 8080;
	sleepAfter = '30m';
	enableInternet = true;

	envVars: Record<string, string> = {
		PORT: '8080',
		FLASK_ENV: 'production',
		CACHE_BACKEND: 'file',
		CACHE_DIR: '/tmp/cfb-cache',
		AI_MODE: 'stub',
		CFBD_OFFLINE: '1',
	};

	/**
	 * Paid-call caps and kill switches are forwarded even when unset, using the
	 * in-code defaults from caps.ts / budget.ts. Unset and preview hostnames
	 * use AI_MODE=stub and CFBD_OFFLINE=1 unless PREVIEW_* overrides a preview.
	 * XAI_API_KEY is not forwarded. The ai.xai outbound host sends it only to
	 * the AI Gateway grok path. AI_GATEWAY_ID selects that gateway.
	 */
	private runtimeEnvVars(hostname: string): Record<string, string> {
		return {
			...buildRuntimeEnv(this.envVars, this.env, hostname),
			...containerSecrets(this.env),
		};
	}

	override async fetch(request: Request): Promise<Response> {
		const hostname = new URL(request.url).hostname;
		// Named instance `spend-budget` only stores the daily counters. Starting
		// the container here would boot gunicorn for a bookkeeping request.
		// ai.xai and ai.workers are outbound hosts, not visitor entry points.
		if (hostname === 'spend.budget') {
			return consumeSpend(this.ctx, this.env, request);
		}
		if (isInternalHost(hostname)) {
			return jsonResponse({ ok: false, error: 'path' }, 400);
		}
		const visitorHost = request.headers.get(VISITOR_HOST_HEADER)?.trim() || hostname;
		if (isInternalHost(visitorHost)) {
			return jsonResponse({ ok: false, error: 'path' }, 400);
		}
		await this.startAndWaitForPorts({
			startOptions: { envVars: this.runtimeEnvVars(visitorHost) },
			cancellationOptions: { portReadyTimeoutMS: 120_000 },
		});
		return super.fetch(request);
	}
}

/**
 * Container outbound hosts. spend.budget is the shared daily counter.
 * ai.xai and ai.workers perform the live completion. No visitor can reach them.
 */
async function xaiPrompt(request: Request): Promise<string> {
	try {
		const body = (await request.json()) as { messages?: { content?: unknown }[] };
		if (!Array.isArray(body.messages)) return '';
		return body.messages
			.map((message) => (typeof message?.content === 'string' ? message.content : ''))
			.join('');
	} catch {
		return '';
	}
}

CfbApiContainer.outboundByHost = {
	'spend.budget': async (request: Request, env: Env): Promise<Response> => {
		let payload: { provider?: string; bucket?: string; source?: string; action?: string; prompt?: string } = {};
		try {
			payload = (await request.json()) as {
				provider?: string;
				bucket?: string;
				source?: string;
				action?: string;
				prompt?: string;
			};
		} catch {
			return Response.json({ ok: false, error: 'json' }, { status: 400 });
		}
		if (payload.action === 'reserve_usd') {
			const stub = env.CFB_API.get(env.CFB_API.idFromName('spend-budget'));
			return stub.fetch('https://spend.budget/consume', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					action: 'reserve_usd',
					provider: 'xai',
					bucket: 'xai',
					prompt: typeof payload.prompt === 'string' ? payload.prompt : '',
				}),
			});
		}
		const bucket = payload.provider ?? payload.bucket;
		if (bucket !== 'xai' && bucket !== 'workers_ai' && bucket !== 'cfbd') {
			return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
		}
		const spendBucket = bucket as SpendBucket;
		const limit = dailyLimitFor(spendBucket, env);
		if (!paidCallAllowed(env, spendBucket)) {
			return Response.json(
				{ ok: false, count: 0, limit, bucket, provider: bucket, code: 'kill_switch' },
				{ status: 429, headers: { 'cache-control': 'no-store' } },
			);
		}
		const stub = env.CFB_API.get(env.CFB_API.idFromName('spend-budget'));
		const body: { provider: string; bucket: string; limit: number; source?: string } = {
			provider: bucket,
			bucket,
			limit,
		};
		if (bucket === CFBD_PROVIDER) body.source = payload.source?.trim() || CFBD_APP_SOURCE;
		return stub.fetch('https://spend.budget/consume', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify(body),
		});
	},
	[XAI_HOST]: async (request: Request, env: Env): Promise<Response> => {
		if (!paidCallAllowed(env, 'xai')) {
			return Response.json(
				{ ok: false, code: 'kill_switch' },
				{ status: 429, headers: { 'cache-control': 'no-store' } },
			);
		}
		if (request.headers.get('x-xai-week-reserved') !== '1') {
			const prompt = await xaiPrompt(request.clone());
			const stub = env.CFB_API.get(env.CFB_API.idFromName('spend-budget'));
			const reserved = await stub.fetch('https://spend.budget/consume', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					action: 'reserve_usd',
					provider: 'xai',
					bucket: 'xai',
					prompt,
				}),
			});
			if (!reserved.ok) return busyResponse('xai_weekly_usd');
		}
		return completeFromRequest('xai', env, request);
	},
	[WORKERS_AI_HOST]: async (request: Request, env: Env): Promise<Response> => {
		if (!paidCallAllowed(env, 'workers_ai')) {
			return Response.json(
				{ ok: false, code: 'kill_switch' },
				{ status: 429, headers: { 'cache-control': 'no-store' } },
			);
		}
		if (request.headers.get('x-workers-ai-reserved') !== '1') {
			const stub = env.CFB_API.get(env.CFB_API.idFromName('spend-budget'));
			const reserved = await stub.fetch('https://spend.budget/consume', {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ provider: 'workers_ai', bucket: 'workers_ai' }),
			});
			if (!reserved.ok) {
				return Response.json(
					{ ok: false, code: 'workers_ai_budget' },
					{ status: 429, headers: { 'cache-control': 'no-store' } },
				);
			}
		}
		return completeFromRequest('workers_ai', env, request);
	},
};

async function loadManifest(env: Env, origin: string): Promise<Manifest> {
	try {
		const assetUrl = new URL('/rankings/manifest.json', origin);
		const response = await env.ASSETS.fetch(new Request(assetUrl.toString()));
		if (!response.ok) return { years: {} };
		const payload = (await response.json()) as Manifest;
		if (!payload || typeof payload !== 'object' || !payload.years) return { years: {} };
		return payload;
	} catch {
		return { years: {} };
	}
}

function jsonResponse(body: Record<string, unknown>, status: number): Response {
	return Response.json(body, {
		status,
		headers: { 'cache-control': 'no-store' },
	});
}

async function sanitizeCounters(pathname: string, response: Response): Promise<Response> {
	if (!isCounterEndpoint(pathname)) return response;
	const text = await response.text();
	let parsed: unknown = {};
	try {
		parsed = text ? JSON.parse(text) : {};
	} catch {
		parsed = { status: 'ok' };
	}
	const headers = new Headers(response.headers);
	headers.set('cache-control', 'no-store');
	headers.delete('content-length');
	return new Response(JSON.stringify(stripPublicCounters(parsed)), {
		status: response.status,
		headers,
	});
}

/** Invoked for /api/* only (see wrangler.toml run_worker_first). */
export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		let incoming: URL;
		try {
			incoming = new URL(request.url);
		} catch {
			return jsonResponse({ ok: false, error: 'path' }, 400);
		}
		if (!isVisitorApiPath(incoming.pathname)) {
			return jsonResponse({ ok: false, error: 'path' }, 400);
		}
		const routed = routeApiRequest(request.url);
		if (!routed.ok) return jsonResponse({ ok: false, error: 'path' }, routed.status);
		const apiPath = routed.apiPath;

		const limit = await enforceVisitorLimit(request, {
			api: env.API_RATE_LIMITER,
			agent: env.AGENT_RATE_LIMITER,
		}, apiPath);
		if (limit.limited) return busyResponse(limit.code);

		if (isSpendKillRoute(request.method, apiPath)) {
			let raw: unknown = {};
			try {
				raw = await request.json();
			} catch {
				return jsonResponse({ ok: false, error: 'json' }, 400);
			}
			const body = publicKillSetBody(raw);
			if (!body) return jsonResponse({ ok: false, error: 'json' }, 400);
			const stub = env.CFB_API.get(env.CFB_API.idFromName('spend-budget'));
			return stub.fetch('https://spend.budget/consume', {
				method: 'POST',
				headers: {
					'content-type': 'application/json',
					'x-cache-secret': request.headers.get('x-cache-secret') ?? '',
				},
				body: JSON.stringify(body),
			});
		}

		const route = boardRoute(apiPath);
		if (route) {
			const manifest = await loadManifest(env, incoming.origin);
			const decision = checkPublicQuery(apiPath, incoming.searchParams, manifest);
			if (decision && !decision.ok) return jsonResponse(decision.body, decision.status);
			if (decision?.ok && decision.route === 'weeks') {
				return jsonResponse({
					year: decision.year,
					weeks: decision.weeks ?? [],
					max_week: decision.weeks?.length ? Math.max(...decision.weeks) : 0,
					published: true,
				}, 200);
			}
			if (decision?.ok && decision.route === 'rankings') {
				const assetUrl = new URL(
					`/rankings/${decision.year}/week-${decision.week}.json`,
					incoming.origin,
				);
				const asset = await env.ASSETS.fetch(new Request(assetUrl.toString()));
				if (asset.ok) return asset;
				return jsonResponse({
					published: false,
					busy: false,
					message: UNPUBLISHED_MESSAGE,
					code: 'not_published',
					year: decision.year,
					week: decision.week,
					team_rankings: [],
					conference_rankings: [],
				}, 200);
			}
		}

		const target = routed.upstream;

		const headers = new Headers(request.headers);
		headers.delete('host');
		headers.delete('x-forwarded-for');
		headers.delete(VISITOR_HOST_HEADER);
		headers.set(VISITOR_HOST_HEADER, routed.modeHost);
		headers.set('CF-Connecting-IP', limit.ip);

		const apiRequest = new Request(target.toString(), {
			method: request.method,
			headers,
			body: request.body,
			redirect: 'manual',
		});

		const container = await getRandom(env.CFB_API, 3);
		const response = await container.fetch(apiRequest);
		return sanitizeCounters(apiPath, response);
	},
};
