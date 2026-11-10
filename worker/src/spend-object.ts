import {
	CFBD_APP_SOURCE,
	CFBD_PROVIDER,
	consumeDaily,
	dailyLimitFor,
	resolveDailyLimit,
	type BudgetEnv,
	type SpendBucket,
} from './budget.ts';
import { BUSY_MESSAGE, jsonSecurityHeaders } from './caps.ts';
import { isoWeekId, weeklyCapMicros, worstCaseMicros, wouldCross, xaiUsdKey } from './xai-usd.ts';

/**
 * Durable Object keys. A deploy that clears dashboard vars must not clear
 * these. They are written only by `set_kill`, never copied from env.
 */
export const AI_KILL_KEY = 'ai_kill';
export const CFBD_KILL_KEY = 'cfbd_kill';

/** Storage surface used by the named container instance that holds the counters. */
export interface SpendState {
	storage: {
		get<T = unknown>(key: string): Promise<T | undefined>;
		put(key: string, value: number): Promise<unknown>;
	};
	blockConcurrencyWhile<T>(callback: () => Promise<T>): Promise<T>;
}

const BUCKETS: readonly SpendBucket[] = ['xai', 'workers_ai', 'cfbd'];

function asBucket(value: unknown): SpendBucket | null {
	return BUCKETS.includes(value as SpendBucket) ? value as SpendBucket : null;
}

/**
 * One global counter for every container instance. Storage keys are
 * `xai:YYYY-MM-DD`, `workers_ai:YYYY-MM-DD`, and `cfbd:{source}:YYYY-MM-DD`
 * in UTC. xAI dollars use `xai:usd:{ISO week}` (`xai:usd:YYYY-Www`), rolling
 * at Monday 00:00 UTC. `ai_kill` and `cfbd_kill` are 0 or 1 and are read
 * inside the same `blockConcurrencyWhile` as the counter they gate.
 * This app's CFBD budget is provider `cfbd`, source `app`. Source `mcp` is
 * reserved for #115 and is refused here.
 *
 * This runs on the existing `CfbApiContainer` class (instance name
 * `spend-budget`) so a preview version upload does not add a Durable Object
 * migration. The handler returns before the container process starts.
 */
type SpendEnv = BudgetEnv & {
	XAI_WEEKLY_USD_CAP?: string;
	CACHE_CLEAR_SECRET?: string;
	SPEND_KILL_SECRET?: string;
};

type SpendPayload = {
	provider?: string;
	bucket?: string;
	source?: string;
	limit?: number;
	action?: string;
	prompt?: string;
	ai_kill?: unknown;
	cfbd_kill?: unknown;
};

function killKeyFor(bucket: SpendBucket): string {
	return bucket === CFBD_PROVIDER ? CFBD_KILL_KEY : AI_KILL_KEY;
}

async function killLatched(state: SpendState, key: string): Promise<boolean> {
	return (await state.storage.get<number>(key)) === 1;
}

function killBit(value: unknown): 0 | 1 | null {
	if (value === 0 || value === '0') return 0;
	if (value === 1 || value === '1') return 1;
	return null;
}

function spendJson(body: object, status: number): Response {
	return Response.json(body, { status, headers: jsonSecurityHeaders() });
}

/** Compare SHA-256 digests so a different length does not return early. */
export async function secretsMatch(expected: string, provided: string): Promise<boolean> {
	const encoder = new TextEncoder();
	const [left, right] = await Promise.all([
		crypto.subtle.digest('SHA-256', encoder.encode(expected)),
		crypto.subtle.digest('SHA-256', encoder.encode(provided)),
	]);
	return crypto.subtle.timingSafeEqual(left, right);
}

/** Header only. Unset SPEND_KILL_SECRET fails closed and never uses another secret. */
export async function spendKillAuthorized(
	env: { SPEND_KILL_SECRET?: string },
	request: Request,
): Promise<{ ok: true } | { ok: false; status: 403 | 401 }> {
	const expected = (env.SPEND_KILL_SECRET ?? '').trim();
	if (!expected) return { ok: false, status: 403 };
	const provided = request.headers.get('x-spend-kill-secret') ?? '';
	if (!(await secretsMatch(expected, provided))) return { ok: false, status: 401 };
	return { ok: true };
}

/**
 * Header only. Unset CACHE_CLEAR_SECRET fails closed. The container still
 * compares with hmac.compare_digest after this gate.
 */
export async function cacheClearAuthorized(
	env: { CACHE_CLEAR_SECRET?: string },
	request: Request,
): Promise<boolean> {
	const expected = env.CACHE_CLEAR_SECRET ?? '';
	if (!expected) return false;
	const provided = request.headers.get('x-cache-secret') ?? '';
	return secretsMatch(expected, provided);
}

/** Public POST /api/spend/kill may only write the two flags. */
export function publicKillSetBody(raw: unknown): { action: 'set_kill'; ai_kill?: unknown; cfbd_kill?: unknown } | null {
	if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
	const record = raw as Record<string, unknown>;
	const body: { action: 'set_kill'; ai_kill?: unknown; cfbd_kill?: unknown } = { action: 'set_kill' };
	if ('ai_kill' in record) body.ai_kill = record.ai_kill;
	if ('cfbd_kill' in record) body.cfbd_kill = record.cfbd_kill;
	return body;
}

async function setStoredKills(state: SpendState, env: SpendEnv, request: Request, payload: SpendPayload): Promise<Response> {
	const auth = await spendKillAuthorized(env, request);
	if (!auth.ok) {
		return spendJson({ ok: false, error: 'auth' }, auth.status);
	}
	const updates: Record<string, 0 | 1> = {};
	if (payload.ai_kill !== undefined) {
		const bit = killBit(payload.ai_kill);
		if (bit === null) {
			return spendJson({ ok: false, error: 'flags' }, 400);
		}
		updates[AI_KILL_KEY] = bit;
	}
	if (payload.cfbd_kill !== undefined) {
		const bit = killBit(payload.cfbd_kill);
		if (bit === null) {
			return spendJson({ ok: false, error: 'flags' }, 400);
		}
		updates[CFBD_KILL_KEY] = bit;
	}
	if (!Object.keys(updates).length) {
		return spendJson({ ok: false, error: 'flags' }, 400);
	}
	await state.blockConcurrencyWhile(async () => {
		for (const [key, value] of Object.entries(updates)) {
			await state.storage.put(key, value);
		}
	});
	return spendJson({ ok: true, ...updates }, 200);
}

async function reserveXaiUsd(
	state: SpendState,
	env: SpendEnv,
	prompt: string,
): Promise<Response> {
	const add = worstCaseMicros(prompt);
	const cap = weeklyCapMicros(env.XAI_WEEKLY_USD_CAP);
	const week = isoWeekId();
	const key = xaiUsdKey();
	const result = await state.blockConcurrencyWhile(async () => {
		if (await killLatched(state, AI_KILL_KEY)) {
			return {
				ok: false,
				busy: true,
				capped: true,
				message: BUSY_MESSAGE,
				code: 'kill_switch',
				spent_micros: 0,
				cap_micros: cap,
				week,
			};
		}
		const raw = await state.storage.get<number>(key);
		const current = typeof raw === 'number' && Number.isFinite(raw) ? raw : 0;
		if (wouldCross(current, add, cap)) {
			return {
				ok: false,
				busy: true,
				capped: true,
				message: BUSY_MESSAGE,
				code: 'xai_weekly_usd',
				spent_micros: current,
				cap_micros: cap,
				week,
			};
		}
		const next = current + add;
		await state.storage.put(key, next);
		return {
			ok: true,
			spent_micros: next,
			cap_micros: cap,
			reserved_micros: add,
			week,
		};
	});
	return spendJson(result, result.ok ? 200 : 429);
}

export async function consumeSpend(state: SpendState, env: SpendEnv, request: Request): Promise<Response> {
	let payload: SpendPayload = {};
	try {
		payload = (await request.json()) as SpendPayload;
	} catch {
		return spendJson({ ok: false, error: 'json' }, 400);
	}
	if (payload.action === 'set_kill') {
		return setStoredKills(state, env, request, payload);
	}
	const bucket = asBucket(payload.provider ?? payload.bucket);
	if (!bucket) {
		return spendJson({ ok: false, error: 'bucket' }, 400);
	}
	if (payload.action === 'reserve_usd') {
		if (bucket !== 'xai') {
			return spendJson({ ok: false, error: 'bucket' }, 400);
		}
		const prompt = typeof payload.prompt === 'string' ? payload.prompt : '';
		return reserveXaiUsd(state, env, prompt);
	}
	let source: string | undefined;
	if (bucket === CFBD_PROVIDER) {
		source = (payload.source ?? '').trim() || CFBD_APP_SOURCE;
		if (source !== CFBD_APP_SOURCE) {
			return spendJson({ ok: false, error: 'source', provider: CFBD_PROVIDER, source }, 400);
		}
	}
	const fallback = dailyLimitFor(bucket, env);
	const limit = bucket === 'xai' || payload.limit === undefined
		? fallback
		: resolveDailyLimit(payload.limit, fallback);
	const store = {
		get: (key: string) => state.storage.get<number>(key),
		put: (key: string, value: number) => state.storage.put(key, value).then(() => undefined),
	};
	const result = await state.blockConcurrencyWhile(async () => {
		if (await killLatched(state, killKeyFor(bucket))) {
			return {
				ok: false,
				busy: true,
				capped: true,
				message: BUSY_MESSAGE,
				count: 0,
				limit,
				bucket,
				provider: bucket,
				...(source ? { source } : {}),
				code: 'kill_switch',
			};
		}
		return consumeDaily(store, bucket, limit, new Date(), source);
	});
	return spendJson(result, result.ok ? 200 : 429);
}
