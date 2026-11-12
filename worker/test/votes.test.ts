import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { BUSY_MESSAGE, FORMULA_MESSAGE, turnstileDecision } from '../src/caps.ts';
import worker from '../src/index.ts';
import {
	FanVoteTally,
	VOTE_COOKIE,
	VOTE_COOKIE_MAX_AGE,
	VOTE_PRIVACY,
	applyMark,
	enforceVoteLimit,
	handleVoteGet,
	handleVotePost,
	newVoteId,
	readVotes,
	voteDedupeHash,
	voteObjectName,
	voteSetCookie,
	voteTurnstile,
	type VoteMap,
	type VoteMark,
	type VoteState,
} from '../src/votes.ts';

const MANIFEST = { years: { '2024': [10], '2026': [1, 10] } };
const TEAMS = new Set(['Quiet', 'Loud']);
const IP = '203.0.113.44';

function racingState(): VoteState & { outside: () => number } {
	const data = new Map<string, unknown>();
	let depth = 0;
	let outside = 0;
	let revision = 0;
	let tail: Promise<unknown> = Promise.resolve();
	const open = new Map<string, { seen: number; value: unknown }[]>();

	const storage = {
		async get<T>(key: string): Promise<T | undefined> {
			const value = data.get(key) as T | undefined;
			if (depth === 0) {
				outside += 1;
				if (key.startsWith('count:')) {
					const bucket = open.get(key) ?? [];
					bucket.push({ seen: revision, value });
					open.set(key, bucket);
				}
				await new Promise((resolve) => setTimeout(resolve, 0));
				return value;
			}
			return data.get(key) as T | undefined;
		},
		async put(key: string, value: string | number) {
			if (depth === 0) outside += 1;
			if (depth === 0 && typeof value === 'number') {
				const bucket = open.get(key) ?? [];
				const read = bucket.pop();
				const base = read && typeof read.value === 'number' ? read.value : 0;
				const current = typeof data.get(key) === 'number' ? data.get(key) as number : 0;
				const stale = read !== undefined && read.seen !== revision;
				const crowded = read !== undefined && bucket.some((item) => item.seen === read.seen);
				if (stale) {
					data.set(key, current + (value - base));
					revision += 1;
					return;
				}
				if (crowded) {
					data.set(key, value);
					revision += 1;
					return;
				}
			}
			data.set(key, value);
			if (typeof value === 'number') revision += 1;
		},
		async list(prefix: string) {
			const out = new Map<string, unknown>();
			for (const [key, value] of data) {
				if (key.startsWith(prefix)) out.set(key, value);
			}
			return out;
		},
	};

	return {
		storage,
		outside: () => outside,
		blockConcurrencyWhile<T>(callback: () => Promise<T>): Promise<T> {
			const run = tail.then(async () => {
				depth += 1;
				try {
					return await callback();
				} finally {
					depth -= 1;
				}
			});
			tail = run.then(() => undefined, () => undefined);
			return run;
		},
	};
}

function tally(state: VoteState): FanVoteTally {
	const object = Object.create(FanVoteTally.prototype) as FanVoteTally & {
		ctx: {
			blockConcurrencyWhile: VoteState['blockConcurrencyWhile'];
			storage: {
				get: VoteState['storage']['get'];
				put: VoteState['storage']['put'];
				list: (options: { prefix: string }) => Promise<Map<string, unknown>>;
			};
		};
	};
	object.ctx = {
		blockConcurrencyWhile: (callback) => state.blockConcurrencyWhile(callback),
		storage: {
			get: (key) => state.storage.get(key),
			put: (key, value) => state.storage.put(key, value),
			list: (options) => state.storage.list(options.prefix),
		},
	};
	return object;
}

function markBody(hash: string, team: string, mark: VoteMark): string {
	return JSON.stringify({ hash, team, mark });
}

async function teamCount(state: VoteState, team: string): Promise<{ too_high: number; too_low: number }> {
	const votes = await readVotes(state);
	return votes[team] ?? { too_high: 0, too_low: 0 };
}

function siteverifyPass() {
	return async () => Response.json({ success: true, hostname: 'example.test', action: 'vote' });
}

function voteRequest(body: unknown, cookie?: string, origin = 'https://example.test'): Request {
	const headers = new Headers({
		origin,
		'content-type': 'application/json',
		'CF-Connecting-IP': IP,
		'cf-turnstile-response': 'token-ok',
	});
	if (cookie) headers.set('cookie', cookie);
	return new Request('https://example.test/api/votes', {
		method: 'POST',
		headers,
		body: JSON.stringify(body),
	});
}

function openLimiter() {
	return { async limit() { return { success: true }; } };
}

function voteEnv(capture: { bodies: unknown[]; names: string[] }, state: VoteState) {
	return {
		TURNSTILE_SECRET_KEY: 'turnstile-test-secret',
		VOTE_RATE_LIMITER: openLimiter(),
		FAN_VOTES: {
			idFromName(name: string) {
				capture.names.push(name);
				return name as unknown as DurableObjectId;
			},
			get() {
				return {
					async fetch(request: Request) {
						const body = await request.json() as { hash: string; team: string; mark: VoteMark };
						capture.bodies.push(body);
						const object = tally(state);
						return object.fetch(new Request(request.url, {
							method: 'POST',
							body: markBody(body.hash, body.team, body.mark),
						}));
					},
				};
			},
		},
	};
}

test('vote hash is SHA-256 of id, year, week, and team with no pepper', async () => {
	const digest = async (text: string) => {
		const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
		return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
	};
	const id = 'ab'.repeat(16);
	const hash = await voteDedupeHash(id, 2024, 10, 'Quiet');
	assert.equal(hash, await digest(`${id}|2024|10|Quiet`));
	assert.notEqual(hash, await digest(`pepper|${id}|2024|10|Quiet`));
	const source = readFileSync(new URL('../src/votes.ts', import.meta.url), 'utf8');
	assert.equal(source.includes('pepper'), false);
	assert.equal(source.includes('VOTE_PEPPER'), false);
	assert.equal(source.includes('turnstileDecision'), false);
	assert.equal(source.includes('CfbApiContainer'), false);
	assert.equal(source.includes('enableInternet'), false);
	assert.equal(source.includes('console.'), false);
	assert.equal(source.includes('Math.random'), false);
	assert.equal(source.includes('not logged'), false);
	assert.match(VOTE_PRIVACY, /not stored/);
});

test('cookie is __Host-tr_vote for at most 180 days', () => {
	const id = newVoteId();
	assert.match(id, /^[0-9a-f]{32}$/);
	const header = voteSetCookie(id);
	assert.equal(VOTE_COOKIE_MAX_AGE <= 180 * 24 * 60 * 60, true);
	assert.match(header, new RegExp(`^${VOTE_COOKIE}=${id}; `));
	const parts = header.split(';').map((part) => part.trim());
	assert.deepEqual(parts.slice(1), [
		'HttpOnly',
		'Secure',
		'SameSite=Lax',
		'Path=/',
		`Max-Age=${VOTE_COOKIE_MAX_AGE}`,
	]);
	assert.equal(parts.some((part) => part.toLowerCase().startsWith('domain=')), false);
});

test('two concurrent marks with the same cookie leave the count at 1', async () => {
	const state = racingState();
	const capture = { bodies: [] as unknown[], names: [] as string[] };
	const env = voteEnv(capture, state);
	const id = 'cd'.repeat(16);
	const cookie = `${VOTE_COOKIE}=${id}`;
	const body = { year: 2024, week: 10, team: 'Quiet', mark: 'too_high' };
	const [first, second] = await Promise.all([
		handleVotePost(voteRequest(body, cookie), env, MANIFEST, TEAMS, siteverifyPass()),
		handleVotePost(voteRequest(body, cookie), env, MANIFEST, TEAMS, siteverifyPass()),
	]);
	assert.equal(first.status, 200);
	assert.equal(second.status, 200);
	assert.equal(capture.bodies.length, 2);
	assert.deepEqual(capture.names, ['2024-w10', '2024-w10']);
	const hashes = capture.bodies.map((item) => (item as { hash: string }).hash);
	assert.equal(hashes[0], hashes[1]);
	assert.equal(hashes[0]?.includes(id), false);
	for (const sent of capture.bodies) {
		assert.deepEqual(Object.keys(sent as object).sort(), ['hash', 'mark', 'team']);
		assert.equal(JSON.stringify(sent).includes(IP), false);
		assert.equal(JSON.stringify(sent).includes(id), false);
	}
	const row = await teamCount(state, 'Quiet');
	assert.deepEqual(row, { too_high: 1, too_low: 0 });
	assert.equal(state.outside(), 0);
	const echoed = `${await first.clone().text()}\n${await second.text()}`;
	assert.equal(echoed.includes(id), false);
	assert.equal(echoed.includes(IP), false);
	assert.match(echoed, /not stored/);
});

test('a replaced mark moves one tally instead of adding a second', async () => {
	const state = racingState();
	const hash = await voteDedupeHash('ef'.repeat(16), 2026, 1, 'Loud');
	await applyMark(state, { hash, team: 'Loud', mark: 'too_high' });
	await applyMark(state, { hash, team: 'Loud', mark: 'too_low' });
	assert.deepEqual(await teamCount(state, 'Loud'), { too_high: 0, too_low: 1 });
});

test('a missing tally reads back as an empty zero map', async () => {
	const state = racingState();
	const response = await tally(state).fetch(new Request('https://fan-votes.internal/counts'));
	const body = await response.json() as { votes: VoteMap };
	assert.deepEqual(body.votes, {});
	assert.equal(voteObjectName(2026, 10), '2026-w10');
});

test('vote limiter failure is HTTP 429', async () => {
	const response = await enforceVoteLimit(
		{ async limit() { return { success: false }; } },
		IP,
	);
	assert.ok(response);
	assert.equal(response?.status, 429);
	const body = await response?.json() as { code: string; message: string; busy: boolean; capped: boolean };
	assert.equal(body.code, 'vote_rate_limit');
	assert.equal(body.message, BUSY_MESSAGE);
	assert.equal(body.busy, true);
	assert.equal(body.capped, true);

	let siteverifyCalls = 0;
	const limited = await handleVotePost(
		voteRequest({ year: 2024, week: 10, team: 'Quiet', mark: 'too_high' }),
		{
			TURNSTILE_SECRET_KEY: 'turnstile-test-secret',
			VOTE_RATE_LIMITER: { async limit() { return { success: false }; } },
			FAN_VOTES: {
				idFromName() { throw new Error('storage'); },
				get() { throw new Error('storage'); },
			},
		},
		MANIFEST,
		TEAMS,
		async () => {
			siteverifyCalls += 1;
			return Response.json({ success: true });
		},
	);
	assert.equal(limited.status, 429);
	assert.equal(siteverifyCalls, 0);
});

test('vote turnstile refuses a missing secret', async () => {
	let called = 0;
	const vote = await voteTurnstile({
		secret: '  ',
		token: 'token-ok',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => {
			called += 1;
			return Response.json({ success: true });
		},
	});
	assert.deepEqual(vote, { ok: false, reason: 'secret' });
	assert.equal(called, 0);
	const agent = await turnstileDecision({}, '', IP, async () => {
		throw new Error('agent siteverify');
	}, () => {});
	assert.equal(agent, 'pass');
});

test('vote turnstile refuses a missing token', async () => {
	let called = 0;
	const vote = await voteTurnstile({
		secret: 'turnstile-test-secret',
		token: '',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => {
			called += 1;
			return Response.json({ success: true });
		},
	});
	assert.deepEqual(vote, { ok: false, reason: 'token' });
	assert.equal(called, 0);
});

test('vote turnstile refuses a siteverify network error', async () => {
	const network = await voteTurnstile({
		secret: 'turnstile-test-secret',
		token: 'token-ok',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => {
			throw new Error('network');
		},
	});
	assert.deepEqual(network, { ok: false, reason: 'siteverify' });
});

test('vote turnstile refuses a siteverify non-2xx', async () => {
	const status = await voteTurnstile({
		secret: 'turnstile-test-secret',
		token: 'token-ok',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => new Response('no', { status: 503 }),
	});
	assert.deepEqual(status, { ok: false, reason: 'siteverify' });
});

test('vote turnstile refuses success false', async () => {
	const vote = await voteTurnstile({
		secret: 'turnstile-test-secret',
		token: 'token-ok',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => Response.json({
			success: false,
			hostname: 'example.test',
			action: 'vote',
		}),
	});
	assert.deepEqual(vote, { ok: false, reason: 'success' });
});

test('vote turnstile refuses a hostname mismatch', async () => {
	const vote = await voteTurnstile({
		secret: 'turnstile-test-secret',
		token: 'token-ok',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => Response.json({
			success: true,
			hostname: 'other.example',
			action: 'vote',
		}),
	});
	assert.deepEqual(vote, { ok: false, reason: 'hostname' });
});

test('vote turnstile refuses an action mismatch', async () => {
	const vote = await voteTurnstile({
		secret: 'turnstile-test-secret',
		token: 'token-ok',
		ip: IP,
		hostname: 'example.test',
		siteverify: async () => Response.json({
			success: true,
			hostname: 'example.test',
			action: 'login',
		}),
	});
	assert.deepEqual(vote, { ok: false, reason: 'action' });
});

test('vote post refuses a foreign origin', async () => {
	let called = 0;
	const response = await handleVotePost(
		voteRequest(
			{ year: 2024, week: 10, team: 'Quiet', mark: 'too_high' },
			undefined,
			'https://other.example',
		),
		{
			TURNSTILE_SECRET_KEY: 'turnstile-test-secret',
			VOTE_RATE_LIMITER: openLimiter(),
			FAN_VOTES: {
				idFromName() { throw new Error('storage'); },
				get() { throw new Error('storage'); },
			},
		},
		MANIFEST,
		TEAMS,
		async () => {
			called += 1;
			return Response.json({ success: true });
		},
	);
	assert.equal(response.status, 403);
	assert.equal((await response.json() as { code: string }).code, 'origin');
	assert.equal(called, 0);
});

test('an unpublished week, including 2025, writes nothing', async () => {
	let names = 0;
	const response = await handleVotePost(
		voteRequest({ year: 2025, week: 15, team: 'Quiet', mark: 'too_low' }),
		{
			TURNSTILE_SECRET_KEY: 'turnstile-test-secret',
			VOTE_RATE_LIMITER: openLimiter(),
			FAN_VOTES: {
				idFromName() {
					names += 1;
					return '2025-w15' as unknown as DurableObjectId;
				},
				get() { throw new Error('storage'); },
			},
		},
		MANIFEST,
		TEAMS,
		siteverifyPass(),
	);
	assert.equal(response.status, 200);
	const body = await response.json() as { code: string; year: number };
	assert.equal(body.code, 'not_published');
	assert.equal(body.year, 2025);
	assert.equal(names, 0);
	assert.equal(JSON.stringify(body).includes('team_rankings'), false);
});

test('GET counts use one object per year-week and do not open 2025', async () => {
	const names: string[] = [];
	const assets: string[] = [];
	const response = await handleVoteGet(
		new URLSearchParams('year=2024&week=10'),
		MANIFEST,
		{
			idFromName(name: string) {
				names.push(name);
				return name as unknown as DurableObjectId;
			},
			get() {
				return {
					async fetch() {
						return Response.json({ votes: {} });
					},
				};
			},
		},
	);
	assert.equal(response.status, 200);
	assert.deepEqual(names, ['2024-w10']);
	const body = await response.json() as { year: number; week: number; votes: VoteMap };
	assert.deepEqual(body, { year: 2024, week: 10, votes: {} });
	assert.equal(JSON.stringify(body).includes('ordering_score'), false);

	const sealed = await handleVoteGet(
		new URLSearchParams('year=2025&week=1'),
		MANIFEST,
		{
			idFromName() {
				assets.push('object');
				return 'no' as unknown as DurableObjectId;
			},
			get() { throw new Error('storage'); },
		},
	);
	assert.equal((await sealed.json() as { code: string }).code, 'not_published');
	assert.deepEqual(assets, []);

	const rejected = await handleVoteGet(
		new URLSearchParams('year=2024&week=10&too_high=1'),
		MANIFEST,
		{
			idFromName() { throw new Error('storage'); },
			get() { throw new Error('storage'); },
		},
	);
	assert.equal(rejected.status, 400);
	const refusal = await rejected.json() as { code: string; rejected: string[] };
	assert.equal(refusal.code, 'formula_params');
	assert.deepEqual(refusal.rejected, ['too_high']);
	assert.equal(refusal.code === 'formula_params' && FORMULA_MESSAGE.length > 0, true);
});

test('POST /api/votes stays dark and does not boot the container', async () => {
	const index = readFileSync(new URL('../src/index.ts', import.meta.url), 'utf8');
	assert.equal(index.includes('handleVotePost'), false);
	let votes = 0;
	let container = 0;
	const env = {
		API_RATE_LIMITER: { async limit() { return { success: true }; } },
		AGENT_RATE_LIMITER: { async limit() { return { success: true }; } },
		VOTE_RATE_LIMITER: {
			async limit() {
				votes += 1;
				return { success: false };
			},
		},
		ASSETS: { async fetch() { throw new Error('assets'); } },
		CFB_API: {
			idFromName() { container += 1; return 'spend'; },
			get() { container += 1; return { async fetch() { container += 1; } }; },
		},
		FAN_VOTES: {
			idFromName() { votes += 1; return 'tally'; },
			get() { votes += 1; return { async fetch() { votes += 1; } }; },
		},
	};
	const response = await worker.fetch(new Request('https://example.test/api/votes', {
		method: 'POST',
		headers: {
			origin: 'https://example.test',
			'content-type': 'application/json',
			'CF-Connecting-IP': IP,
			'cf-turnstile-response': 'token-ok',
		},
		body: JSON.stringify({ year: 2024, week: 10, team: 'Quiet', mark: 'too_high' }),
	}), env as never);
	assert.equal(response.status, 404);
	assert.equal(votes, 0);
	assert.equal(container, 0);

	const wrangler = readFileSync(new URL('../../wrangler.toml', import.meta.url), 'utf8');
	assert.match(wrangler, /class_name = "FanVoteTally"/);
	assert.match(wrangler, /tag = "v2"\nnew_sqlite_classes = \["FanVoteTally"\]/);
	assert.equal(wrangler.includes('kv_namespaces'), false);
	assert.match(wrangler, /name = "VOTE_RATE_LIMITER"\nnamespace_id = "9303"\nsimple = \{ limit = 10, period = 60 \}/);
});

test('GET /api/votes reads the tally and leaves 2025 sealed', async () => {
	const paths: string[] = [];
	let container = 0;
	const env = {
		API_RATE_LIMITER: { async limit() { return { success: true }; } },
		AGENT_RATE_LIMITER: { async limit() { return { success: true }; } },
		ASSETS: {
			async fetch(request: Request) {
				const url = new URL(request.url);
				paths.push(url.pathname);
				if (url.pathname === '/rankings/manifest.json') {
					return Response.json(MANIFEST);
				}
				return new Response('missing', { status: 404 });
			},
		},
		CFB_API: {
			get() {
				container += 1;
				return { async fetch() { container += 1; } };
			},
		},
		FAN_VOTES: {
			idFromName(name: string) {
				assert.equal(name, '2024-w10');
				return name;
			},
			get() {
				return {
					async fetch() {
						return Response.json({ votes: { Quiet: { too_high: 2, too_low: 0 } } });
					},
				};
			},
		},
	};
	const response = await worker.fetch(
		new Request('https://example.test/api/votes?year=2024&week=10'),
		env as never,
	);
	assert.equal(response.status, 200);
	const body = await response.json() as { votes: VoteMap; ordering_score?: unknown };
	assert.deepEqual(body.votes.Quiet, { too_high: 2, too_low: 0 });
	assert.equal('ordering_score' in body, false);
	assert.equal(container, 0);
	assert.deepEqual(paths, ['/rankings/manifest.json']);

	paths.length = 0;
	const sealed = await worker.fetch(
		new Request('https://example.test/api/votes?year=2025&week=1'),
		env as never,
	);
	assert.equal((await sealed.json() as { code: string }).code, 'not_published');
	assert.deepEqual(paths, ['/rankings/manifest.json']);
	assert.equal(paths.some((path) => path.includes('2025')), false);
});
