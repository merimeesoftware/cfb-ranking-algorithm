import { Container, ContainerProxy, getRandom } from '@cloudflare/containers';
import { dailyLimitFor, type SpendBucket } from './budget.ts';
import {
	boardRoute,
	buildRuntimeEnv,
	busyResponse,
	checkPublicQuery,
	clientIp,
	containerSecrets,
	enforceVisitorLimit,
	isCounterEndpoint,
	paidCallAllowed,
	stripPublicCounters,
	UNPUBLISHED_MESSAGE,
	type CapEnv,
	type Manifest,
	type RateLimiter,
} from './caps.ts';
import { completeFromRequest, WORKERS_AI_HOST, XAI_HOST, type WorkersAiBinding } from './providers.ts';
import { consumeSpend } from './spend-object.ts';

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
		if (hostname === 'spend.budget') {
			return consumeSpend(this.ctx, this.env, request);
		}
		await this.startAndWaitForPorts({
			startOptions: { envVars: this.runtimeEnvVars(hostname) },
			cancellationOptions: { portReadyTimeoutMS: 120_000 },
		});
		return super.fetch(request);
	}
}

/**
 * Container outbound hosts. spend.budget is the shared daily counter.
 * ai.xai and ai.workers perform the live completion. No visitor can reach them.
 */
CfbApiContainer.outboundByHost = {
	'spend.budget': async (request: Request, env: Env): Promise<Response> => {
		let payload: { bucket?: string } = {};
		try {
			payload = (await request.json()) as { bucket?: string };
		} catch {
			return Response.json({ ok: false, error: 'json' }, { status: 400 });
		}
		const bucket = payload.bucket;
		if (bucket !== 'xai' && bucket !== 'workers_ai' && bucket !== 'cfbd') {
			return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
		}
		const spendBucket = bucket as SpendBucket;
		const limit = dailyLimitFor(spendBucket, env);
		if (!paidCallAllowed(env, spendBucket)) {
			return Response.json(
				{ ok: false, count: 0, limit, bucket, code: 'kill_switch' },
				{ status: 429, headers: { 'cache-control': 'no-store' } },
			);
		}
		const stub = env.CFB_API.get(env.CFB_API.idFromName('spend-budget'));
		return stub.fetch('https://spend.budget/consume', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ bucket, limit }),
		});
	},
	[XAI_HOST]: async (request: Request, env: Env): Promise<Response> => {
		if (!paidCallAllowed(env, 'xai')) {
			return Response.json(
				{ ok: false, code: 'kill_switch' },
				{ status: 429, headers: { 'cache-control': 'no-store' } },
			);
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
		const incoming = new URL(request.url);
		const apiPath = incoming.pathname.replace(/^\/api/, '') || '/';

		const limit = await enforceVisitorLimit(request, {
			api: env.API_RATE_LIMITER,
			agent: env.AGENT_RATE_LIMITER,
		});
		if (limit.limited) return busyResponse(limit.code);

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

		const target = new URL(apiPath, incoming.origin);
		target.search = incoming.search;

		const headers = new Headers(request.headers);
		headers.delete('host');
		headers.delete('x-forwarded-for');
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
