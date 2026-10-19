import {
	CFBD_APP_SOURCE,
	CFBD_PROVIDER,
	consumeDaily,
	dailyLimitFor,
	resolveDailyLimit,
	type BudgetEnv,
	type SpendBucket,
} from './budget.ts';
import { BUSY_MESSAGE } from './caps.ts';
import { isoWeekId, weeklyCapMicros, worstCaseMicros, wouldCross, xaiUsdKey } from './xai-usd.ts';

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
 * at Monday 00:00 UTC. This app's CFBD budget is provider `cfbd`, source
 * `app`. Source `mcp` is reserved for #115 and is refused here.
 *
 * This runs on the existing `CfbApiContainer` class (instance name
 * `spend-budget`) so a preview version upload does not add a Durable Object
 * migration. The handler returns before the container process starts.
 */
type SpendEnv = BudgetEnv & { XAI_WEEKLY_USD_CAP?: string };

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
	return Response.json(result, {
		status: result.ok ? 200 : 429,
		headers: { 'cache-control': 'no-store' },
	});
}

export async function consumeSpend(state: SpendState, env: SpendEnv, request: Request): Promise<Response> {
	let payload: { provider?: string; bucket?: string; source?: string; limit?: number; action?: string; prompt?: string } = {};
	try {
		payload = (await request.json()) as {
			provider?: string;
			bucket?: string;
			source?: string;
			limit?: number;
			action?: string;
			prompt?: string;
		};
	} catch {
		return Response.json({ ok: false, error: 'json' }, { status: 400 });
	}
	const bucket = asBucket(payload.provider ?? payload.bucket);
	if (!bucket) {
		return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
	}
	if (payload.action === 'reserve_usd') {
		if (bucket !== 'xai') {
			return Response.json({ ok: false, error: 'bucket' }, { status: 400 });
		}
		const prompt = typeof payload.prompt === 'string' ? payload.prompt : '';
		return reserveXaiUsd(state, env, prompt);
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
