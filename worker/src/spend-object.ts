import { consumeDaily, resolveDailyLimit, DEFAULT_AI_MAX_CALLS_PER_DAY, DEFAULT_CFBD_MAX_CALLS_PER_DAY, type SpendBucket } from './budget.ts';

interface SpendEnv {
	AI_MAX_CALLS?: string;
	CFBD_MAX_CALLS?: string;
}

/** Storage surface used by the named container instance that holds the counters. */
export interface SpendState {
	storage: {
		get<T = unknown>(key: string): Promise<T | undefined>;
		put(key: string, value: number): Promise<unknown>;
	};
	blockConcurrencyWhile<T>(callback: () => Promise<T>): Promise<T>;
}

/**
 * One global counter for every container instance. Storage keys are
 * `ai:YYYY-MM-DD` and `cfbd:YYYY-MM-DD` in UTC.
 *
 * This runs on the existing `CfbApiContainer` class (instance name
 * `spend-budget`) so a preview version upload does not add a Durable Object
 * migration. The handler returns before the container process starts.
 */
export async function consumeSpend(state: SpendState, env: SpendEnv, request: Request): Promise<Response> {
	let payload: { bucket?: string; limit?: number } = {};
	try {
		payload = (await request.json()) as { bucket?: string; limit?: number };
	} catch {
		return Response.json({ ok: false, error: 'json' }, { status: 400 });
	}
	const bucket: SpendBucket | null = payload.bucket === 'ai' || payload.bucket === 'cfbd'
		? payload.bucket
		: null;
	if (!bucket) {
		return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
	}
	const fallback = bucket === 'ai' ? DEFAULT_AI_MAX_CALLS_PER_DAY : DEFAULT_CFBD_MAX_CALLS_PER_DAY;
	const envLimit = bucket === 'ai' ? env.AI_MAX_CALLS : env.CFBD_MAX_CALLS;
	const limit = resolveDailyLimit(payload.limit ?? envLimit, fallback);
	const store = {
		get: (key: string) => state.storage.get<number>(key),
		put: (key: string, value: number) => state.storage.put(key, value).then(() => undefined),
	};
	const result = await state.blockConcurrencyWhile(() => consumeDaily(store, bucket, limit));
	return Response.json(result, {
		status: result.ok ? 200 : 429,
		headers: { 'cache-control': 'no-store' },
	});
}
