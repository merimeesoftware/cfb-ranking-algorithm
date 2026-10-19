import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { consumeDaily, resolveDailyLimit, DEFAULT_AI_MAX_CALLS_PER_DAY, DEFAULT_CFBD_MAX_CALLS_PER_DAY } from '../src/budget.ts';
import {
	buildRuntimeEnv,
	checkPublicQuery,
	clientIp,
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

test('unset daily limits fall back to in-code defaults', () => {
	const fixture = load('unset_defaults.json');
	assert.equal(resolveDailyLimit(undefined, DEFAULT_AI_MAX_CALLS_PER_DAY), fixture.expect_ai);
	assert.equal(resolveDailyLimit('', DEFAULT_CFBD_MAX_CALLS_PER_DAY), fixture.expect_cfbd);
	assert.equal(resolveDailyLimit('nope', DEFAULT_AI_MAX_CALLS_PER_DAY), fixture.expect_ai);
	assert.notEqual(resolveDailyLimit(undefined, DEFAULT_AI_MAX_CALLS_PER_DAY), Number.POSITIVE_INFINITY);
});

test('AI daily budget trips on the planted counter', async () => {
	const fixture = load('ai_daily_at_cap.json');
	const store = mapStore(fixture.counts as Record<string, number>);
	const result = await consumeDaily(
		store,
		'ai',
		fixture.limit as number,
		new Date(fixture.now as string),
	);
	assert.equal(result.ok, false);
	assert.equal(result.code, 'ai_budget');
	assert.equal(result.count, fixture.limit);
	assert.equal(store.data.get('ai:2026-10-19'), fixture.limit);
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

test('kill switch blocks both paid buckets', () => {
	const fixture = load('kill_switch.json');
	const env = {
		AI_KILL: fixture.AI_KILL as string,
		CFBD_KILL: fixture.CFBD_KILL as string,
	};
	assert.equal(paidCallAllowed(env, 'ai'), false);
	assert.equal(paidCallAllowed(env, 'cfbd'), false);
	assert.equal(BUSY_MESSAGE, 'Busy right now, try again later.');
});

test('runtime env forwards caps and keeps preview stub/offline', () => {
	const forwarded = buildRuntimeEnv(
		{ PORT: '8080', AI_MODE: 'live', CFBD_OFFLINE: '0' },
		{ AI_MODE: 'live', CFBD_OFFLINE: '0' },
		'true-rankings-cfb.example.workers.dev',
	);
	assert.equal(forwarded.AI_MODE, 'live');
	assert.equal(forwarded.CFBD_OFFLINE, '0');
	assert.equal(forwarded.AI_MAX_CALLS, '100');
	assert.equal(forwarded.CFBD_MAX_CALLS, '25');
	assert.equal(forwarded.AI_KILL, '0');
	assert.equal(forwarded.CFBD_KILL, '0');
	assert.equal(forwarded.SPEND_GATE_HOST, 'spend.budget');

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
		ai_max_calls: 100,
		cfbd_max_calls: 25,
		ai_live_calls: 4,
		cfbd_calls: 9,
		cfbd_key: { slot: 'A' },
		agent_rate_limit_per_hour: 30,
		spend: { ai_max_calls: 100 },
		memory_entries: 12,
		cache_dir: '/tmp/cfb-cache',
	});
	assert.equal(stripped.status, 'ok');
	assert.equal(stripped.ai_max_calls, undefined);
	assert.equal(stripped.cfbd_calls, undefined);
	assert.equal(stripped.spend, undefined);
	assert.equal(stripped.memory_entries, undefined);
	assert.equal(stripped.cache_dir, undefined);
});
