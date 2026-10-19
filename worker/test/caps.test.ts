import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { consumeDaily, dailyLimitFor, resolveDailyLimit, DEFAULT_XAI_MAX_CALLS_PER_DAY, DEFAULT_AI_MAX_CALLS_PER_DAY, DEFAULT_CFBD_MAX_CALLS_PER_DAY } from '../src/budget.ts';
import { consumeSpend, publicKillSetBody, type SpendState } from '../src/spend-object.ts';
import worker, { CfbApiContainer } from '../src/index.ts';
import { completeWorkersAi, completeXai, gatewayBypassErrors, isGatewayXaiUrl, xaiCompletionBody, xaiGatewayUrl, DEFAULT_WORKERS_AI_MODEL, WORKERS_AI_HOST, WORKERS_AI_MAX_OUTPUT_TOKENS, XAI_HOST, type GatewayCall } from '../src/providers.ts';
import { isoWeekId, weeklyCapMicros, worstCaseMicros, wouldCross, xaiUsdKey } from '../src/xai-usd.ts';
import {
	buildRuntimeEnv,
	checkPublicQuery,
	clientIp,
	containerSecrets,
	enforceVisitorLimit,
	SPEND_GATE_HOST,
	internalHosts,
	isInternalHost,
	isNonProductionHostname,
	isSpendKillRoute,
	paidCallAllowed,
	routeApiRequest,
	UPSTREAM_ORIGIN,
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
		body: JSON.stringify({ provider: 'cfbd', source: 'app' }),
	}));
	assert.equal(first.status, 200);
	const body = await first.json() as { ok: boolean; count: number; limit: number; provider: string; source: string };
	assert.equal(body.ok, true);
	assert.equal(body.count, 1);
	assert.equal(body.limit, DEFAULT_CFBD_MAX_CALLS_PER_DAY);
	assert.equal(body.provider, 'cfbd');
	assert.equal(body.source, 'app');
	const denied = await consumeSpend(state, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ bucket: 'nope' }),
	}));
	assert.equal(denied.status, 400);
	const mcp = await consumeSpend(state, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ provider: 'cfbd', source: 'mcp' }),
	}));
	assert.equal(mcp.status, 400);
	const reserved = await mcp.json() as { error: string; source: string };
	assert.equal(reserved.error, 'source');
	assert.equal(reserved.source, 'mcp');
});

test('unset daily limits fall back to in-code defaults', () => {
	const fixture = load('unset_defaults.json');
	assert.equal(resolveDailyLimit(undefined, DEFAULT_XAI_MAX_CALLS_PER_DAY), fixture.expect_xai);
	assert.equal(resolveDailyLimit(undefined, DEFAULT_AI_MAX_CALLS_PER_DAY), fixture.expect_workers_ai);
	assert.equal(resolveDailyLimit('', DEFAULT_CFBD_MAX_CALLS_PER_DAY), fixture.expect_cfbd);
	assert.equal(DEFAULT_XAI_MAX_CALLS_PER_DAY, 0);
	assert.equal(DEFAULT_AI_MAX_CALLS_PER_DAY, 100);
	assert.equal(dailyLimitFor('xai', { XAI_MAX_CALLS: '100' }), 0);
	assert.equal(dailyLimitFor('workers_ai', {}), 100);
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
	const first = await enforceVisitorLimit(request, { api, agent }, '/agent/explain');
	const second = await enforceVisitorLimit(request, { api, agent }, '/agent/explain');
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
	assert.equal(BUSY_MESSAGE, 'Busy right now. Try again later.');
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
	const disabled = { AI_KILL: '0', XAI_KILL: '0', WORKERS_AI_KILL: '0', CFBD_KILL: '0' };
	assert.equal(paidCallAllowed(disabled, 'xai'), false);
	assert.equal(paidCallAllowed(disabled, 'workers_ai'), true);
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
	assert.equal(forwarded.XAI_ENABLED, '0');
	assert.equal(forwarded.AI_MAX_CALLS, '100');
	assert.equal(forwarded.CFBD_MAX_CALLS, '25');
	assert.equal(forwarded.AI_KILL, '0');
	assert.equal(forwarded.XAI_KILL, '0');
	assert.equal(forwarded.WORKERS_AI_KILL, '0');
	assert.equal(forwarded.CFBD_KILL, '0');
	assert.equal(forwarded.SPEND_GATE_HOST, 'spend.budget');
	assert.equal(forwarded.AI_XAI_HOST, 'ai.xai');
	assert.equal(forwarded.AI_WORKERS_HOST, 'ai.workers');
	assert.equal(forwarded.XAI_WEEKLY_USD_CAP, '0');
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

test('xAI gateway path stays in code and a key does not reach it', async () => {
	const fixture = load('xai_disabled_with_key.json');
	const url = xaiGatewayUrl(
		fixture.CF_ACCOUNT_ID as string,
		fixture.AI_GATEWAY_ID as string,
	);
	assert.equal(url, 'https://gateway.ai.cloudflare.com/v1/acct-test/true-rankings/grok/v1/chat/completions');
	assert.equal(isGatewayXaiUrl(url ?? ''), true);
	assert.equal(gatewayBypassErrors({ provider: 'xai', url, gateway_id: 'true-rankings' }).length, 0);
	let fetched = false;
	const response = await completeXai(
		{
			XAI_API_KEY: fixture.XAI_API_KEY as string,
			CF_ACCOUNT_ID: fixture.CF_ACCOUNT_ID as string,
			AI_GATEWAY_ID: fixture.AI_GATEWAY_ID as string,
			XAI_ENABLED: fixture.XAI_ENABLED as string,
		},
		[{ role: 'user', content: 'Why is Oregon here?' }],
		(async () => {
			fetched = true;
			return new Response('{}', { status: 200 });
		}) as typeof fetch,
	);
	const body = await response.json() as { ok: boolean; error: string };
	assert.equal(response.status, 503);
	assert.equal(body.ok, false);
	assert.equal(body.error, 'disabled');
	assert.equal(fetched, false);
	assert.equal(JSON.stringify(body).includes(fixture.XAI_API_KEY as string), false);

	const raised = await consumeSpend(
		spendState({}),
		{ XAI_MAX_CALLS: fixture.XAI_MAX_CALLS as string },
		new Request('https://spend.budget/consume', {
			method: 'POST',
			body: JSON.stringify({ bucket: 'xai', limit: 100 }),
		}),
	);
	assert.equal(raised.status, 429);
	const denied = await raised.json() as { ok: boolean; limit: number };
	assert.equal(denied.ok, false);
	assert.equal(denied.limit, 0);
});

test('Workers AI completion passes the gateway id on the binding', async () => {
	let model = '';
	let options: { gateway?: { id?: string; skipCache?: boolean } } | undefined;
	let input: { messages?: unknown; max_tokens?: number; tools?: unknown; web_search?: unknown } | undefined;
	const response = await completeWorkersAi(
		{
			AI_GATEWAY_ID: 'true-rankings',
			AI: {
				async run(
					next: string,
					nextInput: { messages: { role: string; content: string }[]; max_tokens: number },
					gatewayOptions: { gateway: { id: string; skipCache: true } },
				) {
					model = next;
					input = nextInput;
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
	assert.equal(model, DEFAULT_WORKERS_AI_MODEL);
	assert.equal(model, '@cf/meta/llama-3.1-8b-instruct-fp8');
	assert.equal(input?.max_tokens, WORKERS_AI_MAX_OUTPUT_TOKENS);
	assert.equal(input?.tools, undefined);
	assert.equal(input?.web_search, undefined);
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

test('xAI week estimate matches the verify rates and the ISO week id', () => {
	assert.equal(worstCaseMicros('hi'), 2 * 25 + 256 * 100);
	assert.equal(weeklyCapMicros(undefined), 0);
	assert.equal(weeklyCapMicros(''), 0);
	assert.equal(weeklyCapMicros('0'), 0);
	assert.equal(weeklyCapMicros('0.23'), 230_000);
	assert.equal(wouldCross(0, 25650, 0), true);
	assert.equal(wouldCross(0, 25650, 25650), false);
	assert.equal(wouldCross(1, 25650, 25650), true);
	assert.equal(isoWeekId(new Date('2026-10-19T05:17:00Z')), '2026-W43');
	assert.equal(isoWeekId(new Date('2026-01-01T00:00:00Z')), '2026-W01');
	assert.equal(isoWeekId(new Date('2025-12-29T00:00:00Z')), '2026-W01');
	assert.equal(isoWeekId(new Date('2027-01-01T00:00:00Z')), '2026-W53');
	assert.equal(xaiUsdKey(new Date('2026-10-19T05:17:00Z')), 'xai:usd:2026-W43');
	assert.equal(xaiCompletionBody('grok-4', [{ role: 'user', content: 'hi' }]).max_tokens, 256);
});

test('weekly dollar cap of 0 refuses the reserve and does not store', async () => {
	const data = new Map<string, number>();
	const closed = {
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
	const denied = await consumeSpend(closed, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ action: 'reserve_usd', provider: 'xai', bucket: 'xai', prompt: 'hi' }),
	}));
	assert.equal(denied.status, 429);
	const body = await denied.json() as {
		ok: boolean;
		busy: boolean;
		message: string;
		code: string;
		spent_micros: number;
	};
	assert.equal(body.ok, false);
	assert.equal(body.busy, true);
	assert.equal(body.message, BUSY_MESSAGE);
	assert.equal(body.code, 'xai_weekly_usd');
	assert.equal(body.spent_micros, 0);
	assert.equal(data.size, 0);
});

test('a second reserve that would cross the week cap does not add', async () => {
	const data = new Map<string, number>();
	const state = {
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
	const env = { XAI_WEEKLY_USD_CAP: '0.03' };
	const first = await consumeSpend(state, env, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ action: 'reserve_usd', bucket: 'xai', prompt: 'hi' }),
	}));
	assert.equal(first.status, 200);
	const opened = await first.json() as { ok: boolean; spent_micros: number; week: string };
	assert.equal(opened.ok, true);
	assert.equal(opened.spent_micros, worstCaseMicros('hi'));
	assert.match(opened.week, /^\d{4}-W\d{2}$/);
	assert.equal(data.get(xaiUsdKey()), worstCaseMicros('hi'));
	const second = await consumeSpend(state, env, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ action: 'reserve_usd', bucket: 'xai', prompt: 'hi' }),
	}));
	assert.equal(second.status, 429);
	const denied = await second.json() as { ok: boolean; busy: boolean; message: string; code: string };
	assert.equal(denied.ok, false);
	assert.equal(denied.busy, true);
	assert.equal(denied.message, BUSY_MESSAGE);
	assert.equal(denied.code, 'xai_weekly_usd');
	assert.equal(data.get(xaiUsdKey()), worstCaseMicros('hi'));
});

test('raising the weekly cap still does not fetch while the daily budget is 0', async () => {
	let fetched = false;
	const response = await completeXai(
		{
			XAI_API_KEY: 'test-token',
			CF_ACCOUNT_ID: 'acct-test',
			AI_GATEWAY_ID: 'true-rankings',
			XAI_ENABLED: '1',
			XAI_WEEKLY_USD_CAP: '4',
		},
		[{ role: 'user', content: 'hi' }],
		(async () => {
			fetched = true;
			return new Response('{}', { status: 200 });
		}) as typeof fetch,
	);
	const body = await response.json() as { ok: boolean; error: string };
	assert.equal(response.status, 503);
	assert.equal(body.error, 'disabled');
	assert.equal(fetched, false);
});

function trackedSpend(seed: Record<string, number>) {
	const data = new Map<string, number>(Object.entries(seed));
	const state: SpendState = {
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
	return { data, state };
}

test('durable object kill flags trip after dashboard vars are cleared', async () => {
	const fixture = load('do_kill.json');
	const { data, state } = trackedSpend(fixture.storage as Record<string, number>);
	const before = new Map(data);
	const env = fixture.env as Record<string, string>;
	for (const body of fixture.requests as Record<string, unknown>[]) {
		const response = await consumeSpend(state, env, new Request('https://spend.budget/consume', {
			method: 'POST',
			body: JSON.stringify(body),
		}));
		assert.equal(response.status, 429);
		const payload = await response.json() as { ok: boolean; code: string; busy: boolean; message: string };
		assert.equal(payload.ok, false);
		assert.equal(payload.busy, true);
		assert.equal(payload.message, BUSY_MESSAGE);
		assert.equal(payload.code, fixture.expect_code);
	}
	assert.deepEqual([...data.entries()], [...before.entries()]);
	assert.equal(isSpendKillRoute('POST', (fixture.latch as { route: string }).route), true);
	assert.equal(isSpendKillRoute('GET', (fixture.latch as { route: string }).route), false);
});

test('set_kill latches flags that a wiped env cannot clear', async () => {
	const fixture = load('do_kill.json');
	const latch = fixture.latch as { secret: string; ai_kill: number; cfbd_kill: number };
	const { data, state } = trackedSpend({});
	const denied = await consumeSpend(state, {}, new Request('https://spend.budget/consume', {
		method: 'POST',
		headers: { 'x-cache-secret': latch.secret },
		body: JSON.stringify({ action: 'set_kill', ai_kill: latch.ai_kill, cfbd_kill: latch.cfbd_kill }),
	}));
	assert.equal(denied.status, 403);
	assert.equal(data.size, 0);
	const wrong = await consumeSpend(
		state,
		{ CACHE_CLEAR_SECRET: latch.secret },
		new Request('https://spend.budget/consume', {
			method: 'POST',
			headers: { 'x-cache-secret': 'nope' },
			body: JSON.stringify({ action: 'set_kill', ai_kill: latch.ai_kill }),
		}),
	);
	assert.equal(wrong.status, 401);
	assert.equal(data.size, 0);
	const planted = publicKillSetBody({
		action: 'consume',
		provider: 'xai',
		ai_kill: latch.ai_kill,
		cfbd_kill: latch.cfbd_kill,
	});
	assert.deepEqual(planted, { action: 'set_kill', ai_kill: latch.ai_kill, cfbd_kill: latch.cfbd_kill });
	const set = await consumeSpend(
		state,
		{ CACHE_CLEAR_SECRET: latch.secret },
		new Request('https://spend.budget/consume', {
			method: 'POST',
			headers: { 'x-cache-secret': latch.secret },
			body: JSON.stringify(planted),
		}),
	);
	assert.equal(set.status, 200);
	assert.equal(data.get('ai_kill'), 1);
	assert.equal(data.get('cfbd_kill'), 1);
	const response = await consumeSpend(state, fixture.env as Record<string, string>, new Request('https://spend.budget/consume', {
		method: 'POST',
		body: JSON.stringify({ provider: 'cfbd', source: 'app' }),
	}));
	assert.equal(response.status, 429);
	const payload = await response.json() as { ok: boolean; code: string };
	assert.equal(payload.ok, false);
	assert.equal(payload.code, fixture.expect_code);
	assert.equal(data.get('ai_kill'), 1);
	assert.equal(data.get('cfbd_kill'), 1);
	assert.equal([...data.keys()].some((key) => key.startsWith('cfbd:app:')), false);
});

test('spoofed api paths never select an internal or production host', () => {
	const fixture = load('path_spoof.json');
	assert.deepEqual(
		[...internalHosts()].sort(),
		[SPEND_GATE_HOST, XAI_HOST, WORKERS_AI_HOST].sort(),
	);
	for (const host of internalHosts()) assert.equal(isInternalHost(host), true);
	for (const form of fixture.forms as { name: string; url: string }[]) {
		const routed = routeApiRequest(form.url);
		assert.equal(routed.ok, false, form.name);
		if (!routed.ok) assert.equal(routed.status, 400);
	}
	const safe = routeApiRequest(fixture.safe as string);
	assert.equal(safe.ok, true);
	if (safe.ok) {
		assert.equal(safe.upstream.origin, UPSTREAM_ORIGIN);
		assert.equal(safe.upstream.hostname, 'api.internal');
		assert.equal(safe.upstream.pathname, '/rankings');
		assert.equal(safe.upstream.search, '?year=2024&week=10');
		assert.equal(safe.modeHost, 'preview.example.workers.dev');
		assert.equal(isNonProductionHostname(safe.modeHost), true);
		assert.equal(isInternalHost(safe.upstream.hostname), false);
		assert.equal(safe.upstream.hostname.includes('spend.budget'), false);
	}
});

test('agent limiter follows the routed path, not a normalized raw URL', async () => {
	let agentHits = 0;
	const limiters = {
		api: { async limit() { return { success: true }; } },
		agent: {
			async limit() {
				agentHits += 1;
				return { success: true };
			},
		},
	};
	const traversal = new Request('https://preview.example.workers.dev/api/%2e%2e/agent/explain');
	await enforceVisitorLimit(traversal, limiters, '/rankings');
	assert.equal(agentHits, 0);
	await enforceVisitorLimit(traversal, limiters, '/agent/explain');
	assert.equal(agentHits, 1);
});

function apiEnv(capture: { request: Request | null }, agentHits: { n: number }) {
	return {
		API_RATE_LIMITER: { async limit() { return { success: true }; } },
		AGENT_RATE_LIMITER: {
			async limit() {
				agentHits.n += 1;
				return { success: true };
			},
		},
		ASSETS: { async fetch() { return new Response('no', { status: 404 }); } },
		CFB_API: {
			idFromName() { return 'id'; },
			get() {
				return {
					async fetch(request: Request) {
						capture.request = request;
						return new Response('{"status":"ok"}', {
							status: 200,
							headers: { 'content-type': 'application/json' },
						});
					},
				};
			},
		},
	};
}

test('fetch keeps the container on api.internal and rejects dot-dot paths', async () => {
	const capture: { request: Request | null } = { request: null };
	const agentHits = { n: 0 };
	const env = apiEnv(capture, agentHits);
	const response = await worker.fetch(new Request('https://preview.example.workers.dev/api/agent/explain', {
		headers: { 'CF-Connecting-IP': '203.0.113.8' },
	}), env as never);
	assert.equal(response.status, 200);
	assert.ok(capture.request);
	const upstream = new URL(capture.request.url);
	assert.equal(upstream.hostname, 'api.internal');
	assert.equal(upstream.pathname, '/agent/explain');
	assert.equal(capture.request.headers.get('x-visitor-host'), 'preview.example.workers.dev');
	assert.equal(agentHits.n, 1);

	for (const path of ['/api/%2e%2e/agent/explain', '/api/.%2e/agent/explain']) {
		capture.request = null;
		agentHits.n = 0;
		const rejected = await worker.fetch(
			new Request(`https://preview.example.workers.dev${path}`),
			env as never,
		);
		assert.equal(rejected.status, 400);
		assert.equal(capture.request, null);
		assert.equal(agentHits.n, 0);
	}
});

test('workers ai outbound refuses call 101 before the model runs', async () => {
	const state = spendState({});
	const budgetEnv = { AI_MAX_CALLS: '100' };
	for (let n = 0; n < 100; n += 1) {
		const accepted = await consumeSpend(state, budgetEnv, new Request('https://spend.budget/consume', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ provider: 'workers_ai', bucket: 'workers_ai' }),
		}));
		assert.equal(accepted.status, 200);
	}
	let modelRan = false;
	const env = {
		AI_MAX_CALLS: '100',
		AI_GATEWAY_ID: 'true-rankings',
		AI: {
			async run() {
				modelRan = true;
				return { response: 'no' };
			},
		},
		CFB_API: {
			idFromName() { return 'spend-budget'; },
			get() {
				return {
					fetch(request: Request) {
						return consumeSpend(state, budgetEnv, request);
					},
				};
			},
		},
	};
	const handler = CfbApiContainer.outboundByHost['ai.workers'] as (
		request: Request,
		env: typeof env,
	) => Promise<Response>;
	const response = await handler(new Request('https://ai.workers/complete', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ messages: [{ role: 'user', content: 'Why is Oregon here?' }] }),
	}), env);
	assert.equal(response.status, 429);
	const body = await response.json() as { ok: boolean; code: string };
	assert.equal(body.ok, false);
	assert.equal(body.code, 'workers_ai_budget');
	assert.equal(modelRan, false);
});

test('AI_MAX_CALLS of 1000 still refuses workers ai call 101', async () => {
	const state = spendState({});
	const budgetEnv = { AI_MAX_CALLS: '1000' };
	assert.equal(dailyLimitFor('workers_ai', budgetEnv), 100);
	for (let n = 0; n < 100; n += 1) {
		const accepted = await consumeSpend(state, budgetEnv, new Request('https://spend.budget/consume', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ provider: 'workers_ai', bucket: 'workers_ai' }),
		}));
		assert.equal(accepted.status, 200);
	}
	let modelRan = false;
	const env = {
		AI_MAX_CALLS: '1000',
		AI_GATEWAY_ID: 'true-rankings',
		AI: {
			async run() {
				modelRan = true;
				return { response: 'no' };
			},
		},
		CFB_API: {
			idFromName() { return 'spend-budget'; },
			get() {
				return {
					fetch(request: Request) {
						return consumeSpend(state, budgetEnv, request);
					},
				};
			},
		},
	};
	const handler = CfbApiContainer.outboundByHost['ai.workers'] as (
		request: Request,
		env: typeof env,
	) => Promise<Response>;
	const response = await handler(new Request('https://ai.workers/complete', {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ messages: [{ role: 'user', content: 'Why is Oregon here?' }] }),
	}), env);
	assert.equal(response.status, 429);
	const body = await response.json() as { ok: boolean; code: string };
	assert.equal(body.ok, false);
	assert.equal(body.code, 'workers_ai_budget');
	assert.equal(modelRan, false);
});
