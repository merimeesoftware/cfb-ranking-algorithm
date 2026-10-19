import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { consumeDaily, resolveDailyLimit, DEFAULT_XAI_MAX_CALLS_PER_DAY, DEFAULT_WORKERS_AI_MAX_CALLS_PER_DAY, DEFAULT_CFBD_MAX_CALLS_PER_DAY } from '../src/budget.ts';
import { consumeSpend, type SpendState } from '../src/spend-object.ts';
import { completeWorkersAi, completeXai, gatewayBypassErrors, isGatewayXaiUrl, type GatewayCall } from '../src/providers.ts';
import {
	buildRuntimeEnv,
	checkPublicQuery,
	clientIp,
	containerSecrets,
	enforceVisitorLimit,
	isNonProductionHostname,
	paidCallAllowed,
	stripPublicCounters,
	BUSY_MESSAGE,
} from '../src/caps.ts';

const FIXTURES = new URL('../../tests/fixtures/caps/', import.meta.url);

function load(name: string): Record<string, unknown> {
	return JSON.parse(readFileSync(new URL(name, FIXTURES), 'utf8')) as Record<string, unknown>;
}

function spendState(seed: Record<string, number>): SpendState {
	const data = new Map<string, number>(Object.entries(seed));
	return {
		storage: {
			async get<T = unknown>(key: string) {
				return data.get(key) as T | undefined;
			},
			async put(key: string, value: number) {
				data.set(key, value);
			},
		},
		async blockConcurrencyWhile<T>(callback: () => Promise<T>) {
			return callback();
		},
	};
}

function mapStore(seed: Record<string, number>) {
	const data = new Map<string, number>(Object.entries(seed));
	return {
		data,
		async get(key: string) {
			return data.get(key);
		},
		async put(key: string, value: number) {
			data.set(key, value);
		},
	};
}

test('spend counter accepts one cfbd consume and rejects an unknown bucket', async () => {
	const state = spendState({});
	const first = await consumeSpend(state, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ bucket: 'cfbd' }),
	}));
	assert.equal(first.status, 200);
	const body = await first.json() as { ok: boolean; count: number; limit: number };
	assert.equal(body.ok, true);
	assert.equal(body.count, 1);
	assert.equal(body.limit, DEFAULT_CFBD_MAX_CALLS_PER_DAY);
	const denied = await consumeSpend(state, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ bucket: 'nope' }),
	}));
	assert.equal(denied.status, 400);
});

test('unset daily limits fall back to in-code defaults', () => {
	const fixture = load('unset_defaults.json');
	assert.equal(resolveDailyLimit(undefined, DEFAULT_XAI_MAX_CALLS_PER_DAY), fixture.expect_xai);
	assert.equal(resolveDailyLimit(undefined, DEFAULT_WORKERS_AI_MAX_CALLS_PER_DAY), fixture.expect_workers_ai);
	assert.equal(resolveDailyLimit('', DEFAULT_CFBD_MAX_CALLS_PER_DAY), fixture.expect_cfbd);
	assert.equal(DEFAULT_XAI_MAX_CALLS_PER_DAY, 0);
	assert.equal(DEFAULT_WORKERS_AI_MAX_CALLS_PER_DAY, 0);
	assert.notEqual(resolveDailyLimit(undefined, DEFAULT_XAI_MAX_CALLS_PER_DAY), Number.POSITIVE_INFINITY);
});

test('xAI daily budget trips on the planted zero cap', async () => {
	const fixture = load('xai_daily_at_cap.json');
	const store = mapStore(fixture.counts as Record<string, number>);
	const result = await consumeDaily(
		store,
		'xai',
		fixture.limit as number,
		new Date(fixture.now as string),
	);
	assert.equal(result.ok, false);
	assert.equal(result.code, 'xai_budget');
	assert.equal(result.count, fixture.already_used);
	assert.equal(store.data.has('xai:2026-10-19'), false);
});

test('Workers AI daily budget trips on the planted zero cap', async () => {
	const fixture = load('workers_ai_daily_at_cap.json');
	const store = mapStore(fixture.counts as Record<string, number>);
	const result = await consumeDaily(
		store,
		'workers_ai',
		fixture.limit as number,
		new Date(fixture.now as string),
	);
	assert.equal(result.ok, false);
	assert.equal(result.code, 'workers_ai_budget');
	assert.equal(result.count, fixture.already_used);
});

test('CFBD daily budget trips on the planted counter', async () => {
	const fixture = load('cfbd_daily_at_cap.json');
	const store = mapStore(fixture.counts as Record<string, number>);
	const result = await consumeDaily(
		store,
		'cfbd',
		fixture.limit as number,
		new Date(fixture.now as string),
	);
	assert.equal(result.ok, false);
	assert.equal(result.code, 'cfbd_budget');
	assert.equal(result.count, fixture.limit);
});

test('per-IP limiter trips on CF-Connecting-IP and ignores X-Forwarded-For', async () => {
	const fixture = load('rate_limit_ip.json');
	const seen: string[] = [];
	let agentUsed = 0;
	const api = {
		async limit(options: { key: string }) {
			seen.push(options.key);
			return { success: true };
		},
	};
	const agent = {
		async limit(options: { key: string }) {
			seen.push(options.key);
			agentUsed += 1;
			return { success: agentUsed <= (fixture.limit as number) };
		},
	};
	const request = new Request('https://truerankings.com/api/agent/explain', {
		headers: {
			'CF-Connecting-IP': fixture.cf_connecting_ip as string,
			'X-Forwarded-For': fixture.x_forwarded_for as string,
		},
	});
	assert.equal(clientIp(request), fixture.cf_connecting_ip);
	const first = await enforceVisitorLimit(request, { api, agent });
	const second = await enforceVisitorLimit(request, { api, agent });
	assert.equal(first.limited, false);
	assert.equal(second.limited, true);
	assert.equal(second.code, 'agent_rate_limit');
	assert.ok(seen.every((key) => key === fixture.cf_connecting_ip));
	assert.ok(!seen.includes(fixture.x_forwarded_for as string));
	const spoofed = new Request('https://truerankings.com/api/rankings', {
		headers: { 'X-Forwarded-For': fixture.cf_connecting_ip as string },
	});
	assert.equal(clientIp(spoofed), 'unknown');
});

test('manifest allowlist rejects formula params and unlisted weeks', () => {
	const fixture = load('manifest_allowlist.json');
	const manifest = { years: fixture.years as Record<string, number[]> };
	const rejected = checkPublicQuery(
		'/rankings',
		new URL(`https://truerankings.com${fixture.reject_query as string}`).searchParams,
		manifest,
	);
	assert.ok(rejected && !rejected.ok);
	if (rejected && !rejected.ok) {
		assert.equal(rejected.status, 400);
		assert.equal(rejected.body.code, 'formula_params');
	}
	const allowed = checkPublicQuery(
		'/rankings',
		new URL(`https://truerankings.com${fixture.allow_query as string}`).searchParams,
		manifest,
	);
	assert.ok(allowed && allowed.ok);
	const unlisted = checkPublicQuery(
		'/rankings',
		new URL(`https://truerankings.com${fixture.unlisted_query as string}`).searchParams,
		manifest,
	);
	assert.ok(unlisted && !unlisted.ok);
	if (unlisted && !unlisted.ok) {
		assert.equal(unlisted.body.code, 'not_published');
		assert.equal(unlisted.body.message, "That week isn't on the board yet.");
	}
});

test('kill switch blocks both AI providers and CFBD', () => {
	const fixture = load('kill_switch.json');
	const env = {
		AI_KILL: fixture.AI_KILL as string,
		XAI_KILL: fixture.XAI_KILL as string,
		WORKERS_AI_KILL: fixture.WORKERS_AI_KILL as string,
		CFBD_KILL: fixture.CFBD_KILL as string,
	};
	assert.equal(paidCallAllowed(env, 'xai'), false);
	assert.equal(paidCallAllowed(env, 'workers_ai'), false);
	assert.equal(paidCallAllowed(env, 'cfbd'), false);
	assert.equal(BUSY_MESSAGE, 'Busy right now, try again later.');
});

test('per-provider kill flags block only that provider', () => {
	const fixture = load('provider_kill.json');
	const env = {
		AI_KILL: fixture.AI_KILL as string,
		XAI_KILL: fixture.XAI_KILL as string,
		WORKERS_AI_KILL: fixture.WORKERS_AI_KILL as string,
		CFBD_KILL: fixture.CFBD_KILL as string,
	};
	assert.equal(paidCallAllowed(env, 'xai'), false);
	assert.equal(paidCallAllowed(env, 'workers_ai'), false);
	assert.equal(paidCallAllowed(env, 'cfbd'), true);
	const xaiOnly = { AI_KILL: '0', XAI_KILL: '1', WORKERS_AI_KILL: '0', CFBD_KILL: '0' };
	assert.equal(paidCallAllowed(xaiOnly, 'xai'), false);
	assert.equal(paidCallAllowed(xaiOnly, 'workers_ai'), true);
});

test('runtime env forwards caps and keeps preview and unset production stub/offline', () => {
	const forwarded = buildRuntimeEnv(
		{ PORT: '8080', AI_MODE: 'stub', CFBD_OFFLINE: '1' },
		{ AI_MODE: 'stub', CFBD_OFFLINE: '1' },
		'true-rankings-cfb.example.workers.dev',
	);
	assert.equal(forwarded.AI_MODE, 'stub');
	assert.equal(forwarded.CFBD_OFFLINE, '1');
	assert.equal(forwarded.XAI_MAX_CALLS, '0');
	assert.equal(forwarded.WORKERS_AI_MAX_CALLS, '0');
	assert.equal(forwarded.CFBD_MAX_CALLS, '25');
	assert.equal(forwarded.AI_KILL, '0');
	assert.equal(forwarded.XAI_KILL, '0');
	assert.equal(forwarded.WORKERS_AI_KILL, '0');
	assert.equal(forwarded.CFBD_KILL, '0');
	assert.equal(forwarded.SPEND_GATE_HOST, 'spend.budget');
	assert.equal(forwarded.AI_XAI_HOST, 'ai.xai');
	assert.equal(forwarded.AI_WORKERS_HOST, 'ai.workers');
	assert.equal('XAI_API_KEY' in forwarded, false);

	const unset = buildRuntimeEnv(
		{ PORT: '8080', AI_MODE: 'live', CFBD_OFFLINE: '0' },
		{},
		'true-rankings-cfb.example.workers.dev',
	);
	assert.equal(unset.AI_MODE, 'stub');
	assert.equal(unset.CFBD_OFFLINE, '1');

	const preview = buildRuntimeEnv(
		{ PORT: '8080', AI_MODE: 'live', CFBD_OFFLINE: '0' },
		{ AI_MODE: 'live', CFBD_OFFLINE: '0' },
		'abc123-true-rankings-cfb.example.workers.dev',
	);
	assert.equal(isNonProductionHostname('abc123-true-rankings-cfb.example.workers.dev'), true);
	assert.equal(preview.AI_MODE, 'stub');
	assert.equal(preview.CFBD_OFFLINE, '1');

	const overridden = buildRuntimeEnv(
		{ PORT: '8080' },
		{ AI_MODE: 'live', CFBD_OFFLINE: '0', PREVIEW_AI_MODE: 'live', PREVIEW_CFBD_OFFLINE: '0' },
		'cfb-rankings-dev.example.workers.dev',
	);
	assert.equal(overridden.AI_MODE, 'live');
	assert.equal(overridden.CFBD_OFFLINE, '0');
});

test('public counter strip drops budget fields from a planted health payload', () => {
	const stripped = stripPublicCounters({
		status: 'ok',
		xai_max_calls: 0,
		workers_ai_max_calls: 0,
		cfbd_max_calls: 25,
		xai_live_calls: 4,
		cfbd_calls: 9,
		cfbd_key: { slot: 'A' },
		agent_rate_limit_per_hour: 30,
		spend: { xai_max_calls: 0 },
		memory_entries: 12,
		cache_dir: '/tmp/cfb-cache',
	});
	assert.equal(stripped.status, 'ok');
	assert.equal(stripped.xai_max_calls, undefined);
	assert.equal(stripped.workers_ai_max_calls, undefined);
	assert.equal(stripped.cfbd_calls, undefined);
	assert.equal(stripped.spend, undefined);
	assert.equal(stripped.memory_entries, undefined);
	assert.equal(stripped.cache_dir, undefined);
});

test('xAI completion uses the gateway URL and does not echo the secret', async () => {
	const seen: { url?: string; authorization?: string; skipCache?: string } = {};
	const response = await completeXai(
		{ XAI_API_KEY: 'test-token', CF_ACCOUNT_ID: 'acct-test', AI_GATEWAY_ID: 'true-rankings' },
		[{ role: 'user', content: 'Why is Oregon here?' }],
		(async (url: string, init?: RequestInit) => {
			seen.url = String(url);
			const headers = new Headers(init?.headers);
			seen.authorization = headers.get('authorization') ?? '';
			seen.skipCache = headers.get('cf-aig-skip-cache') ?? '';
			return new Response(JSON.stringify({
				choices: [{ message: { content: 'The resume.' } }],
			}), { status: 200 });
		}) as typeof fetch,
	);
	const body = await response.json() as { ok: boolean; text: string };
	assert.equal(response.status, 200);
	assert.equal(body.ok, true);
	assert.equal(body.text, 'The resume.');
	assert.equal(
		seen.url,
		'https://gateway.ai.cloudflare.com/v1/acct-test/true-rankings/grok/v1/chat/completions',
	);
	assert.equal(isGatewayXaiUrl(seen.url ?? ''), true);
	assert.equal(gatewayBypassErrors({ provider: 'xai', url: seen.url, gateway_id: 'true-rankings' }).length, 0);
	assert.equal(seen.authorization, 'Bearer test-token');
	assert.equal(seen.skipCache, 'true');
	assert.equal(JSON.stringify(body).includes('test-token'), false);

	const fetchImpl = (async () => {
		throw new Error('fetch should not run');
	}) as typeof fetch;
	const missing = await completeXai(
		{ XAI_API_KEY: 'test-token' },
		[{ role: 'user', content: 'hi' }],
		fetchImpl,
	);
	assert.equal(missing.status, 503);
	const noKey = await completeXai(
		{ CF_ACCOUNT_ID: 'acct-test', AI_GATEWAY_ID: 'true-rankings' },
		[{ role: 'user', content: 'hi' }],
		fetchImpl,
	);
	assert.equal(noKey.status, 503);
});

test('Workers AI completion passes the gateway id on the binding', async () => {
	let model = '';
	let options: { gateway?: { id?: string; skipCache?: boolean } } | undefined;
	const response = await completeWorkersAi(
		{
			AI_GATEWAY_ID: 'true-rankings',
			AI: {
				async run(next: string, _input: { messages: { role: string; content: string }[] }, gatewayOptions: { gateway: { id: string; skipCache: true } }) {
					model = next;
					options = gatewayOptions;
					return { response: 'Stacked wins.' };
				},
			},
		},
		[{ role: 'user', content: 'What moves them up?' }],
	);
	const body = await response.json() as { ok: boolean; text: string };
	assert.equal(body.ok, true);
	assert.equal(body.text, 'Stacked wins.');
	assert.equal(model, '@cf/meta/llama-3.1-8b-instruct');
	assert.equal(options?.gateway?.id, 'true-rankings');
	assert.equal(options?.gateway?.skipCache, true);
	assert.equal(gatewayBypassErrors({ provider: 'workers_ai', gateway_id: options?.gateway?.id }).length, 0);
	const unbound = await completeWorkersAi(
		{ AI_GATEWAY_ID: 'true-rankings' },
		[{ role: 'user', content: 'hi' }],
	);
	assert.equal(unbound.status, 503);
	let ran = false;
	const noGateway = await completeWorkersAi(
		{
			AI: {
				async run() {
					ran = true;
					return { response: 'should not run' };
				},
			},
		},
		[{ role: 'user', content: 'hi' }],
	);
	assert.equal(noGateway.status, 503);
	assert.equal(ran, false);
});

test('planted gateway bypass fixture fails for a direct URL or a bare binding', () => {
	const fixture = load('gateway_bypass.json') as { calls?: GatewayCall[] };
	const calls = fixture.calls ?? [];
	assert.equal(calls.length, 2);
	for (const call of calls) {
		assert.notEqual(gatewayBypassErrors(call).length, 0);
	}
	const source = readFileSync(new URL('../src/providers.ts', import.meta.url), 'utf8')
		+ readFileSync(new URL('../src/index.ts', import.meta.url), 'utf8');
	assert.equal(source.includes('api.x.ai'), false);
	assert.equal(source.includes('gateway.ai.cloudflare.com'), true);
});

test('container secrets do not forward the xAI credential', () => {
	const forwarded = containerSecrets({
		CFBD_API_KEY: 'cfbd-test',
		XAI_API_KEY: 'test-token',
		CACHE_CLEAR_SECRET: 'clear-test',
	});
	assert.equal(forwarded.CFBD_API_KEY, 'cfbd-test');
	assert.equal(forwarded.CACHE_CLEAR_SECRET, 'clear-test');
	assert.equal('XAI_API_KEY' in forwarded, false);
});

test('spend counter refuses xAI when the default cap is zero', async () => {
	const state = spendState({});
	const denied = await consumeSpend(state, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ bucket: 'xai' }),
	}));
	assert.equal(denied.status, 429);
	const body = await denied.json() as { ok: boolean; limit: number; code: string };
	assert.equal(body.ok, false);
	assert.equal(body.limit, 0);
	assert.equal(body.code, 'xai_budget');
});
