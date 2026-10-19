import {
	CFBD_APP_SOURCE,
	CFBD_PROVIDER,
	consumeDaily,
	dailyLimitFor,
	resolveDailyLimit,
	type BudgetEnv,
	type SpendBucket,
} from './budget.ts';

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
 * in UTC. This app's CFBD budget is provider `cfbd`, source `app`. Source
 * `mcp` is reserved for #115 and is refused here.
 *
 * This runs on the existing `CfbApiContainer` class (instance name
 * `spend-budget`) so a preview version upload does not add a Durable Object
 * migration. The handler returns before the container process starts.
 */
export async function consumeSpend(state: SpendState, env: BudgetEnv, request: Request): Promise<Response> {
	let payload: { provider?: string; bucket?: string; source?: string; limit?: number } = {};
	try {
		payload = (await request.json()) as { provider?: string; bucket?: string; source?: string; limit?: number };
	} catch {
		return Response.json({ ok: false, error: 'json' }, { status: 400 });
	}
	const bucket = asBucket(payload.provider ?? payload.bucket);
	if (!bucket) {
		return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
	}
	let source: string | undefined;
	if (bucket === CFBD_PROVIDER) {
		source = (payload.source ?? '').trim() || CFBD_APP_SOURCE;
		if (source !== CFBD_APP_SOURCE) {
			return Response.json(
				{ ok: false, error: 'source', provider: CFBD_PROVIDER, source },
				{ status: 400 },
			);
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
	const result = await state.blockConcurrencyWhile(() => consumeDaily(store, bucket, limit, new Date(), source));
	return Response.json(result, {
		status: result.ok ? 200 : 429,
		headers: { 'cache-control': 'no-store' },
	});
}
